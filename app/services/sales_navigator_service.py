"""Sales Navigator HTML scraping service."""

import json
import logging
import re
from datetime import UTC, datetime, timezone
from typing import Dict, List, Optional, Tuple
from urllib.parse import parse_qs, unquote, urlparse

from bs4 import BeautifulSoup
from sqlalchemy import and_, or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.connectra_client import ConnectraClient
from app.models.companies import Company, CompanyMetadata
from app.models.contacts import Contact, ContactMetadata
from app.repositories.linkedin import LinkedInRepository
from app.utils.batch_lookup import (
    batch_fetch_companies_by_uuids,
    batch_fetch_company_metadata_by_uuids,
    batch_fetch_contact_metadata_by_uuids,
    batch_fetch_contacts_by_uuids,
    fetch_companies_and_metadata_by_uuids,
    fetch_company_metadata_by_uuid,
    fetch_contact_metadata_by_uuid,
)
from app.utils.normalization import PLACEHOLDER_VALUE, normalize_text
from app.utils.sales_navigator_utils import (
    convert_sales_nav_url_to_linkedin,
    extract_departments_from_title_about,
    generate_company_uuid,
    generate_contact_uuid,
    infer_seniority,
    parse_location,
    parse_name,
)

logger = logging.getLogger(__name__)


def clean_text(text: Optional[str]) -> Optional[str]:
    """Clean and normalize text content."""
    if not text:
        return None
    # Remove extra whitespace and newlines
    text = ' '.join(text.split())
    return text.strip() if text.strip() else None


def parse_lead_url(url: str) -> Dict[str, Optional[str]]:
    """
    Parse lead URL to extract lead ID, search type, and search ID.
    
    Args:
        url: Profile URL in format /sales/lead/{LEAD_ID},{SEARCH_TYPE},{SEARCH_ID}
        
    Returns:
        Dictionary with lead_id, search_type, search_id
    """
    result = {
        'lead_id': None,
        'search_type': None,
        'search_id': None
    }
    
    if not url:
        return result
    
    # Remove query parameters and base URL if present
    if '?' in url:
        url = url.split('?')[0]
    if url.startswith('http'):
        parsed = urlparse(url)
        url = parsed.path
    
    # Pattern: /sales/lead/{LEAD_ID},{SEARCH_TYPE},{SEARCH_ID}
    match = re.search(r'/sales/lead/([^,]+),([^,]+),([^/?]+)', url)
    if match:
        result['lead_id'] = match.group(1)
        result['search_type'] = match.group(2)
        result['search_id'] = match.group(3)
    
    return result


def parse_company_url(url: str) -> Dict[str, Optional[str]]:
    """
    Parse company URL to extract company ID.
    
    Args:
        url: Company URL in format /sales/company/{COMPANY_ID}
        
    Returns:
        Dictionary with company_id and full company_url
    """
    result = {
        'company_id': None,
        'company_url': None
    }
    
    if not url:
        return result
    
    # Remove query parameters if present
    if '?' in url:
        url = url.split('?')[0]
    
    # Extract company ID
    match = re.search(r'/sales/company/(\d+)', url)
    if match:
        company_id = match.group(1)
        result['company_id'] = int(company_id)
        
        # Build full URL
        if url.startswith('/'):
            result['company_url'] = f"https://www.linkedin.com{url}"
        elif url.startswith('http'):
            result['company_url'] = url
        else:
            result['company_url'] = f"https://www.linkedin.com/sales/company/{company_id}"
    
    return result


def parse_urn(urn_string: str) -> Dict[str, Optional[str]]:
    """
    Parse URN string to extract components.
    
    Args:
        urn_string: URN in format urn:li:fs_salesProfile:({LEAD_ID},{SEARCH_TYPE},{SEARCH_ID})
        
    Returns:
        Dictionary with lead_id, search_type, search_id
    """
    result = {
        'lead_id': None,
        'search_type': None,
        'search_id': None
    }
    
    if not urn_string:
        return result
    
    # Pattern: urn:li:fs_salesProfile:({LEAD_ID},{SEARCH_TYPE},{SEARCH_ID})
    match = re.search(r'urn:li:fs_salesProfile:\(([^,]+),([^,]+),([^)]+)\)', urn_string)
    if match:
        result['lead_id'] = match.group(1)
        result['search_type'] = match.group(2)
        result['search_id'] = match.group(3)
    
    return result


def extract_lead_identifiers(profile_element, profile_url: Optional[str]) -> Dict[str, Optional[str]]:
    """
    Extract lead identifiers from profile element and URL.
    
    Args:
        profile_element: Profile element from HTML
        profile_url: Profile URL string
        
    Returns:
        Dictionary with lead_id, lead_urn, search_type, search_id
    """
    result = {
        'lead_id': None,
        'lead_urn': None,
        'search_type': None,
        'search_id': None
    }
    
    # Try to extract from URN first (most reliable)
    parent_li = profile_element.find_parent('li', class_='artdeco-list__item')
    if parent_li:
        scroll_elem = parent_li.find('div', attrs={'data-scroll-into-view': True})
        if scroll_elem:
            urn = scroll_elem.get('data-scroll-into-view', '')
            if urn:
                result['lead_urn'] = urn
                urn_data = parse_urn(urn)
                result['lead_id'] = urn_data['lead_id']
                result['search_type'] = urn_data['search_type']
                result['search_id'] = urn_data['search_id']
    
    # Fallback to URL parsing if URN didn't work
    if not result['lead_id'] and profile_url:
        url_data = parse_lead_url(profile_url)
        if url_data['lead_id']:
            result['lead_id'] = url_data['lead_id']
            result['search_type'] = url_data['search_type']
            result['search_id'] = url_data['search_id']
    
    return result


def extract_company_info(company_link) -> Dict[str, Optional[str]]:
    """
    Extract company information from company link element.
    
    Args:
        company_link: Company link element from HTML
        
    Returns:
        Dictionary with company_id and company_url
    """
    result = {
        'company_id': None,
        'company_url': None
    }
    
    if not company_link:
        return result
    
    href = company_link.get('href', '')
    if href:
        url_data = parse_company_url(href)
        result['company_id'] = url_data['company_id']
        result['company_url'] = url_data['company_url']
    
    return result


