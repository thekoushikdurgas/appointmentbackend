"""Utility functions for batch fetching related entities by foreign keys.

This module provides efficient batch lookup functions to replace JOIN operations
by fetching related entities in separate queries using foreign key lookups.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.companies import Company, CompanyMetadata
from app.models.contacts import Contact, ContactMetadata


# Maximum batch size for UUID lookups to avoid query size limits
BATCH_SIZE = 1000


async def batch_fetch_companies_by_uuids(
    session: AsyncSession,
    company_uuids: set[str],
) -> dict[str, Company]:
    """
    Batch fetch companies by their UUIDs.
    
    Args:
        session: Database session
        company_uuids: Set of company UUIDs to fetch
        
    Returns:
        Dictionary mapping company UUID to Company object
    """
    if not company_uuids:
        return {}
    
    # Split into batches to avoid query size limits
    uuid_list = list(company_uuids)
    result_dict: dict[str, Company] = {}
    
    for i in range(0, len(uuid_list), BATCH_SIZE):
        batch = uuid_list[i:i + BATCH_SIZE]
        stmt = select(Company).where(Company.uuid.in_(batch))
        result = await session.execute(stmt)
        companies = result.scalars().all()
        
        for company in companies:
            result_dict[company.uuid] = company
    
    return result_dict


async def batch_fetch_contact_metadata_by_uuids(
    session: AsyncSession,
    contact_uuids: set[str],
) -> dict[str, ContactMetadata]:
    """
    Batch fetch contact metadata by contact UUIDs.
    
    Args:
        session: Database session
        contact_uuids: Set of contact UUIDs to fetch metadata for
        
    Returns:
        Dictionary mapping contact UUID to ContactMetadata object
    """
    if not contact_uuids:
        return {}
    
    # Split into batches to avoid query size limits
    uuid_list = list(contact_uuids)
    result_dict: dict[str, ContactMetadata] = {}
    
    for i in range(0, len(uuid_list), BATCH_SIZE):
        batch = uuid_list[i:i + BATCH_SIZE]
        stmt = select(ContactMetadata).where(ContactMetadata.uuid.in_(batch))
        result = await session.execute(stmt)
        metadata_list = result.scalars().all()
        
        for metadata in metadata_list:
            result_dict[metadata.uuid] = metadata
    
    return result_dict


async def batch_fetch_company_metadata_by_uuids(
    session: AsyncSession,
    company_uuids: set[str],
) -> dict[str, CompanyMetadata]:
    """
    Batch fetch company metadata by company UUIDs.
    
    Args:
        session: Database session
        company_uuids: Set of company UUIDs to fetch metadata for
        
    Returns:
        Dictionary mapping company UUID to CompanyMetadata object
    """
    if not company_uuids:
        return {}
    
    # Split into batches to avoid query size limits
    uuid_list = list(company_uuids)
    result_dict: dict[str, CompanyMetadata] = {}
    
    for i in range(0, len(uuid_list), BATCH_SIZE):
        batch = uuid_list[i:i + BATCH_SIZE]
        stmt = select(CompanyMetadata).where(CompanyMetadata.uuid.in_(batch))
        result = await session.execute(stmt)
        metadata_list = result.scalars().all()
        
        for metadata in metadata_list:
            result_dict[metadata.uuid] = metadata
    
    return result_dict


async def fetch_company_by_uuid(
    session: AsyncSession,
    company_uuid: Optional[str],
) -> Optional[Company]:
    """
    Fetch a single company by UUID.
    
    Args:
        session: Database session
        company_uuid: Company UUID to fetch
        
    Returns:
        Company object or None if not found
    """
    if not company_uuid:
        return None
    
    stmt = select(Company).where(Company.uuid == company_uuid)
    result = await session.execute(stmt)
    company = result.scalar_one_or_none()
    return company


async def fetch_contact_metadata_by_uuid(
    session: AsyncSession,
    contact_uuid: str,
) -> Optional[ContactMetadata]:
    """
    Fetch contact metadata by contact UUID.
    
    Args:
        session: Database session
        contact_uuid: Contact UUID to fetch metadata for
        
    Returns:
        ContactMetadata object or None if not found
    """
    stmt = select(ContactMetadata).where(ContactMetadata.uuid == contact_uuid)
    result = await session.execute(stmt)
    metadata = result.scalar_one_or_none()
    return metadata


async def fetch_company_metadata_by_uuid(
    session: AsyncSession,
    company_uuid: str,
) -> Optional[CompanyMetadata]:
    """
    Fetch company metadata by company UUID.
    
    Args:
        session: Database session
        company_uuid: Company UUID to fetch metadata for
        
    Returns:
        CompanyMetadata object or None if not found
    """
    stmt = select(CompanyMetadata).where(CompanyMetadata.uuid == company_uuid)
    result = await session.execute(stmt)
    metadata = result.scalar_one_or_none()
    return metadata

