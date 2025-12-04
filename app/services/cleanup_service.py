"""Service for cleaning/normalizing contact and company data."""

import json
import re
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.companies import Company, CompanyMetadata
from app.models.contacts import Contact, ContactMetadata

logger = get_logger(__name__)

# #region agent log
DEBUG_LOG_PATH = r"d:\code\ayan\contact360\.cursor\debug.log"
# #endregion


def clean_text(value: Optional[str]) -> Optional[str]:
    """
    Clean text value by:
    1. Removing special characters (keep only alphanumeric, spaces, hyphens, periods)
    2. Converting "_" and "" to None (NULL)
    
    Args:
        value: The text value to clean
        
    Returns:
        Cleaned text or None if value is "_" or empty string
    """
    # #region agent log
    try:
        with open(DEBUG_LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"cleanup_service.py:clean_text:entry","message":"clean_text called","data":{"value":value,"type":str(type(value))},"timestamp":int(__import__('time').time()*1000)})+'\n')
    except: pass
    # #endregion
    
    if value is None:
        return None
    
    # Convert to string if not already
    if not isinstance(value, str):
        value = str(value)
    
    # Convert "_" and empty strings to None
    if value == "_" or value == "":
        return None
    
    # Remove special characters, keep only alphanumeric, spaces, hyphens, and periods
    cleaned = re.sub(r'[^a-zA-Z0-9\s\-\.]', '', value)
    
    # Strip whitespace
    cleaned = cleaned.strip()
    
    # Return None if result is empty
    if cleaned == "":
        return None
    
    # #region agent log
    try:
        with open(DEBUG_LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"cleanup_service.py:clean_text:exit","message":"clean_text result","data":{"original":value,"cleaned":cleaned,"changed":value!=cleaned},"timestamp":int(__import__('time').time()*1000)})+'\n')
    except: pass
    # #endregion
    
    return cleaned


def clean_url(value: Optional[str]) -> Optional[str]:
    """
    Clean and fix malformed URLs.
    
    Fixes common issues:
    - Missing "://" after http/https (e.g., "httpwww.linkedin.com" -> "https://www.linkedin.com")
    - Missing "/" in LinkedIn URLs (e.g., "linkedin.comin" -> "linkedin.com/in/")
    - Normalizes http to https
    - Removes invalid characters while preserving URL structure
    
    Args:
        value: The URL value to clean
        
    Returns:
        Cleaned URL or None if value is invalid/empty
    """
    if value is None:
        return None
    
    if not isinstance(value, str):
        value = str(value)
    
    # Convert "_" and empty strings to None
    if value == "_" or value == "":
        return None
    
    # Strip whitespace
    value = value.strip()
    if not value:
        return None
    
    # Fix missing "://" after http/https
    # First check if it already has :// to avoid double-adding
    if not re.match(r'^https?://', value, re.IGNORECASE):
        # Pattern: "httpwww" or "httpswww" -> "http://www"
        if re.match(r'^https?www\.', value, re.IGNORECASE):
            value = re.sub(r'^(https?)(www\.)', r'\1://\2', value, flags=re.IGNORECASE)
        # Pattern: "http" or "https" followed by non-slash -> "http://"
        elif re.match(r'^https?[^/]', value, re.IGNORECASE):
            value = re.sub(r'^(https?)([^/])', r'\1://\2', value, re.IGNORECASE)
    
    # Fix LinkedIn URLs: "linkedin.comin" -> "linkedin.com/in/"
    if 'linkedin.com' in value.lower():
        # Fix "linkedin.comin" -> "linkedin.com/in/"
        value = re.sub(r'linkedin\.comin([^/])', r'linkedin.com/in/\1', value, flags=re.IGNORECASE)
        # Fix "linkedin.com/in" without trailing slash if needed
        value = re.sub(r'linkedin\.com/in([^/])', r'linkedin.com/in/\1', value, flags=re.IGNORECASE)
        # Ensure https
        if value.startswith('http://'):
            value = 'https://' + value[7:]
        elif not value.startswith('http'):
            value = 'https://' + value
    
    # Normalize http to https for all URLs
    if value.startswith('http://'):
        value = 'https://' + value[7:]
    
    # Basic validation: should start with http:// or https://
    if not re.match(r'^https?://', value, re.IGNORECASE):
        # Try to add https:// if it looks like a domain
        if re.match(r'^[a-zA-Z0-9][a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', value):
            value = 'https://' + value
    
    # Remove invalid characters but preserve URL structure
    # Keep: alphanumeric, :, /, ?, #, [, ], @, ., -, _, ~, %, +, =, &, ;
    cleaned = re.sub(r'[^a-zA-Z0-9:/?#\[\]@._~%+=&;-]', '', value)
    
    # Final validation: must be a valid URL format
    if not re.match(r'^https?://[^\s]+', cleaned):
        return None
    
    return cleaned