def extract_connection_degree(element) -> Optional[str]:
    """Extract connection degree from the badge element."""
    degree_elem = element.find('span', class_='artdeco-entity-lockup__degree')
    if degree_elem:
        text = degree_elem.get_text(strip=True)
        # Extract degree number (e.g., "· 3rd" -> "3rd")
        match = re.search(r'(\d+(?:st|nd|rd|th))', text)
        if match:
            return match.group(1)
    return None


def extract_premium_status(badge_element) -> bool:
    """
    Extract premium membership status from badge element.
    
    Args:
        badge_element: Badge element from HTML
        
    Returns:
        Boolean indicating if person has LinkedIn Premium
    """
    if not badge_element:
        return False
    
    # Check for premium icon
    premium_icon = badge_element.find('li-icon', attrs={'type': 'linkedin-premium-gold-icon'})
    if premium_icon:
        return True
    
    # Check aria-label for premium mention
    aria_label = badge_element.get('aria-label', '')
    if aria_label and 'premium member' in aria_label.lower():
        return True
    
    # Check for premium icon in SVG
    svg = badge_element.find('svg')
    if svg:
        # Check for premium-related paths or attributes
        paths = svg.find_all('path')
        for path in paths:
            fill = path.get('fill', '')
            if fill == '#9f8333':  # Premium gold color
                return True
    
    return False


def extract_activity_status(lockup_element) -> Dict[str, Optional[str]]:
    """
    Extract activity status from lockup element.
    
    Args:
        lockup_element: Lockup element from HTML
        
    Returns:
        Dictionary with is_reachable and last_active
    """
    result = {
        'is_reachable': False,
        'last_active': None
    }
    
    if not lockup_element:
        return result
    
    # Find presence indicator
    presence_indicator = lockup_element.find('div', class_='presence-indicator')
    if not presence_indicator:
        # Try finding in image container
        image_container = lockup_element.find('div', class_='presence-entity')
        if image_container:
            presence_indicator = image_container.find('div', class_='presence-indicator')
    
    if presence_indicator:
        # Check if reachable (not hidden)
        classes = presence_indicator.get('class', [])
        if 'presence-indicator--is-reachable' in classes:
            result['is_reachable'] = True
        elif 'hidden' not in classes:
            result['is_reachable'] = True
        
        # Extract activity text from title
        title = presence_indicator.get('title', '')
        if title:
            result['last_active'] = clean_text(title)
            if 'reachable' in title.lower():
                result['is_reachable'] = True
    
    return result


def extract_viewed_status(lockup_element) -> bool:
    """
    Extract viewed status from lockup element.
    
    Args:
        lockup_element: Lockup element from HTML
        
    Returns:
        Boolean indicating if profile was previously viewed
    """
    if not lockup_element:
        return False
    
    # Check for eyeball icon
    eyeball_icon = lockup_element.find('li-icon', attrs={'type': 'eyeball-icon'})
    if eyeball_icon:
        return True
    
    # Check parent for viewed indicator
    parent = lockup_element.find_parent('div', class_='flex')
    if parent:
        # Look for viewed text or icon
        viewed_elem = parent.find('span', string=re.compile(r'already seen', re.I))
        if viewed_elem:
            return True
        
        # Check for aria-label
        aria_labels = parent.find_all(attrs={'aria-label': re.compile(r'already seen', re.I)})
        if aria_labels:
            return True
    
    return False


def extract_time_info(metadata_text: str) -> tuple:
    """Extract time in role and time in company from metadata text."""
    time_in_role = None
    time_in_company = None
    
    if metadata_text:
        # Pattern: "1 year 8 months in role | 1 year 8 months in company"
        role_match = re.search(r'(.+?)\s+in\s+role', metadata_text)
        if role_match:
            time_in_role = clean_text(role_match.group(1))
        
        company_match = re.search(r'(.+?)\s+in\s+company', metadata_text)
        if company_match:
            time_in_company = clean_text(company_match.group(1))
    
    return time_in_role, time_in_company


def extract_about_text(about_elem) -> Optional[str]:
    """
    Extract full about text, preferring title attribute if truncated.
    
    Enhanced to always check for truncated content and use title attribute.
    """
    if not about_elem:
        return None
    
    # Check if content is truncated
    is_truncated = about_elem.get('data-truncated') is not None
    
    # Always prefer title attribute if available (contains full text)
    title = about_elem.get('title', '')
    if title and title.strip():
        return clean_text(title)
    
    # If not truncated or no title, get visible text
    if not is_truncated:
        text = about_elem.get_text(strip=True)
        # Remove "Show more" button text if present
        text = re.sub(r'\s*…\s*Show more\s*', '', text)
        return clean_text(text) if text else None
    
    return None


def extract_mutual_connections(profile_container) -> Dict:
    """
    Extract mutual connections information.
    
    Args:
        profile_container: Container element for profile
        
    Returns:
        Dictionary with mutual_connections_count and mutual_connections array
    """
    result = {
        'mutual_connections_count': 0,
        'mutual_connections': []
    }
    
    if not profile_container:
        return result
    
    # Find mutual connections button
    mutual_btn = profile_container.find(
        'button',
        attrs={'data-control-name': 'search_spotlight_second_degree_connection'}
    )
    
    if not mutual_btn:
        return result
    
    # Extract count from text
    text = mutual_btn.get_text(strip=True)
    count_match = re.search(r'(\d+)\s+mutual\s+connection', text, re.I)
    if count_match:
        result['mutual_connections_count'] = int(count_match.group(1))
    
    # Extract profile images
    entity_stack = mutual_btn.find('ul', class_='_entityStack_ws13em')
    if entity_stack:
        images = entity_stack.find_all('img', class_='_entity_shcpvh')
        for img in images:
            img_url = img.get('src')
            if img_url:
                connection = {
                    'image_url': img_url,
                    'name': None  # Names usually not available in HTML
                }
                # Try to get name from alt text
                alt = img.get('alt', '')
                if alt and alt.strip():
                    connection['name'] = clean_text(alt)
                result['mutual_connections'].append(connection)
    
    return result


