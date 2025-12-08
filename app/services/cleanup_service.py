"""Service for cleaning/normalizing contact and company data."""

import re
from typing import Optional

from sqlalchemy import select, update, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.batch_lookup import batch_fetch_contact_metadata_by_uuids

from app.models.companies import Company, CompanyMetadata
from app.models.contacts import Contact, ContactMetadata
from app.utils.company_name_utils import clean_company_name
from app.utils.keyword_utils import clean_keyword_array
from app.utils.title_utils import clean_title


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
        # Use cleaning utilities from app.utils
        self.clean_company_name = clean_company_name
        self.clean_keyword_array = clean_keyword_array
        self.clean_title = clean_title

    async def clean_contact(
        self,
        session: AsyncSession,
        contact_uuid: str,
    ) -> dict:
        """
        Clean a single contact and its metadata.
        
        Optimized to use bulk UPDATE statements instead of ORM changes
        to reduce commit time from ~1000ms to <50ms.
        
        Args:
            session: Database session
            contact_uuid: Contact UUID
            
        Returns:
            Dictionary with cleanup results
        """
        fields_updated = 0
        
        try:
            # Get contact using minimal query (no joins)
            result = await session.execute(
                select(Contact).where(Contact.uuid == contact_uuid)
            )
            contact = result.scalar_one_or_none()
            
            if not contact:
                return {
                    "uuid": contact_uuid,
                    "success": False,
                    "fields_updated": 0,
                    "error": "Contact not found",
                }
            
            # Batch fetch metadata separately
            contact_metadata = await batch_fetch_contact_metadata_by_uuids(session, {contact_uuid})
            metadata = contact_metadata.get(contact_uuid)
            
            # Collect all updates in dictionaries for bulk UPDATE
            contact_updates = {}
            metadata_updates = {}
            
            # Clean contact fields
            if contact.title:
                cleaned_title = self.clean_title(contact.title)
                if cleaned_title != contact.title:
                    contact_updates["title"] = cleaned_title
                    fields_updated += 1
            
            if contact.departments:
                cleaned_departments = self.clean_keyword_array(contact.departments)
                if cleaned_departments != contact.departments:
                    contact_updates["departments"] = cleaned_departments
                    fields_updated += 1
            
            # Clean email field
            if contact.email:
                cleaned_email = clean_email(contact.email)
                if cleaned_email and cleaned_email != contact.email:
                    contact_updates["email"] = cleaned_email
                    fields_updated += 1
            
            # Clean other text fields
            text_fields = ["first_name", "last_name", "mobile_phone", "email_status", "seniority"]
            for field_name in text_fields:
                current_value = getattr(contact, field_name, None)
                if current_value:
                    cleaned_value = clean_text(current_value)
                    if cleaned_value != current_value:
                        contact_updates[field_name] = cleaned_value
                        fields_updated += 1
            
            # Set status to "1" after successful cleanup
            if contact.status != "1":
                contact_updates["status"] = "1"
                fields_updated += 1
            
            if metadata:
                # Clean URL fields
                url_fields = ["linkedin_url", "facebook_url", "twitter_url", "website"]
                for field_name in url_fields:
                    current_value = getattr(metadata, field_name, None)
                    if current_value:
                        cleaned_value = clean_url(current_value)
                        if cleaned_value and cleaned_value != current_value:
                            metadata_updates[field_name] = cleaned_value
                            fields_updated += 1
                
                # Clean other metadata text fields
                metadata_text_fields = [
                    "work_direct_phone", "home_phone", "city", "state",
                    "country", "other_phone", "stage"
                ]
                for field_name in metadata_text_fields:
                    current_value = getattr(metadata, field_name, None)
                    if current_value:
                        cleaned_value = clean_text(current_value)
                        if cleaned_value != current_value:
                            metadata_updates[field_name] = cleaned_value
                            fields_updated += 1
            
            # Execute bulk UPDATE statements only if there are changes
            # Use synchronize_session=False to avoid ORM overhead
            # Flush after updates to reduce commit time
            if contact_updates:
                await session.execute(
                    update(Contact)
                    .where(Contact.uuid == contact_uuid)
                    .values(**contact_updates)
                    .execution_options(synchronize_session=False)
                )
                # Flush to reduce commit overhead
                await session.flush()
            
            if metadata_updates:
                await session.execute(
                    update(ContactMetadata)
                    .where(ContactMetadata.uuid == contact_uuid)
                    .values(**metadata_updates)
                    .execution_options(synchronize_session=False)
                )
                # Flush to reduce commit overhead
                await session.flush()
            
            # Note: We don't commit here - let get_db() dependency handle the commit
            # This avoids double commits and allows the transaction to be managed at the endpoint level
            
            return {
                "uuid": contact_uuid,
                "success": True,
                "fields_updated": fields_updated,
                "error": None,
            }
        except Exception as e:
            await session.rollback()
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
        Clean a batch of contacts using optimized bulk operations.
        
        Optimized to:
        - Bulk fetch all contacts and metadata in a single query
        - Process all contacts in memory
        - Use bulk UPDATE statements with CASE WHEN for efficiency
        - Single commit at the end
        
        Args:
            session: Database session
            contact_uuids: List of contact UUIDs
            
        Returns:
            Dictionary with batch cleanup results
        """
        if not contact_uuids:
            return {
                "total": 0,
                "successful": 0,
                "failed": 0,
                "results": [],
            }
        
        results = []
        successful = 0
        failed = 0
        
        try:
            # Bulk fetch all contacts with metadata in a single query
            # Split into batches to avoid query size limits (some DBs have IN clause limits)
            BATCH_SIZE = 1000
            all_contacts = {}
            all_metadata = {}
            
            for i in range(0, len(contact_uuids), BATCH_SIZE):
                batch_uuids = contact_uuids[i:i + BATCH_SIZE]
                # Fetch contacts using minimal query (no joins)
                result = await session.execute(
                    select(Contact).where(Contact.uuid.in_(batch_uuids))
                )
                contacts = result.scalars().all()
                
                for contact in contacts:
                    all_contacts[contact.uuid] = contact
            
            # Batch fetch all metadata separately
            all_contact_uuids_set = set(contact_uuids)
            all_metadata = await batch_fetch_contact_metadata_by_uuids(session, all_contact_uuids_set)
            
            # Process all contacts in memory
            contact_updates_by_field = {}  # field_name -> {uuid: value}
            metadata_updates_by_field = {}  # field_name -> {uuid: value}
            contact_status_updates = {}  # uuid -> "1"
            fields_updated_by_uuid = {}  # uuid -> count
            
            for uuid in contact_uuids:
                contact = all_contacts.get(uuid)
                if not contact:
                    results.append({
                        "uuid": uuid,
                        "success": False,
                        "fields_updated": 0,
                        "error": "Contact not found",
                    })
                    failed += 1
                    continue
                
                metadata = all_metadata.get(uuid)
                fields_updated = 0
                
                # Clean contact fields
                if contact.title:
                    cleaned_title = self.clean_title(contact.title)
                    if cleaned_title != contact.title:
                        if "title" not in contact_updates_by_field:
                            contact_updates_by_field["title"] = {}
                        contact_updates_by_field["title"][uuid] = cleaned_title
                        fields_updated += 1
                
                if contact.departments:
                    cleaned_departments = self.clean_keyword_array(contact.departments)
                    if cleaned_departments != contact.departments:
                        if "departments" not in contact_updates_by_field:
                            contact_updates_by_field["departments"] = {}
                        contact_updates_by_field["departments"][uuid] = cleaned_departments
                        fields_updated += 1
                
                # Clean email field
                if contact.email:
                    cleaned_email = clean_email(contact.email)
                    if cleaned_email and cleaned_email != contact.email:
                        if "email" not in contact_updates_by_field:
                            contact_updates_by_field["email"] = {}
                        contact_updates_by_field["email"][uuid] = cleaned_email
                        fields_updated += 1
                
                # Clean other text fields
                text_fields = ["first_name", "last_name", "mobile_phone", "email_status", "seniority"]
                for field_name in text_fields:
                    current_value = getattr(contact, field_name, None)
                    if current_value:
                        cleaned_value = clean_text(current_value)
                        if cleaned_value != current_value:
                            if field_name not in contact_updates_by_field:
                                contact_updates_by_field[field_name] = {}
                            contact_updates_by_field[field_name][uuid] = cleaned_value
                            fields_updated += 1
                
                # Set status to "1" after successful cleanup
                if contact.status != "1":
                    contact_status_updates[uuid] = "1"
                    fields_updated += 1
                
                if metadata:
                    # Clean URL fields
                    url_fields = ["linkedin_url", "facebook_url", "twitter_url", "website"]
                    for field_name in url_fields:
                        current_value = getattr(metadata, field_name, None)
                        if current_value:
                            cleaned_value = clean_url(current_value)
                            if cleaned_value and cleaned_value != current_value:
                                if field_name not in metadata_updates_by_field:
                                    metadata_updates_by_field[field_name] = {}
                                metadata_updates_by_field[field_name][uuid] = cleaned_value
                                fields_updated += 1
                    
                    # Clean other metadata text fields
                    metadata_text_fields = [
                        "work_direct_phone", "home_phone", "city", "state",
                        "country", "other_phone", "stage"
                    ]
                    for field_name in metadata_text_fields:
                        current_value = getattr(metadata, field_name, None)
                        if current_value:
                            cleaned_value = clean_text(current_value)
                            if cleaned_value != current_value:
                                if field_name not in metadata_updates_by_field:
                                    metadata_updates_by_field[field_name] = {}
                                metadata_updates_by_field[field_name][uuid] = cleaned_value
                                fields_updated += 1
                
                fields_updated_by_uuid[uuid] = fields_updated
                results.append({
                    "uuid": uuid,
                    "success": True,
                    "fields_updated": fields_updated,
                    "error": None,
                })
                successful += 1
            
            # Execute bulk UPDATE statements - OPTIMIZED: Combine all fields into single UPDATE per table
            # This reduces database round trips from N (one per field) to 2 (one per table)
            
            # Build combined VALUES clause for all contact fields
            if contact_updates_by_field or contact_status_updates:
                # Collect all UUIDs that need updates
                all_contact_uuids = set()
                for uuid_values in contact_updates_by_field.values():
                    all_contact_uuids.update(uuid_values.keys())
                all_contact_uuids.update(contact_status_updates.keys())
                
                if all_contact_uuids:
                    # Build VALUES clause with all fields for each UUID
                    values_parts = []
                    for uuid in all_contact_uuids:
                        field_values = []
                        # Add each field value (or NULL if not updated for this UUID)
                        for field_name in sorted(contact_updates_by_field.keys()):
                            uuid_values = contact_updates_by_field[field_name]
                            if uuid in uuid_values:
                                value = uuid_values[uuid]
                                is_array_field = field_name == "departments"
                                if value is None:
                                    field_values.append("NULL::text" if not is_array_field else "NULL::text[]")
                                elif isinstance(value, list):
                                    array_vals = [f"'{str(v).replace(chr(39), chr(39)+chr(39))}'" for v in value]
                                    field_values.append(f"ARRAY[{', '.join(array_vals)}]::text[]")
                                elif isinstance(value, str):
                                    escaped = value.replace("'", "''")
                                    field_values.append(f"'{escaped}'::text")
                                else:
                                    field_values.append(f"'{str(value)}'::text")
                            else:
                                field_values.append("NULL")  # Field not updated for this UUID
                        
                        # Add status
                        if uuid in contact_status_updates:
                            field_values.append("'1'::text")
                        else:
                            field_values.append("NULL")
                        
                        # Build row: uuid, field1, field2, ..., status
                        field_names = sorted(contact_updates_by_field.keys())
                        values_parts.append(f"('{uuid}'::text, {', '.join(field_values)})")
                    
                    values_clause = ", ".join(values_parts)
                    field_names = sorted(contact_updates_by_field.keys())
                    
                    # Build SET clauses - only update fields that have non-NULL values
                    set_clauses = []
                    for idx, field_name in enumerate(field_names):
                        is_array_field = field_name == "departments"
                        set_clauses.append(
                            f"{field_name} = COALESCE(v.field{idx}::{('text[]' if is_array_field else 'text')}, contacts.{field_name})"
                        )
                    # Add status
                    set_clauses.append("status = COALESCE(v.status::text, contacts.status)")
                    
                    # Execute single combined UPDATE for all contact fields
                    update_sql = text(f"""
                        UPDATE contacts
                        SET {', '.join(set_clauses)}
                        FROM (VALUES {values_clause}) AS v(uuid, {', '.join([f'field{i}' for i in range(len(field_names))])}, status)
                        WHERE contacts.uuid = v.uuid
                    """)
                    await session.execute(update_sql)
            
            # Build combined VALUES clause for all metadata fields
            if metadata_updates_by_field:
                # Collect all UUIDs that need metadata updates
                all_metadata_uuids = set()
                for uuid_values in metadata_updates_by_field.values():
                    all_metadata_uuids.update(uuid_values.keys())
                
                if all_metadata_uuids:
                    # Build VALUES clause with all fields for each UUID
                    values_parts = []
                    field_names = sorted(metadata_updates_by_field.keys())
                    
                    for uuid in all_metadata_uuids:
                        field_values = []
                        # Add each field value (or NULL if not updated for this UUID)
                        for field_name in field_names:
                            uuid_values = metadata_updates_by_field[field_name]
                            if uuid in uuid_values:
                                value = uuid_values[uuid]
                                if value is None:
                                    field_values.append("NULL::text")
                                elif isinstance(value, str):
                                    escaped = value.replace("'", "''")
                                    field_values.append(f"'{escaped}'::text")
                                else:
                                    field_values.append(f"'{str(value)}'::text")
                            else:
                                field_values.append("NULL")  # Field not updated for this UUID
                        
                        # Build row: uuid, field1, field2, ...
                        values_parts.append(f"('{uuid}'::text, {', '.join(field_values)})")
                    
                    values_clause = ", ".join(values_parts)
                    
                    # Build SET clauses - only update fields that have non-NULL values
                    set_clauses = []
                    for idx, field_name in enumerate(field_names):
                        set_clauses.append(
                            f"{field_name} = COALESCE(v.field{idx}::text, contacts_metadata.{field_name})"
                        )
                    
                    # Execute single combined UPDATE for all metadata fields
                    update_sql = text(f"""
                        UPDATE contacts_metadata
                        SET {', '.join(set_clauses)}
                        FROM (VALUES {values_clause}) AS v(uuid, {', '.join([f'field{i}' for i in range(len(field_names))])})
                        WHERE contacts_metadata.uuid = v.uuid
                    """)
                    await session.execute(update_sql)
            
            # Single flush at the end (no commit - let endpoint handle it)
            await session.flush()
            
        except Exception as e:
            # Mark all remaining as failed
            for uuid in contact_uuids:
                if not any(r["uuid"] == uuid for r in results):
                    results.append({
                        "uuid": uuid,
                        "success": False,
                        "fields_updated": 0,
                        "error": str(e),
                    })
                failed += 1
            await session.rollback()
        
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