def clean_email(value: Optional[str]) -> Optional[str]:
    """
    Clean and fix malformed email addresses.
    
    Fixes common issues:
    - Missing "@" symbol (e.g., "name.domain.com" -> "name@domain.com" if pattern detected)
    - Removes invalid characters
    - Validates basic email format
    
    Args:
        value: The email value to clean
        
    Returns:
        Cleaned email or None if value is invalid/empty
    """
    if value is None:
        return None
    
    if not isinstance(value, str):
        value = str(value)
    
    # Convert "_" and empty strings to None
    if value == "_" or value == "":
        return None
    
    # Strip whitespace
    value = value.strip()
    if not value:
        return None
    
    # If already has @, just clean it
    if '@' in value:
        # Remove invalid characters but keep email-valid chars: alphanumeric, @, ., -, _, +
        cleaned = re.sub(r'[^a-zA-Z0-9@._+-]', '', value)
        # Basic validation: should have format "local@domain"
        if re.match(r'^[a-zA-Z0-9._+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', cleaned):
            return cleaned.lower()
        return None
    
    # Try to fix missing @
    # Pattern 1: "name.domain.com" -> "name@domain.com" (at least 2 dots)
    match = re.match(r'^([a-zA-Z0-9._+-]+)\.([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})$', value)
    if match:
        local_part = match.group(1)
        domain = match.group(2)
        # Validate domain looks like a real domain
        if re.match(r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', domain):
            email = f"{local_part}@{domain}"
            if re.match(r'^[a-zA-Z0-9._+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
                return email.lower()
    
    # Pattern 2: "name.domain.com" where domain.com is a common TLD
    # Try to find the last dot before a common TLD and insert @ before domain
    # e.g., "laurens.goedgebeurabbvie.com" -> "laurens.goedgebeur@abbvie.com"
    tld_pattern = r'\.(com|org|net|edu|gov|io|co|uk|de|fr|it|es|nl|be|au|ca|jp|cn|in|br|mx|ru|za|se|no|dk|fi|pl|cz|gr|ie|pt|at|ch|tr|il|nz|sg|hk|my|th|ph|id|vn|kr|tw|ae|sa|eg|ma|dz|tn|ly|sd|so|et|ke|tz|ug|rw|gh|ng|za|zm|bw|mw|mz|ao|cd|cg|cm|ci|sn|ml|bf|ne|td|cf|ga|gq|st|gw|cv|mr|dj|km|sc|mu|re|yt|pm|wf|pf|nc|vu|fj|pg|sb|nc|pw|fm|mh|ki|nr|tv|to|ws|as|gu|mp|vi|pr|do|ht|jm|bb|tt|lc|vc|gd|ag|dm|kn|bs|bz|cr|pa|ni|hn|sv|gt|bz|gy|sr|gf|co|ec|pe|bo|py|uy|ar|cl|fk|gs|tf|aq|bv|hm|sj|no|fo|gl|is|ax|ad|mc|sm|va|li|lu|mt|cy|gi|je|gg|im|ie|gb)$'
    match = re.search(tld_pattern, value, re.IGNORECASE)
    if match:
        # Find the position of the TLD
        tld_start = match.start()
        # Look backwards for a dot to find where domain starts
        # Try to split: everything before last dot before TLD = local, rest = domain
        before_tld = value[:tld_start]
        # Find the last dot in the part before TLD
        last_dot_idx = before_tld.rfind('.')
        if last_dot_idx > 0:
            # Split at the last dot: local@domain.tld
            potential_local = before_tld[:last_dot_idx]
            potential_domain = before_tld[last_dot_idx+1:] + match.group(0)
            # Validate - domain should be reasonable length (at least 2 chars)
            if (len(potential_local) > 0 and len(potential_domain) >= 4 and
                re.match(r'^[a-zA-Z0-9._+-]+$', potential_local) and 
                re.match(r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', potential_domain)):
                email = f"{potential_local}@{potential_domain}"
                if re.match(r'^[a-zA-Z0-9._+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
                    return email.lower()
        # If no dot found before TLD, try splitting at a reasonable point
        # Look for common patterns like "namecompany.com" -> "name@company.com"
        # Try to find where a name might end (look for lowercase to uppercase transition or common name endings)
        if len(before_tld) > 3:
            # Try splitting at various points, preferring shorter local parts
            for split_pos in range(max(3, len(before_tld) - 15), len(before_tld) - 2):
                potential_local = before_tld[:split_pos]
                potential_domain = before_tld[split_pos:] + match.group(0)
                if (len(potential_local) >= 2 and len(potential_domain) >= 4 and
                    re.match(r'^[a-zA-Z0-9._+-]+$', potential_local) and 
                    re.match(r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', potential_domain)):
                    email = f"{potential_local}@{potential_domain}"
                    if re.match(r'^[a-zA-Z0-9._+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
                        return email.lower()
    
    # If we can't fix it, return None (invalid email)
    return None


def clean_array(value: Optional[list]) -> Optional[list]:
    """
    Clean array by cleaning each element.
    
    Args:
        value: List of strings to clean
        
    Returns:
        Cleaned list or None if all elements are None/empty
    """
    if value is None:
        return None
    
    if not isinstance(value, list):
        return None
    
    cleaned_list = []
    for item in value:
        cleaned_item = clean_text(item)
        if cleaned_item is not None:
            cleaned_list.append(cleaned_item)
    
    return cleaned_list if cleaned_list else None


class CleanupService:
    """Service for cleaning contact and company data."""

    def __init__(self):
        """Initialize cleanup service."""
        # Import cleaning utilities from data scripts
        try:
            import sys
            from pathlib import Path
            
            # Add scripts/data to path if not already there
            scripts_path = Path(__file__).parent.parent.parent.parent / "scripts" / "data"
            if str(scripts_path) not in sys.path:
                sys.path.insert(0, str(scripts_path))
            
            from utils.cleaning import (
                clean_company_name,
                clean_keyword_array,
                clean_title,
            )
            
            self.clean_company_name = clean_company_name
            self.clean_keyword_array = clean_keyword_array
            self.clean_title = clean_title
        except ImportError as e:
            logger.warning("Could not import cleaning utilities from data scripts: %s", e)
            # Fallback to basic cleaning
            self.clean_company_name = lambda x: clean_text(x)
            self.clean_keyword_array = clean_array
            self.clean_title = clean_text

    async def clean_contact(
        self,
        session: AsyncSession,
        contact_uuid: str,
    ) -> dict:
        """
        Clean a single contact and its metadata.
        
        Args:
            session: Database session
            contact_uuid: Contact UUID
            
        Returns:
            Dictionary with cleanup results
        """
        # #region agent log
        try:
            with open(DEBUG_LOG_PATH, 'a', encoding='utf-8') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"ALL","location":"cleanup_service.py:clean_contact:entry","message":"clean_contact started","data":{"contact_uuid":contact_uuid},"timestamp":int(__import__('time').time()*1000)})+'\n')
        except: pass
        # #endregion
        
        fields_updated = 0
        
        try:
            # Get contact
            result = await session.execute(
                select(Contact).where(Contact.uuid == contact_uuid)
            )
            contact = result.scalar_one_or_none()
            
            # #region agent log
            try:
                with open(DEBUG_LOG_PATH, 'a', encoding='utf-8') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"cleanup_service.py:clean_contact:contact_found","message":"Contact lookup result","data":{"found":contact is not None,"email":getattr(contact,'email',None) if contact else None},"timestamp":int(__import__('time').time()*1000)})+'\n')
            except: pass
            # #endregion
            
            if not contact:
                return {
                    "uuid": contact_uuid,
                    "success": False,
                    "fields_updated": 0,
                    "error": "Contact not found",
                }
            
            # Clean contact fields
            if contact.title:
                cleaned_title = self.clean_title(contact.title)
                if cleaned_title != contact.title:
                    contact.title = cleaned_title
                    fields_updated += 1
            
            if contact.departments:
                cleaned_departments = self.clean_keyword_array(contact.departments)
                if cleaned_departments != contact.departments:
                    contact.departments = cleaned_departments
                    fields_updated += 1
            
            # Clean email field with specialized email cleaner
            if contact.email:
                # #region agent log
                try:
                    with open(DEBUG_LOG_PATH, 'a', encoding='utf-8') as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"post-fix","hypothesisId":"C","location":"cleanup_service.py:clean_contact:email_before","message":"Before cleaning email","data":{"field":"email","value":contact.email,"type":str(type(contact.email))},"timestamp":int(__import__('time').time()*1000)})+'\n')
                except: pass
                # #endregion
                cleaned_email = clean_email(contact.email)
                # #region agent log
                try:
                    with open(DEBUG_LOG_PATH, 'a', encoding='utf-8') as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"post-fix","hypothesisId":"C","location":"cleanup_service.py:clean_contact:email_after","message":"After cleaning email","data":{"field":"email","original":contact.email,"cleaned":cleaned_email,"changed":cleaned_email!=contact.email if cleaned_email else False,"will_update":cleaned_email!=contact.email if cleaned_email else False},"timestamp":int(__import__('time').time()*1000)})+'\n')
                except: pass
                # #endregion
                if cleaned_email and cleaned_email != contact.email:
                    contact.email = cleaned_email
                    fields_updated += 1
            
            # Clean other text fields
            text_fields = ["first_name", "last_name", "mobile_phone", "email_status", "seniority"]
            for field_name in text_fields:
                current_value = getattr(contact, field_name, None)
                # #region agent log
                try:
                    with open(DEBUG_LOG_PATH, 'a', encoding='utf-8') as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"post-fix","hypothesisId":"C","location":"cleanup_service.py:clean_contact:text_field_before","message":"Before cleaning text field","data":{"field":field_name,"value":current_value,"type":str(type(current_value))},"timestamp":int(__import__('time').time()*1000)})+'\n')
                except: pass
                # #endregion
                if current_value:
                    cleaned_value = clean_text(current_value)
                    # #region agent log
                    try:
                        with open(DEBUG_LOG_PATH, 'a', encoding='utf-8') as f:
                            f.write(json.dumps({"sessionId":"debug-session","runId":"post-fix","hypothesisId":"C","location":"cleanup_service.py:clean_contact:text_field_after","message":"After cleaning text field","data":{"field":field_name,"original":current_value,"cleaned":cleaned_value,"changed":cleaned_value!=current_value,"will_update":cleaned_value!=current_value},"timestamp":int(__import__('time').time()*1000)})+'\n')
                    except: pass
                    # #endregion
                    if cleaned_value != current_value:
                        setattr(contact, field_name, cleaned_value)
                        fields_updated += 1
            
            # Clean contact metadata
            result = await session.execute(
                select(ContactMetadata).where(ContactMetadata.uuid == contact_uuid)
            )
            metadata = result.scalar_one_or_none()
            
            # #region agent log
            try:
                with open(DEBUG_LOG_PATH, 'a', encoding='utf-8') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"cleanup_service.py:clean_contact:metadata_found","message":"Metadata lookup result","data":{"found":metadata is not None,"linkedin_url":getattr(metadata,'linkedin_url',None) if metadata else None,"website":getattr(metadata,'website',None) if metadata else None},"timestamp":int(__import__('time').time()*1000)})+'\n')
            except: pass
            # #endregion
            
            if metadata:
                # Clean URL fields with specialized URL cleaner
                url_fields = ["linkedin_url", "facebook_url", "twitter_url", "website"]
                for field_name in url_fields:
                    current_value = getattr(metadata, field_name, None)
                    # #region agent log
                    try:
                        with open(DEBUG_LOG_PATH, 'a', encoding='utf-8') as f:
                            f.write(json.dumps({"sessionId":"debug-session","runId":"post-fix","hypothesisId":"B","location":"cleanup_service.py:clean_contact:url_field_before","message":"Before cleaning URL field","data":{"field":field_name,"value":current_value,"type":str(type(current_value))},"timestamp":int(__import__('time').time()*1000)})+'\n')
                    except: pass
                    # #endregion
                    if current_value:
                        cleaned_value = clean_url(current_value)
                        # #region agent log
                        try:
                            with open(DEBUG_LOG_PATH, 'a', encoding='utf-8') as f:
                                f.write(json.dumps({"sessionId":"debug-session","runId":"post-fix","hypothesisId":"B","location":"cleanup_service.py:clean_contact:url_field_after","message":"After cleaning URL field","data":{"field":field_name,"original":current_value,"cleaned":cleaned_value,"changed":cleaned_value!=current_value if cleaned_value else False,"will_update":cleaned_value!=current_value if cleaned_value else False},"timestamp":int(__import__('time').time()*1000)})+'\n')
                        except: pass
                        # #endregion
                        if cleaned_value and cleaned_value != current_value:
                            setattr(metadata, field_name, cleaned_value)
                            fields_updated += 1
                
                # Clean other metadata text fields
                metadata_text_fields = [
                    "work_direct_phone", "home_phone", "city", "state",
                    "country", "other_phone", "stage"
                ]
                
                for field_name in metadata_text_fields:
                    current_value = getattr(metadata, field_name, None)
                    # #region agent log
                    try:
                        with open(DEBUG_LOG_PATH, 'a', encoding='utf-8') as f:
                            f.write(json.dumps({"sessionId":"debug-session","runId":"post-fix","hypothesisId":"B","location":"cleanup_service.py:clean_contact:metadata_field_before","message":"Before cleaning metadata field","data":{"field":field_name,"value":current_value,"type":str(type(current_value))},"timestamp":int(__import__('time').time()*1000)})+'\n')
                    except: pass
                    # #endregion
                    if current_value:
                        cleaned_value = clean_text(current_value)
                        # #region agent log
                        try:
                            with open(DEBUG_LOG_PATH, 'a', encoding='utf-8') as f:
                                f.write(json.dumps({"sessionId":"debug-session","runId":"post-fix","hypothesisId":"B","location":"cleanup_service.py:clean_contact:metadata_field_after","message":"After cleaning metadata field","data":{"field":field_name,"original":current_value,"cleaned":cleaned_value,"changed":cleaned_value!=current_value,"will_update":cleaned_value!=current_value},"timestamp":int(__import__('time').time()*1000)})+'\n')
                        except: pass
                        # #endregion
                        if cleaned_value != current_value:
                            setattr(metadata, field_name, cleaned_value)
                            fields_updated += 1
            
            await session.commit()
            
            # #region agent log
            try:
                with open(DEBUG_LOG_PATH, 'a', encoding='utf-8') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"ALL","location":"cleanup_service.py:clean_contact:exit","message":"clean_contact completed","data":{"fields_updated":fields_updated,"success":True},"timestamp":int(__import__('time').time()*1000)})+'\n')
            except: pass
            # #endregion
            
            return {
                "uuid": contact_uuid,
                "success": True,
                "fields_updated": fields_updated,
                "error": None,
            }
        except Exception as e:
            await session.rollback()
            logger.exception("Error cleaning contact: uuid=%s", contact_uuid)
            return {
                "uuid": contact_uuid,
                "success": False,
                "fields_updated": fields_updated,
                "error": str(e),
            }

    async def clean_company(
        self,
        session: AsyncSession,
        company_uuid: str,
    ) -> dict:
        """
        Clean a single company and its metadata.
        
        Args:
            session: Database session
            company_uuid: Company UUID
            
        Returns:
            Dictionary with cleanup results
        """
        fields_updated = 0
        
        try:
            # Get company
            result = await session.execute(
                select(Company).where(Company.uuid == company_uuid)
            )
            company = result.scalar_one_or_none()
            
            if not company:
                return {
                    "uuid": company_uuid,
                    "success": False,
                    "fields_updated": 0,
                    "error": "Company not found",
                }
            
            # Clean company name
            if company.name:
                cleaned_name = self.clean_company_name(company.name)
                if cleaned_name != company.name:
                    company.name = cleaned_name
                    fields_updated += 1
            
            # Clean keywords
            if company.keywords:
                cleaned_keywords = self.clean_keyword_array(company.keywords)
                if cleaned_keywords != company.keywords:
                    company.keywords = cleaned_keywords
                    fields_updated += 1
            
            # Clean other array fields
            array_fields = ["industries", "technologies"]
            for field_name in array_fields:
                current_value = getattr(company, field_name, None)
                if current_value:
                    cleaned_value = clean_array(current_value)
                    if cleaned_value != current_value:
                        setattr(company, field_name, cleaned_value)
                        fields_updated += 1
            
            # Clean other text fields
            text_fields = ["address", "text_search"]
            for field_name in text_fields:
                current_value = getattr(company, field_name, None)
                if current_value:
                    cleaned_value = clean_text(current_value)
                    if cleaned_value != current_value:
                        setattr(company, field_name, cleaned_value)
                        fields_updated += 1
            
            # Clean company metadata
            result = await session.execute(
                select(CompanyMetadata).where(CompanyMetadata.uuid == company_uuid)
            )
            metadata = result.scalar_one_or_none()
            
            if metadata:
                # Clean URL fields with specialized URL cleaner
                url_fields = ["linkedin_url", "linkedin_sales_url", "facebook_url", "twitter_url", "website"]
                for field_name in url_fields:
                    current_value = getattr(metadata, field_name, None)
                    if current_value:
                        cleaned_value = clean_url(current_value)
                        if cleaned_value and cleaned_value != current_value:
                            setattr(metadata, field_name, cleaned_value)
                            fields_updated += 1
                
                # Clean other metadata text fields
                metadata_text_fields = [
                    "company_name_for_emails", "phone_number", "latest_funding",
                    "last_raised_at", "city", "state", "country"
                ]
                
                for field_name in metadata_text_fields:
                    current_value = getattr(metadata, field_name, None)
                    if current_value:
                        cleaned_value = clean_text(current_value)
                        if cleaned_value != current_value:
                            setattr(metadata, field_name, cleaned_value)
                            fields_updated += 1
            
            await session.commit()
            
            return {
                "uuid": company_uuid,
                "success": True,
                "fields_updated": fields_updated,
                "error": None,
            }
        except Exception as e:
            await session.rollback()
            logger.exception("Error cleaning company: uuid=%s", company_uuid)
            return {
                "uuid": company_uuid,
                "success": False,
                "fields_updated": fields_updated,
                "error": str(e),
            }

    async def clean_contacts_batch(
        self,
        session: AsyncSession,
        contact_uuids: list[str],
    ) -> dict:
        """
        Clean a batch of contacts.
        
        Args:
            session: Database session
            contact_uuids: List of contact UUIDs
            
        Returns:
            Dictionary with batch cleanup results
        """
        results = []
        successful = 0
        failed = 0
        
        for uuid in contact_uuids:
            result = await self.clean_contact(session, uuid)
            results.append(result)
            if result["success"]:
                successful += 1
            else:
                failed += 1
        
        return {
            "total": len(contact_uuids),
            "successful": successful,
            "failed": failed,
            "results": results,
        }

    async def clean_companies_batch(
        self,
        session: AsyncSession,
        company_uuids: list[str],
    ) -> dict:
        """
        Clean a batch of companies.
        
        Args:
            session: Database session
            company_uuids: List of company UUIDs
            
        Returns:
            Dictionary with batch cleanup results
        """
        results = []
        successful = 0
        failed = 0
        
        for uuid in company_uuids:
            result = await self.clean_company(session, uuid)
            results.append(result)
            if result["success"]:
                successful += 1
            else:
                failed += 1
        
        return {
            "total": len(company_uuids),
            "successful": successful,
            "failed": failed,
            "results": results,
        }