def extract_shared_groups_details(profile_container) -> List[Dict]:
    """
    Extract detailed shared groups information.
    
    Args:
        profile_container: Container element for profile
        
    Returns:
        List of dictionaries with group_name, group_logo_url, group_url
    """
    groups = []
    
    if not profile_container:
        return groups
    
    # Find shared groups button
    shared_groups_elem = profile_container.find(
        'button',
        attrs={'data-control-name': 'search_spotlight_shared_group'}
    )
    
    if not shared_groups_elem:
        return groups
    
    # Extract group logos from entity stack
    entity_stack = shared_groups_elem.find('ul', class_='_entityStack_ws13em')
    if entity_stack:
        images = entity_stack.find_all('img', class_='_entity_shcpvh')
        for img in images:
            img_url = img.get('src')
            if img_url:
                group = {
                    'group_name': None,
                    'group_logo_url': img_url,
                    'group_url': None
                }
                # Try to get name from alt text
                alt = img.get('alt', '')
                if alt and alt.strip():
                    group['group_name'] = clean_text(alt)
                groups.append(group)
    
    return groups


def extract_recently_hired(profile_container) -> Dict[str, Optional[str]]:
    """
    Extract recently hired spotlight information.
    
    Args:
        profile_container: Container element for profile
        
    Returns:
        Dictionary with is_recently_hired and recently_hired_company_logo
    """
    result = {
        'is_recently_hired': False,
        'recently_hired_company_logo': None
    }
    
    if not profile_container:
        return result
    
    # Find recently hired button
    recently_hired_btn = profile_container.find(
        'button',
        attrs={'data-control-name': 'search_spotlight_recently_hired'}
    )
    
    if not recently_hired_btn:
        return result
    
    result['is_recently_hired'] = True
    
    # Extract company logo
    entity_stack = recently_hired_btn.find('ul', class_='_entityStack_ws13em')
    if entity_stack:
        img = entity_stack.find('img', class_='_entity_shcpvh')
        if img:
            logo_url = img.get('src')
            if logo_url:
                result['recently_hired_company_logo'] = logo_url
    
    return result


def extract_recent_posts(profile_container) -> Optional[int]:
    """
    Extract recent posts count from spotlight.
    
    Args:
        profile_container: Container element for profile
        
    Returns:
        Integer count of recent posts, or None
    """
    if not profile_container:
        return None
    
    # Find recent posts button
    recent_posts_btn = profile_container.find(
        'button',
        attrs={'data-control-name': re.compile(r'search_spotlight.*recent.*post', re.I)}
    )
    
    if not recent_posts_btn:
        return None
    
    # Extract count from text or aria-label
    text = recent_posts_btn.get_text(strip=True)
    aria_label = recent_posts_btn.get('aria-label', '')
    
    # Pattern: "X recent posts" or "X recent posts on LinkedIn"
    for source in [text, aria_label]:
        match = re.search(r'(\d+)\s+recent\s+post', source, re.I)
        if match:
            return int(match.group(1))
    
    return None


def extract_profile_data(profile_element) -> Dict:
    """Extract all profile data from a single profile element.
    
    Optimized to cache parent elements and reduce DOM traversals.
    """
    profile_data = {
        # Basic fields
        'name': None,
        'title': None,
        'company': None,
        'location': None,
        'profile_url': None,
        'image_url': None,
        'connection_degree': None,
        'about': None,
        'time_in_role': None,
        'time_in_company': None,
        
        # New identifier fields
        'lead_id': None,
        'lead_urn': None,
        'search_type': None,
        'search_id': None,
        'company_id': None,
        'company_url': None,
        
        # Status fields
        'is_premium_member': False,
        'is_reachable': False,
        'last_active': None,
        'is_viewed': False,
        
        # Network fields
        'mutual_connections_count': 0,
        'mutual_connections': [],
        
        # Spotlight fields
        'is_recently_hired': False,
        'recently_hired_company_logo': None,
        'recent_posts_count': None,
        'shared_groups_details': [],
        
        # Legacy field (for backward compatibility)
        'shared_groups': []
    }
    
    # Find the main lockup container (cache this)
    lockup = profile_element.find('div', class_='artdeco-entity-lockup')
    if not lockup:
        return profile_data
    
    # Cache parent container lookup early to avoid repeated traversals
    parent_container = profile_element.find_parent('div', class_='flex')
    if not parent_container:
        # Try finding the parent li element
        parent_li = profile_element.find_parent('li', class_='artdeco-list__item')
        if parent_li:
            parent_container = parent_li
    
    # Extract name
    name_elem = lockup.find('span', attrs={'data-anonymize': 'person-name'})
    if name_elem:
        profile_data['name'] = clean_text(name_elem.get_text())
    
    # Extract profile URL from name link (try multiple selectors)
    name_link = lockup.find('a', attrs={'data-control-name': 'view_lead_panel_via_search_lead_name'})
    if not name_link:
        # Try alternative selector with dynamic ID
        name_link = lockup.find('a', attrs={'data-lead-search-result': re.compile(r'profile-link-')})
    
    if name_link and name_link.get('href'):
        href = name_link.get('href')
        # Convert relative URL to absolute if needed
        if href.startswith('/'):
            profile_data['profile_url'] = f"https://www.linkedin.com{href}"
        else:
            profile_data['profile_url'] = href
    
    # Extract lead identifiers (uses profile_element, not lockup)
    lead_ids = extract_lead_identifiers(profile_element, profile_data['profile_url'])
    profile_data.update(lead_ids)
    
    # Extract image URL
    img = lockup.find('img', attrs={'data-anonymize': 'headshot-photo'})
    if img and img.get('src'):
        profile_data['image_url'] = img.get('src')
    
    # Extract connection degree and premium status (cache badge lookup)
    badge = lockup.find('div', class_='artdeco-entity-lockup__badge')
    if badge:
        profile_data['connection_degree'] = extract_connection_degree(badge)
        profile_data['is_premium_member'] = extract_premium_status(badge)
    
    # Extract activity status (uses lockup)
    activity = extract_activity_status(lockup)
    profile_data['is_reachable'] = activity['is_reachable']
    profile_data['last_active'] = activity['last_active']
    
    # Extract viewed status (uses lockup)
    profile_data['is_viewed'] = extract_viewed_status(lockup)
    
    # Extract title
    title_elem = lockup.find('span', attrs={'data-anonymize': 'title'})
    if title_elem:
        profile_data['title'] = clean_text(title_elem.get_text())
    
    # Extract company information
    company_link = lockup.find('a', attrs={'data-anonymize': 'company-name'})
    if company_link:
        profile_data['company'] = clean_text(company_link.get_text())
        company_info = extract_company_info(company_link)
        profile_data['company_id'] = company_info['company_id']
        profile_data['company_url'] = company_info['company_url']
    
    # Extract location
    location_elem = lockup.find('span', attrs={'data-anonymize': 'location'})
    if location_elem:
        profile_data['location'] = clean_text(location_elem.get_text())
    
    # Extract time in role and company (cache metadata_elem)
    metadata_elem = lockup.find('div', class_='artdeco-entity-lockup__metadata')
    if metadata_elem:
        metadata_text = metadata_elem.get_text()
        time_in_role, time_in_company = extract_time_info(metadata_text)
        profile_data['time_in_role'] = time_in_role
        profile_data['time_in_company'] = time_in_company
    
    # Extract about section and other data from parent container (already cached)
    if parent_container:
        # Extract about section
        about_elem = parent_container.find('div', attrs={'data-anonymize': 'person-blurb'})
        if about_elem:
            profile_data['about'] = extract_about_text(about_elem)
        
        # Extract mutual connections
        mutual_data = extract_mutual_connections(parent_container)
        profile_data['mutual_connections_count'] = mutual_data['mutual_connections_count']
        profile_data['mutual_connections'] = mutual_data['mutual_connections']
        
        # Extract shared groups details
        profile_data['shared_groups_details'] = extract_shared_groups_details(parent_container)
        # Legacy field for backward compatibility
        if profile_data['shared_groups_details']:
            profile_data['shared_groups'] = ['Shared groups']
        
        # Extract recently hired
        recently_hired_data = extract_recently_hired(parent_container)
        profile_data['is_recently_hired'] = recently_hired_data['is_recently_hired']
        profile_data['recently_hired_company_logo'] = recently_hired_data['recently_hired_company_logo']
        
        # Extract recent posts
        profile_data['recent_posts_count'] = extract_recent_posts(parent_container)
    
    return profile_data


