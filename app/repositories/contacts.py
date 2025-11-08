from __future__ import annotations

from typing import Any, Iterable, Optional, Sequence

from sqlalchemy import Select, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models.companies import Company, CompanyMetadata
from app.models.contacts import Contact, ContactMetadata
from app.repositories.base import AsyncRepository
from app.schemas.filters import AttributeListParams, ContactFilterParams
from app.utils.query import (
    apply_ilike_filter,
    apply_numeric_range_filter,
    apply_ordering,
    apply_search,
)


class ContactRepository(AsyncRepository[Contact]):
    def __init__(self) -> None:
        super().__init__(Contact)

    def base_query(self) -> tuple[Select, Company, ContactMetadata, CompanyMetadata]:
        company_alias = aliased(Company, name="company")
        contact_meta_alias = aliased(ContactMetadata, name="contact_metadata")
        company_meta_alias = aliased(CompanyMetadata, name="company_metadata")

        stmt: Select = (
            select(Contact, company_alias, contact_meta_alias, company_meta_alias)
            .select_from(Contact)
            .outerjoin(company_alias, Contact.company_id == company_alias.uuid)
            .outerjoin(contact_meta_alias, Contact.uuid == contact_meta_alias.uuid)
            .outerjoin(company_meta_alias, company_alias.uuid == company_meta_alias.uuid)
        )
        return stmt, company_alias, contact_meta_alias, company_meta_alias

    def apply_filters(
        self,
        stmt: Select,
        filters: ContactFilterParams,
        company: Company,
        company_meta: CompanyMetadata | None = None,
        contact_meta: ContactMetadata | None = None,
    ) -> Select:
        stmt = apply_ilike_filter(stmt, Contact.first_name, filters.first_name)
        stmt = apply_ilike_filter(stmt, Contact.last_name, filters.last_name)
        stmt = apply_ilike_filter(stmt, Contact.email, filters.email)
        stmt = apply_ilike_filter(stmt, Contact.title, filters.title)
        stmt = apply_ilike_filter(stmt, Contact.company_id, filters.company_id)
        stmt = apply_ilike_filter(stmt, company.name, filters.company)
        if filters.seniority:
            stmt = apply_ilike_filter(stmt, Contact.seniority, filters.seniority)

        if company_meta is not None:
            stmt = apply_ilike_filter(stmt, company_meta.country, filters.country)
            stmt = apply_ilike_filter(stmt, company_meta.state, filters.state)
            stmt = apply_ilike_filter(stmt, company_meta.city, filters.city)
            stmt = apply_ilike_filter(stmt, company_meta.company_name_for_emails, filters.company_name_for_emails)
            if filters.company_country:
                stmt = apply_ilike_filter(stmt, company_meta.country, filters.company_country)
            if filters.company_state:
                stmt = apply_ilike_filter(stmt, company_meta.state, filters.company_state)
            if filters.company_city:
                stmt = apply_ilike_filter(stmt, company_meta.city, filters.company_city)
            if filters.latest_funding_amount_min is not None:
                stmt = stmt.where(company_meta.latest_funding_amount >= filters.latest_funding_amount_min)
            if filters.latest_funding_amount_max is not None:
                stmt = stmt.where(company_meta.latest_funding_amount <= filters.latest_funding_amount_max)
        if contact_meta is not None:
            stmt = apply_ilike_filter(stmt, contact_meta.city, filters.city)
            stmt = apply_ilike_filter(stmt, contact_meta.state, filters.state)
            stmt = apply_ilike_filter(stmt, contact_meta.country, filters.country)
            if filters.stage:
                stmt = apply_ilike_filter(stmt, contact_meta.stage, filters.stage)

        stmt = apply_numeric_range_filter(
            stmt,
            company.employees_count,
            filters.employees_min,
            filters.employees_max,
        )
        stmt = apply_numeric_range_filter(
            stmt,
            company.annual_revenue,
            filters.annual_revenue_min,
            filters.annual_revenue_max,
        )
        stmt = apply_numeric_range_filter(
            stmt,
            company.total_funding,
            filters.total_funding_min,
            filters.total_funding_max,
        )

        if filters.technologies:
            stmt = stmt.where(func.array_to_string(company.technologies, ",").ilike(f"%{filters.technologies}%"))
        if filters.keywords:
            stmt = stmt.where(func.array_to_string(company.keywords, ",").ilike(f"%{filters.keywords}%"))
        if filters.industries:
            stmt = stmt.where(func.array_to_string(company.industries, ",").ilike(f"%{filters.industries}%"))

        if filters.department:
            stmt = stmt.where(
                func.array_to_string(Contact.departments, ",").ilike(f"%{filters.department}%")
            )

        if filters.created_at_after is not None:
            stmt = stmt.where(Contact.created_at >= filters.created_at_after)
        if filters.updated_at_before is not None:
            stmt = stmt.where(Contact.updated_at <= filters.updated_at_before)

        return stmt

    def apply_search_terms(
        self,
        stmt: Select,
        search: Optional[str],
        company: Company,
    ) -> Select:
        if not search:
            return stmt
        columns: Iterable = [
            Contact.first_name,
            Contact.last_name,
            Contact.email,
            Contact.title,
            Contact.seniority,
            Contact.text_search,
            company.name,
            company.address,
            company.city,
            company.state,
            company.country,
            func.array_to_string(company.industries, ","),
            func.array_to_string(company.keywords, ","),
        ]
        return apply_search(stmt, search, columns)

    async def list_contacts(
        self,
        session: AsyncSession,
        filters: ContactFilterParams,
        limit: int,
        offset: int,
    ) -> Sequence[tuple[Contact, Company, ContactMetadata, CompanyMetadata]]:
        stmt, company_alias, contact_meta_alias, company_meta_alias = self.base_query()
        stmt = self.apply_filters(stmt, filters, company_alias, company_meta_alias, contact_meta_alias)
        stmt = self.apply_search_terms(stmt, filters.search, company_alias)
        ordering_map = {
            "first_name": Contact.first_name,
            "last_name": Contact.last_name,
            "title": Contact.title,
            "email": Contact.email,
            "company": company_alias.name,
            "employees": company_alias.employees_count,
            "annual_revenue": company_alias.annual_revenue,
            "total_funding": company_alias.total_funding,
            "seniority": Contact.seniority,
            "created_at": Contact.created_at,
        }
        stmt = apply_ordering(stmt, filters.ordering, ordering_map)
        stmt = stmt.limit(limit).offset(offset)
        result = await session.execute(stmt)
        return result.fetchall()

    async def count_contacts(
        self,
        session: AsyncSession,
        filters: ContactFilterParams,
    ) -> int:
        company_alias = aliased(Company, name="company_for_count")
        stmt = select(func.count(Contact.id)).select_from(Contact).outerjoin(
            company_alias, Contact.company_id == company_alias.uuid
        )
        stmt = self.apply_filters(stmt, filters, company_alias)
        stmt = self.apply_search_terms(stmt, filters.search, company_alias)
        result = await session.execute(stmt)
        return result.scalar_one()

    async def list_attribute_values(
        self,
        session: AsyncSession,
        column,
        filters: ContactFilterParams,
        params: AttributeListParams,
    ) -> list[str]:
        stmt = select(distinct(column)).select_from(Contact)
        company_alias = aliased(Company, name="company_attribute")
        contact_meta_alias = aliased(ContactMetadata, name="contact_meta_attribute")
        company_meta_alias = aliased(CompanyMetadata, name="company_meta_attribute")

        stmt = stmt.outerjoin(company_alias, Contact.company_id == company_alias.uuid)
        stmt = stmt.outerjoin(contact_meta_alias, Contact.uuid == contact_meta_alias.uuid)
        stmt = stmt.outerjoin(company_meta_alias, company_alias.uuid == company_meta_alias.uuid)

        stmt = self.apply_filters(
            stmt,
            filters,
            company_alias,
            company_meta_alias,
            contact_meta_alias,
        )
        stmt = self.apply_search_terms(stmt, params.search or filters.search, company_alias)
        stmt = apply_ordering(
            stmt,
            params.ordering,
            {"value": column},
        )
        stmt = stmt.limit(params.limit).offset(params.offset)
        result = await session.execute(stmt)
        return [value for (value,) in result.fetchall() if value]

    async def get_contact_with_relations(
        self,
        session: AsyncSession,
        contact_id: int,
    ) -> Optional[tuple[Contact, Company, ContactMetadata, CompanyMetadata]]:
        stmt, _, _, _ = self.base_query()
        stmt = stmt.where(Contact.id == contact_id)
        result = await session.execute(stmt)
        return result.first()

