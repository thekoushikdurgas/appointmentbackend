"""Utility functions for batch fetching related entities using Connectra.

This module provides efficient batch lookup functions using Connectra API
instead of direct PostgreSQL queries.
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple

from app.clients.connectra_client import ConnectraClient
from app.utils.logger import get_logger

logger = get_logger(__name__)


# Maximum batch size for UUID lookups to avoid API rate limits
BATCH_SIZE = 100


async def batch_fetch_companies_by_uuids(
    session,  # Kept for compatibility, not used
    company_uuids: set[str],
) -> dict[str, dict]:
    """
    Batch fetch companies by their UUIDs using Connectra.
    
    Args:
        session: Database session (kept for compatibility, not used)
        company_uuids: Set of company UUIDs to fetch
        
    Returns:
        Dictionary mapping company UUID to company data dict
    """
    if not company_uuids:
        return {}
    
    try:
        async with ConnectraClient() as client:
            uuid_list = list(company_uuids)
            result_dict = await client.batch_get_companies_by_uuids(uuid_list, batch_size=BATCH_SIZE)
            return result_dict
    except Exception as exc:
        # Log error but return empty dict to avoid breaking callers
        logger.error(f"Failed to batch fetch companies from Connectra: {exc}")
        return {}


async def batch_fetch_contacts_by_uuids(
    session,  # Kept for compatibility, not used
    contact_uuids: set[str],
) -> dict[str, dict]:
    """
    Batch fetch contacts by their UUIDs using Connectra.
    
    Args:
        session: Database session (kept for compatibility, not used)
        contact_uuids: Set of contact UUIDs to fetch
        
    Returns:
        Dictionary mapping contact UUID to contact data dict
    """
    if not contact_uuids:
        return {}
    
    try:
        async with ConnectraClient() as client:
            uuid_list = list(contact_uuids)
            result_dict = await client.batch_get_contacts_by_uuids(uuid_list, batch_size=BATCH_SIZE)
            return result_dict
    except Exception as exc:
        # Log error but return empty dict to avoid breaking callers
        logger.error(f"Failed to batch fetch contacts from Connectra: {exc}")
        return {}


async def batch_fetch_contact_metadata_by_uuids(
    session,  # Kept for compatibility, not used
    contact_uuids: set[str],
) -> dict[str, dict]:
    """
    Batch fetch contact metadata by contact UUIDs using Connectra.
    
    Note: Contact metadata is included in the contact response from Connectra.
    This function extracts metadata from contact data.
    
    Args:
        session: Database session (kept for compatibility, not used)
        contact_uuids: Set of contact UUIDs to fetch metadata for
        
    Returns:
        Dictionary mapping contact UUID to metadata dict
    """
    if not contact_uuids:
        return {}
    
    try:
        async with ConnectraClient() as client:
            uuid_list = list(contact_uuids)
            contacts_dict = await client.batch_get_contacts_by_uuids(uuid_list, batch_size=BATCH_SIZE)
            
            # Extract metadata from contact data
            metadata_dict = {}
            for uuid, contact_data in contacts_dict.items():
                # Metadata fields are included in contact response
                metadata_dict[uuid] = contact_data  # Full contact data includes metadata
            
            return metadata_dict
    except Exception as exc:
        # Log error but return empty dict to avoid breaking callers
        logger.error(f"Failed to batch fetch contact metadata from Connectra: {exc}")
        return {}


async def batch_fetch_company_metadata_by_uuids(
    session,  # Kept for compatibility, not used
    company_uuids: set[str],
) -> dict[str, dict]:
    """
    Batch fetch company metadata by company UUIDs using Connectra.
    
    Note: Company metadata is included in the company response from Connectra.
    This function extracts metadata from company data.
    
    Args:
        session: Database session (kept for compatibility, not used)
        company_uuids: Set of company UUIDs to fetch metadata for
        
    Returns:
        Dictionary mapping company UUID to metadata dict
    """
    if not company_uuids:
        return {}
    
    try:
        async with ConnectraClient() as client:
            uuid_list = list(company_uuids)
            companies_dict = await client.batch_get_companies_by_uuids(uuid_list, batch_size=BATCH_SIZE)
            
            # Extract metadata from company data
            metadata_dict = {}
            for uuid, company_data in companies_dict.items():
                # Metadata fields are included in company response
                metadata_dict[uuid] = company_data  # Full company data includes metadata
            
            return metadata_dict
    except Exception as exc:
        # Log error but return empty dict to avoid breaking callers
        logger.error(f"Failed to batch fetch company metadata from Connectra: {exc}")
        return {}


async def fetch_company_by_uuid(
    session,  # Kept for compatibility, not used
    company_uuid: Optional[str],
) -> Optional[dict]:
    """
    Fetch a single company by UUID using Connectra.
    
    Args:
        session: Database session (kept for compatibility, not used)
        company_uuid: Company UUID to fetch
        
    Returns:
        Company data dict or None if not found
    """
    if not company_uuid:
        return None
    
    try:
        async with ConnectraClient() as client:
            company_data = await client.get_company_by_uuid(company_uuid)
            return company_data
    except Exception as exc:
        logger.error(f"Failed to fetch company from Connectra: {exc}")
        return None


async def fetch_contact_metadata_by_uuid(
    session,  # Kept for compatibility, not used
    contact_uuid: str,
) -> Optional[dict]:
    """
    Fetch contact metadata by contact UUID using Connectra.
    
    Args:
        session: Database session (kept for compatibility, not used)
        contact_uuid: Contact UUID to fetch metadata for
        
    Returns:
        Contact metadata dict or None if not found
    """
    try:
        async with ConnectraClient() as client:
            contact_data = await client.get_contact_by_uuid(contact_uuid)
            return contact_data  # Contact data includes metadata
    except Exception as exc:
        logger.error(f"Failed to fetch contact metadata from Connectra: {exc}")
        return None


async def fetch_company_metadata_by_uuid(
    session,  # Kept for compatibility, not used
    company_uuid: str,
) -> Optional[dict]:
    """
    Fetch company metadata by company UUID using Connectra.
    
    Args:
        session: Database session (kept for compatibility, not used)
        company_uuid: Company UUID to fetch metadata for
        
    Returns:
        Company metadata dict or None if not found
    """
    try:
        async with ConnectraClient() as client:
            company_data = await client.get_company_by_uuid(company_uuid)
            return company_data  # Company data includes metadata
    except Exception as exc:
        logger.error(f"Failed to fetch company metadata from Connectra: {exc}")
        return None


async def fetch_companies_and_metadata_by_uuids(
    session,  # Kept for compatibility, not used
    company_uuids: list[str],
) -> Dict[str, Tuple[dict, Optional[dict]]]:
    """
    Fetch companies and their metadata by UUIDs in batch using Connectra.

    Args:
        session: Database session (kept for compatibility, not used)
        company_uuids: List of company UUIDs to fetch

    Returns:
        Dict mapping company UUID to tuple of (company_data, metadata_data)
        Note: metadata_data is the same as company_data since Connectra includes it
    """
    if not company_uuids:
        return {}

    uuid_set = set(company_uuids)

    # Fetch companies (metadata is included in company data)
    companies = await batch_fetch_companies_by_uuids(session, uuid_set)

    combined: Dict[str, Tuple[dict, Optional[dict]]] = {}
    for uuid, company_data in companies.items():
        # Company data includes metadata, so we return it for both
        combined[uuid] = (company_data, company_data)

    return combined


async def fetch_contacts_and_metadata_by_uuids(
    session,  # Kept for compatibility, not used
    contact_uuids: list[str],
) -> Dict[str, Tuple[dict, Optional[dict]]]:
    """
    Fetch contacts and their metadata by UUIDs in batch using Connectra.

    Args:
        session: Database session (kept for compatibility, not used)
        contact_uuids: List of contact UUIDs to fetch

    Returns:
        Dict mapping contact UUID to tuple of (contact_data, metadata_data)
        Note: metadata_data is the same as contact_data since Connectra includes it
    """
    if not contact_uuids:
        return {}

    uuid_set = set(contact_uuids)

    # Fetch contacts (metadata is included in contact data)
    contacts = await batch_fetch_contacts_by_uuids(session, uuid_set)

    combined: Dict[str, Tuple[dict, Optional[dict]]] = {}
    for uuid, contact_data in contacts.items():
        # Contact data includes metadata, so we return it for both
        combined[uuid] = (contact_data, contact_data)

    return combined