def extract_search_context(soup) -> Dict:
    """
    Extract search context from page.
    
    Args:
        soup: BeautifulSoup object
        
    Returns:
        Dictionary with search_filters, search_id, session_id
    """
    result = {
        'search_filters': {},
        'search_id': None,
        'session_id': None
    }
    
    # Find search navigation link
    search_link = soup.find('a', attrs={'data-x--search-lead-filter': ''})
    if not search_link:
        return result
    
    href = search_link.get('href', '')
    if not href:
        return result
    
    # Parse URL
    parsed = urlparse(href)
    query_params = parse_qs(parsed.query)
    
    # Extract session_id
    if 'sessionId' in query_params:
        result['session_id'] = query_params['sessionId'][0]
    
    # Extract search_id
    if 'recentSearchId' in query_params:
        result['search_id'] = query_params['recentSearchId'][0]
    
    # Parse query parameter (URL-encoded)
    if 'query' in query_params:
        query_str = unquote(query_params['query'][0])
        
        # Try to extract filter information
        # Pattern: filters:List((type:CURRENT_TITLE,values:List((id:9,text:Software%20Engineer,selectionType:INCLUDED))))
        title_match = re.search(r'type:CURRENT_TITLE[^)]*id:(\d+)[^)]*text:([^,)]+)[^)]*selectionType:(\w+)', query_str)
        if title_match:
            result['search_filters'] = {
                'current_title': unquote(title_match.group(2)),
                'filter_id': int(title_match.group(1)),
                'selection_type': title_match.group(3)
            }
    
    return result


def extract_pagination_info(soup, profile_count: int) -> Dict:
    """
    Extract pagination information from page.
    
    Args:
        soup: BeautifulSoup object
        profile_count: Number of profiles found on current page
        
    Returns:
        Dictionary with current_page, total_pages, results_per_page
    """
    result = {
        'current_page': 1,
        'total_pages': 1,
        'results_per_page': profile_count
    }
    
    # Find pagination state
    pagination_state = soup.find('span', class_='artdeco-pagination__state--a11y')
    if pagination_state:
        text = pagination_state.get_text(strip=True)
        # Pattern: "Page 1 of 100"
        match = re.search(r'Page\s+(\d+)\s+of\s+(\d+)', text, re.I)
        if match:
            result['current_page'] = int(match.group(1))
            result['total_pages'] = int(match.group(2))
            
            # Calculate results per page
            if result['total_pages'] > 0:
                # Estimate based on current page (may not be exact)
                result['results_per_page'] = profile_count
    
    return result


def extract_page_metadata(soup) -> Dict:
    """
    Extract page-level metadata.
    
    Args:
        soup: BeautifulSoup object
        
    Returns:
        Dictionary with user_info and application_info
    """
    result = {
        'user_info': {
            'user_member_urn': None,
            'user_name': None
        },
        'application_info': {
            'application_version': None,
            'client_page_instance_id': None,
            'request_ip_country': None,
            'tracking_id': None,
            'tree_id': None
        }
    }
    
    # Extract from __init meta tag
    init_meta = soup.find('meta', attrs={'name': '__init'})
    if init_meta:
        content = init_meta.get('content', '')
        if content:
            try:
                init_data = json.loads(content)
                if 'lix' in init_data:
                    for key, value in init_data['lix'].items():
                        if isinstance(value, dict) and 'trackingInfo' in value:
                            tracking = value['trackingInfo']
                            if tracking and isinstance(tracking, dict) and 'urn' in tracking:
                                urn = tracking.get('urn')
                                if urn and urn.startswith('urn:li:member:'):
                                    result['user_info']['user_member_urn'] = urn
            except (json.JSONDecodeError, KeyError):
                pass
    
    # Extract from applicationInstance meta tag
    app_meta = soup.find('meta', attrs={'name': 'applicationInstance'})
    if app_meta:
        content = app_meta.get('content', '')
        if content:
            try:
                app_data = json.loads(content)
                result['application_info']['application_version'] = app_data.get('version')
            except (json.JSONDecodeError, KeyError):
                pass
    
    # Extract client page instance ID
    client_meta = soup.find('meta', attrs={'name': 'clientPageInstanceId'})
    if client_meta:
        result['application_info']['client_page_instance_id'] = client_meta.get('content')
    
    # Extract request IP country
    country_meta = soup.find('meta', attrs={'name': 'requestIpCountryCode'})
    if country_meta:
        result['application_info']['request_ip_country'] = country_meta.get('content')
    
    # Extract tree ID
    tree_meta = soup.find('meta', attrs={'name': 'treeID'})
    if tree_meta:
        result['application_info']['tree_id'] = tree_meta.get('content')
    
    # Extract user name from header profile image
    header_img = soup.find('img', class_='eah-header-item-content--type-entity')
    if header_img:
        alt = header_img.get('alt', '')
        if alt and "'s profile picture" in alt:
            result['user_info']['user_name'] = alt.replace("'s profile picture", '').strip()
    
    return result


def calculate_data_quality(profile_data: Dict) -> Dict:
    """
    Calculate data quality score and list missing fields.
    
    Args:
        profile_data: Profile data dictionary
        
    Returns:
        Dictionary with data_quality_score and missing_fields
    """
    # Define expected fields (excluding optional ones)
    required_fields = [
        'name', 'title', 'company', 'location', 'profile_url', 'image_url',
        'connection_degree', 'lead_id', 'company_id'
    ]
    
    optional_fields = [
        'about', 'time_in_role', 'time_in_company', 'lead_urn', 'search_type',
        'search_id', 'company_url', 'is_premium_member', 'is_reachable',
        'last_active', 'is_viewed', 'mutual_connections_count', 'mutual_connections',
        'is_recently_hired', 'recent_posts_count', 'shared_groups_details'
    ]
    
    all_fields = required_fields + optional_fields
    
    # Calculate score (weighted: required fields count more)
    # For boolean fields, False is a valid value (not missing)
    boolean_fields = {'is_premium_member', 'is_reachable', 'is_viewed', 'is_recently_hired'}
    
    required_present = sum(1 for field in required_fields if profile_data.get(field) not in [None, [], 0, ''])
    optional_present = sum(1 for field in optional_fields 
                          if field in boolean_fields and profile_data.get(field) is not None
                          or field not in boolean_fields and profile_data.get(field) not in [None, False, [], 0, ''])
    
    # Score: 70% from required fields, 30% from optional
    required_score = (required_present / len(required_fields)) * 70 if required_fields else 0
    optional_score = (optional_present / len(optional_fields)) * 30 if optional_fields else 0
    quality_score = int(required_score + optional_score)
    
    # List missing optional fields (exclude boolean False values)
    missing_fields = []
    for field in optional_fields:
        value = profile_data.get(field)
        if field in boolean_fields:
            if value is None:
                missing_fields.append(field)
        else:
            if value in [None, False, [], 0, '']:
                missing_fields.append(field)
    
    return {
        'data_quality_score': quality_score,
        'missing_fields': missing_fields
    }


def create_output_structure(profiles: List[Dict], page_metadata: Dict, 
                           source_file: str = None, output_format: str = 'hierarchical') -> Dict:
    """
    Create hierarchical output structure.
    
    Args:
        profiles: List of profile dictionaries
        page_metadata: Page metadata dictionary
        source_file: Source HTML file path (optional for API)
        output_format: 'hierarchical' or 'flat'
        
    Returns:
        Structured dictionary or list
    """
    if output_format == 'flat':
        return profiles
    
    # Add data quality to each profile
    for profile in profiles:
        quality = calculate_data_quality(profile)
        profile['data_quality_score'] = quality['data_quality_score']
        profile['missing_fields'] = quality['missing_fields']
    
    return {
        'extraction_metadata': {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'version': '2.0',
            'source_file': source_file or 'api_request'
        },
        'page_metadata': page_metadata,
        'profiles': profiles
    }


def scrape_sales_navigator_html(html_content: str, include_metadata: bool = True) -> Tuple[List[Dict], Dict]:
    """
    Scrape Sales Navigator HTML content and extract all profile data.
    
    Args:
        html_content: HTML content as string
        include_metadata: Whether to include page-level metadata
        
    Returns:
        Tuple of (list of profile dictionaries, page metadata dictionary)
    """
    soup = None
    parser_used = None
    parser_candidates = ['lxml', 'html.parser']
    last_error = None
    for parser_name in parser_candidates:
        try:
            soup = BeautifulSoup(html_content, parser_name)
            parser_used = parser_name
            break
        except Exception as e:
            last_error = str(e)
            continue
    
    if soup is None:
        raise ValueError(f"Invalid HTML content: {last_error}")
    
    # Find all profile entries using the data-x-search-result="LEAD" attribute
    profile_elements = soup.find_all('div', attrs={'data-x-search-result': 'LEAD'})
    
    profile_count = len(profile_elements)
    
    # Extract page metadata
    page_metadata = {
        'search_context': {},
        'pagination': {},
        'user_info': {},
        'application_info': {}
    }
    
    if include_metadata:
        page_metadata['search_context'] = extract_search_context(soup)
        page_metadata['pagination'] = extract_pagination_info(soup, len(profile_elements))
        page_metadata.update(extract_page_metadata(soup))
    
    # Extract profiles
    profiles = []
    for profile_elem in profile_elements:
        try:
            profile_data = extract_profile_data(profile_elem)
            profiles.append(profile_data)
        except Exception:
            continue
    
    return profiles, page_metadata


# ============================================================================
# Database Mapping and Upsert Functions
# ============================================================================

def map_profile_to_contact_data(profile: Dict) -> Dict:
    """
    Map Sales Navigator profile to Contact model fields.
    
    Args:
        profile: Sales Navigator profile dictionary
        
    Returns:
        Dictionary with Contact model fields
    """
    # Parse name
    first_name, last_name = parse_name(profile.get('name'))
    
    # Parse location for text_search
    city, state, country = parse_location(profile.get('location'))
    text_search = f"{city} {state} {country}".strip() if any([city, state, country]) else None
    
    # Infer seniority
    seniority = infer_seniority(profile.get('title'))
    
    # Extract departments
    departments = extract_departments_from_title_about(
        profile.get('title'),
        profile.get('about')
    )
    
    # Get email (may not be in Sales Navigator data)
    email = normalize_text(profile.get('email'), allow_placeholder=True)
    
    # Get title
    title = normalize_text(profile.get('title'), allow_placeholder=True)
    
    # Get mobile phone (may not be in Sales Navigator data)
    mobile_phone = normalize_text(profile.get('mobile_phone'), allow_placeholder=True)
    
    # Get email status (may not be in Sales Navigator data)
    email_status = normalize_text(profile.get('email_status'), allow_placeholder=True)
    
    return {
        'first_name': first_name if first_name != PLACEHOLDER_VALUE else None,
        'last_name': last_name if last_name != PLACEHOLDER_VALUE else None,
        'email': email if email and email != PLACEHOLDER_VALUE else None,
        'title': title if title and title != PLACEHOLDER_VALUE else None,
        'departments': departments if departments else None,
        'mobile_phone': mobile_phone if mobile_phone and mobile_phone != PLACEHOLDER_VALUE else None,
        'email_status': email_status if email_status and email_status != PLACEHOLDER_VALUE else None,
        'text_search': text_search,
        'seniority': seniority if seniority != PLACEHOLDER_VALUE else None,
        'status': PLACEHOLDER_VALUE,
    }


def map_profile_to_contact_metadata(profile: Dict, linkedin_url: str) -> Dict:
    """
    Map Sales Navigator profile to ContactMetadata fields.
    
    Args:
        profile: Sales Navigator profile dictionary
        linkedin_url: Converted LinkedIn URL (standard format)
        
    Returns:
        Dictionary with ContactMetadata fields
    """
    # Parse location
    city, state, country = parse_location(profile.get('location'))
    
    # Get Sales Navigator URL
    linkedin_sales_url = normalize_text(profile.get('profile_url'), allow_placeholder=True)
    
    # Get other fields (may not be in Sales Navigator data)
    facebook_url = normalize_text(profile.get('facebook_url'), allow_placeholder=True)
    twitter_url = normalize_text(profile.get('twitter_url'), allow_placeholder=True)
    website = normalize_text(profile.get('website'), allow_placeholder=True)
    work_direct_phone = normalize_text(profile.get('work_direct_phone'), allow_placeholder=True)
    home_phone = normalize_text(profile.get('home_phone'), allow_placeholder=True)
    other_phone = normalize_text(profile.get('other_phone'), allow_placeholder=True)
    stage = normalize_text(profile.get('stage'), allow_placeholder=True)
    
    return {
        'linkedin_url': linkedin_url if linkedin_url != PLACEHOLDER_VALUE else PLACEHOLDER_VALUE,
        'linkedin_sales_url': linkedin_sales_url if linkedin_sales_url and linkedin_sales_url != PLACEHOLDER_VALUE else PLACEHOLDER_VALUE,
        'facebook_url': facebook_url if facebook_url and facebook_url != PLACEHOLDER_VALUE else PLACEHOLDER_VALUE,
        'twitter_url': twitter_url if twitter_url and twitter_url != PLACEHOLDER_VALUE else PLACEHOLDER_VALUE,
        'website': website if website and website != PLACEHOLDER_VALUE else PLACEHOLDER_VALUE,
        'work_direct_phone': work_direct_phone if work_direct_phone and work_direct_phone != PLACEHOLDER_VALUE else PLACEHOLDER_VALUE,
        'home_phone': home_phone if home_phone and home_phone != PLACEHOLDER_VALUE else PLACEHOLDER_VALUE,
        'city': city if city != PLACEHOLDER_VALUE else PLACEHOLDER_VALUE,
        'state': state if state != PLACEHOLDER_VALUE else PLACEHOLDER_VALUE,
        'country': country if country != PLACEHOLDER_VALUE else PLACEHOLDER_VALUE,
        'other_phone': other_phone if other_phone and other_phone != PLACEHOLDER_VALUE else PLACEHOLDER_VALUE,
        'stage': stage if stage and stage != PLACEHOLDER_VALUE else PLACEHOLDER_VALUE,
    }


def map_profile_to_company_data(profile: Dict) -> Dict:
    """
    Map Sales Navigator profile company info to Company model fields.
    
    Args:
        profile: Sales Navigator profile dictionary
        
    Returns:
        Dictionary with Company model fields
    """
    company_name = normalize_text(profile.get('company'), allow_placeholder=True)
    
    if not company_name or company_name == PLACEHOLDER_VALUE:
        return {}
    
    # Extract technologies from about (if available)
    technologies = []
    about = profile.get('about')
    if about:
        # Simple technology extraction (can be enhanced)
        tech_patterns = [
            r'\b(python|java|javascript|typescript|react|vue|angular|node\.js|django|flask|spring)\b',
            r'\b(aws|azure|gcp|docker|kubernetes|terraform)\b',
            r'\b(mysql|postgresql|mongodb|redis|elasticsearch)\b',
        ]
        about_lower = about.lower()
        for pattern in tech_patterns:
            matches = re.findall(pattern, about_lower, re.IGNORECASE)
            technologies.extend(matches)
        technologies = list(set(technologies)) if technologies else []
    
    # Build text_search from company name
    text_search = company_name
    
    return {
        'name': company_name,
        'employees_count': None,  # Not available in Sales Navigator
        'industries': None,  # Not available in Sales Navigator
        'keywords': None,  # Not available in Sales Navigator
        'address': None,  # Not available in Sales Navigator
        'annual_revenue': None,  # Not available in Sales Navigator
        'total_funding': None,  # Not available in Sales Navigator
        'technologies': technologies if technologies else None,
        'text_search': text_search,
    }


def map_profile_to_company_metadata(profile: Dict) -> Dict:
    """
    Map Sales Navigator profile company info to CompanyMetadata fields.
    
    Args:
        profile: Sales Navigator profile dictionary
        
    Returns:
        Dictionary with CompanyMetadata fields
    """
    company_url = normalize_text(profile.get('company_url'), allow_placeholder=True)
    company_name = normalize_text(profile.get('company'), allow_placeholder=True)
    
    return {
        'linkedin_url': company_url if company_url and company_url != PLACEHOLDER_VALUE else None,
        'linkedin_sales_url': company_url if company_url and company_url != PLACEHOLDER_VALUE else None,
        'facebook_url': None,  # Not available in Sales Navigator
        'twitter_url': None,  # Not available in Sales Navigator
        'website': None,  # Not available in Sales Navigator
        'company_name_for_emails': company_name if company_name and company_name != PLACEHOLDER_VALUE else None,
        'phone_number': None,  # Not available in Sales Navigator
        'latest_funding': None,  # Not available in Sales Navigator
        'latest_funding_amount': None,  # Not available in Sales Navigator
        'last_raised_at': None,  # Not available in Sales Navigator
        'city': None,  # Not available in Sales Navigator
        'state': None,  # Not available in Sales Navigator
        'country': None,  # Not available in Sales Navigator
    }


async def upsert_contact_with_metadata(
    session: AsyncSession,
    profile: Dict,
    company_uuid: Optional[str] = None
) -> Tuple[Contact, ContactMetadata, bool]:
    """
    Upsert contact and metadata (check by UUID, update if exists, create if new).
    
    Args:
        session: Database session
        profile: Sales Navigator profile dictionary
        company_uuid: Optional company UUID to link contact to
        
    Returns:
        Tuple of (Contact, ContactMetadata, is_created)
    """
    # Convert Sales Navigator URL to LinkedIn URL
    profile_url = profile.get('profile_url')
    linkedin_url = convert_sales_nav_url_to_linkedin(profile_url)
    
    # If conversion failed, use Sales Navigator URL as fallback
    if linkedin_url == PLACEHOLDER_VALUE:
        linkedin_url = normalize_text(profile_url, allow_placeholder=True) or PLACEHOLDER_VALUE
    
    # Generate contact UUID
    email = profile.get('email')
    contact_uuid = generate_contact_uuid(linkedin_url, email)
    
    # Check if contact exists using Connectra
    existing_contact = None
    try:
        async with ConnectraClient() as client:
            existing_contact_data = await client.get_contact_by_uuid(contact_uuid)
            if existing_contact_data:
                # Convert dict to Contact-like object for compatibility
                # Note: This is a temporary compatibility layer
                existing_contact = type('Contact', (), existing_contact_data)()
    except Exception as exc:
        logger.warning(f"Connectra contact lookup failed, assuming new contact: {exc}")
        existing_contact = None
    
    now = datetime.now(UTC).replace(tzinfo=None)
    is_created = False
    
    if existing_contact:
        # Update existing contact
        contact = existing_contact
        contact_data = map_profile_to_contact_data(profile)
        
        # Update fields
        for key, value in contact_data.items():
            if hasattr(contact, key) and value is not None:
                setattr(contact, key, value)
        
        # Update company_id if provided
        if company_uuid:
            contact.company_id = company_uuid
        
        contact.updated_at = now
        await session.flush()
    else:
        # Create new contact
        is_created = True
        contact_data = map_profile_to_contact_data(profile)
        
        contact = Contact(
            uuid=contact_uuid,
            company_id=company_uuid,
            created_at=now,
            updated_at=now,
            **contact_data
        )
        session.add(contact)
        await session.flush()
    
    # Upsert contact metadata
    contact_meta_data = map_profile_to_contact_metadata(profile, linkedin_url)
    
    # Check if metadata exists
    existing_meta = await fetch_contact_metadata_by_uuid(session, contact_uuid)
    
    if existing_meta:
        # Update existing metadata
        contact_meta = existing_meta
        for key, value in contact_meta_data.items():
            if hasattr(contact_meta, key):
                setattr(contact_meta, key, value)
        await session.flush()
    else:
        # Create new metadata
        contact_meta = ContactMetadata(
            uuid=contact_uuid,
            **contact_meta_data
        )
        session.add(contact_meta)
        await session.flush()
    
    return contact, contact_meta, is_created


async def upsert_company_with_metadata(
    session: AsyncSession,
    profile: Dict
) -> Tuple[Optional[Company], Optional[CompanyMetadata], bool]:
    """
    Upsert company and metadata (check by name OR linkedin_url, update if exists, create if new).
    
    Args:
        session: Database session
        profile: Sales Navigator profile dictionary
        
    Returns:
        Tuple of (Company, CompanyMetadata, is_created) or (None, None, False) if no company data
    """
    company_name = normalize_text(profile.get('company'), allow_placeholder=True)
    company_url = normalize_text(profile.get('company_url'), allow_placeholder=True)
    
    if not company_name or company_name == PLACEHOLDER_VALUE:
        return None, None, False
    
    # Generate company UUID
    company_uuid = generate_company_uuid(company_name, company_url)
    
    # Check session's new objects first (companies added in this transaction but not yet committed)
    existing_company = None
    try:
        # Check if there's a pending Company object with this UUID in the session
        for obj in list(session.new):
            if isinstance(obj, Company) and obj.uuid == company_uuid:
                existing_company = obj
                break
    except Exception:
        pass
    
    # If not found in new objects, check database
    if not existing_company:
        # Check if company exists using Connectra
        existing_company = None
        try:
            async with ConnectraClient() as client:
                existing_company_data = await client.get_company_by_uuid(company_uuid)
                if existing_company_data:
                    # Convert dict to Company-like object for compatibility
                    # Note: This is a temporary compatibility layer
                    existing_company = type('Company', (), existing_company_data)()
        except Exception as exc:
            logger.warning(f"Connectra company lookup failed, assuming new company: {exc}")
            existing_company = None
    
    # If not found by UUID, check by name OR linkedin_url
    if not existing_company:
        linkedin_repo = LinkedInRepository()
        
        # Try to find by LinkedIn URL
        if company_url and company_url != PLACEHOLDER_VALUE:
            company_match = await linkedin_repo.find_company_by_exact_linkedin_url(session, company_url)
            if company_match:
                existing_company, _ = company_match
        
        # If still not found, try to find by name (case-insensitive)
        if not existing_company:
            normalized_company_name = normalize_text(company_name, allow_placeholder=True)
            if normalized_company_name and normalized_company_name != PLACEHOLDER_VALUE:
                stmt = select(Company).where(Company.name.ilike(normalized_company_name)).limit(1)
                result = await session.execute(stmt)
                existing_company = result.scalar_one_or_none()
    
    now = datetime.now(UTC).replace(tzinfo=None)
    is_created = False
    
    if existing_company:
        # Update existing company
        company = existing_company
        company_data = map_profile_to_company_data(profile)
        
        # Update fields
        for key, value in company_data.items():
            if hasattr(company, key) and value is not None:
                setattr(company, key, value)
        
        company.updated_at = now
        await session.flush()
        company_uuid = company.uuid  # Use existing UUID
    else:
        # Create new company
        is_created = True
        company_data = map_profile_to_company_data(profile)
        
        company = Company(
            uuid=company_uuid,
            created_at=now,
            updated_at=now,
            **company_data
        )
        session.add(company)
        await session.flush()
    
    # Upsert company metadata
    company_meta_data = map_profile_to_company_metadata(profile)
    
    # Check if metadata exists
    existing_meta = await fetch_company_metadata_by_uuid(session, company_uuid)
    
    if existing_meta:
        # Update existing metadata
        company_meta = existing_meta
        for key, value in company_meta_data.items():
            if hasattr(company_meta, key) and value is not None:
                setattr(company_meta, key, value)
        await session.flush()
    else:
        # Create new metadata
        company_meta = CompanyMetadata(
            uuid=company_uuid,
            **company_meta_data
        )
        session.add(company_meta)
        await session.flush()
    
    return company, company_meta, is_created


async def save_profiles_to_database(
    session: AsyncSession,
    profiles: List[Dict]
) -> Dict:
    """
    Process all profiles, save to database via Connectra API, return summary.
    
    Uses Connectra's bulk upsert API which:
    - Handles UUID generation
    - Automatically creates or updates records
    - Manages both main and metadata tables
    - Handles Elasticsearch indexing
    
    Args:
        session: Database session (kept for compatibility, not used for writes)
        profiles: List of Sales Navigator profile dictionaries
        
    Returns:
        Dictionary with saved records and summary:
        {
            'contacts': List[Dict],  # Contact data from Connectra
            'contacts_metadata': List[Dict],  # Contact metadata (embedded)
            'companies': List[Dict],  # Company data from Connectra
            'companies_metadata': List[Dict],  # Company metadata (embedded)
            'summary': {
                'total_profiles': int,
                'contacts_created': int,
                'contacts_updated': int,
                'companies_created': int,
                'companies_updated': int,
                'errors': List[str]
            }
        }
    """
    summary = {
        'total_profiles': len(profiles),
        'contacts_created': 0,
        'contacts_updated': 0,
        'companies_created': 0,
        'companies_updated': 0,
        'errors': []
    }
    
    if not profiles:
        return {
            'contacts': [],
            'contacts_metadata': [],
            'companies': [],
            'companies_metadata': [],
            'summary': summary
        }
    
    now = datetime.now(UTC).replace(tzinfo=None)
    
    # Step 1: Prepare data structures
    company_uuid_map: Dict[str, Dict] = {}  # uuid -> company_data
    contact_data_list: List[Dict] = []  # List of all contact data with company linkage
    
    for idx, profile in enumerate(profiles):
        try:
            # Generate company UUID and prepare company data if company exists
            company_name = normalize_text(profile.get('company'), allow_placeholder=True)
            company_url = normalize_text(profile.get('company_url'), allow_placeholder=True)
            company_uuid = None
            
            if company_name and company_name != PLACEHOLDER_VALUE:
                company_uuid = generate_company_uuid(company_name, company_url)
                if company_uuid not in company_uuid_map:
                    # Prepare company data for bulk upsert
                    company_data = map_profile_to_company_data(profile)
                    company_meta_data = map_profile_to_company_metadata(profile)
                    
                    # Merge main data and metadata into single object for Connectra
                    company_full_data = {**company_data, **company_meta_data}
                    company_full_data['uuid'] = company_uuid
                    company_uuid_map[company_uuid] = company_full_data
            
            # Prepare contact data
            profile_url = profile.get('profile_url')
            linkedin_url = convert_sales_nav_url_to_linkedin(profile_url)
            if linkedin_url == PLACEHOLDER_VALUE:
                linkedin_url = normalize_text(profile_url, allow_placeholder=True) or PLACEHOLDER_VALUE
            
            email = profile.get('email')
            contact_uuid = generate_contact_uuid(linkedin_url, email)
            
            # Prepare contact data for bulk upsert
            contact_data = map_profile_to_contact_data(profile)
            contact_meta_data = map_profile_to_contact_metadata(profile, linkedin_url)
            
            # Merge main data and metadata into single object for Connectra
            contact_full_data = {**contact_data, **contact_meta_data}
            contact_full_data['uuid'] = contact_uuid
            contact_full_data['company_id'] = company_uuid
            contact_data_list.append(contact_full_data)
            
        except Exception as e:
            summary['errors'].append(f"Error preparing profile {idx + 1}: {str(e)}")
            logger.error(f"Error preparing profile {idx + 1}: {str(e)}")
            continue
    
    # Step 2: Bulk upsert via Connectra API
    try:
        async with ConnectraClient() as client:
            # Bulk upsert companies first
            if company_uuid_map:
                companies_list = list(company_uuid_map.values())
                company_result = await client.bulk_upsert_companies(companies_list)
                
                if company_result and 'data' in company_result:
                    result_data = company_result['data']
                    summary['companies_created'] = result_data.get('created', 0)
                    summary['companies_updated'] = result_data.get('updated', 0)
                else:
                    # Fallback if response structure is different
                    summary['companies_created'] = company_result.get('created', len(companies_list) // 2)
                    summary['companies_updated'] = company_result.get('updated', len(companies_list) // 2)
            
            # Bulk upsert contacts
            if contact_data_list:
                contact_result = await client.bulk_upsert_contacts(contact_data_list)
                
                if contact_result and 'data' in contact_result:
                    result_data = contact_result['data']
                    summary['contacts_created'] = result_data.get('created', 0)
                    summary['contacts_updated'] = result_data.get('updated', 0)
                else:
                    # Fallback if response structure is different
                    summary['contacts_created'] = contact_result.get('created', len(contact_data_list) // 2)
                    summary['contacts_updated'] = contact_result.get('updated', len(contact_data_list) // 2)
        
    except Exception as e:
        error_msg = f"Error during bulk upsert via Connectra: {str(e)}"
        summary['errors'].append(error_msg)
        logger.error(error_msg)
        raise
    
    # Step 3: Return results
    # Note: With Connectra, we return the data that was sent
    # The actual saved records would need to be fetched if detailed response is needed
    return {
        'contacts': contact_data_list,
        'contacts_metadata': contact_data_list,  # Metadata is embedded
        'companies': list(company_uuid_map.values()),
        'companies_metadata': list(company_uuid_map.values()),  # Metadata is embedded
        'summary': summary
    }

