"""VQL query builder that converts VQL queries to SQLAlchemy queries."""

from typing import Any, List, Optional, Tuple

from sqlalchemy import Select, and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.vql.field_mapper import FieldMapper
from app.core.vql.operators import VQLOperatorHandler
from app.core.vql.structures import VQLCondition, VQLFilter, VQLQuery
from app.models.companies import Company, CompanyMetadata
from app.models.contacts import Contact, ContactMetadata
from app.utils.logger import get_logger

logger = get_logger(__name__)


class VQLQueryBuilder:
    """Builds SQLAlchemy queries from VQL queries."""

    def __init__(self, entity_type: str = "contact"):
        """
        Initialize query builder.

        Args:
            entity_type: "contact" or "company"
        """
        self.entity_type = entity_type
        self.operator_handler = VQLOperatorHandler()

    def build_query(
        self, vql_query: VQLQuery, base_query: Optional[Select] = None
    ) -> Tuple[Select, dict]:
        """
        Build a SQLAlchemy query from a VQL query.

        Args:
            vql_query: VQL query object
            base_query: Optional base query to extend

        Returns:
            Tuple of (SQLAlchemy Select query, metadata dict with join info)
        """
        # Start with base query or create new one
        if base_query is None:
            if self.entity_type == "contact":
                query = select(Contact)
            else:
                query = select(Company)
        else:
            query = base_query

        metadata = {
            "needs_company": False,
            "needs_contact_meta": False,
            "needs_company_meta": False,
        }

        # Create aliases for joins
        company_alias = aliased(Company)
        contact_meta_alias = aliased(ContactMetadata)
        company_meta_alias = aliased(CompanyMetadata)

        # Build filters first to determine which joins are needed
        filter_expr = None
        if vql_query.filters:
            filter_expr, filter_metadata = self._build_filter(
                vql_query.filters, company_alias, contact_meta_alias, company_meta_alias
            )
            metadata.update(filter_metadata)

        # Apply joins if needed (must be done before where clause)
        if metadata["needs_company"] and self.entity_type == "contact":
            query = query.outerjoin(company_alias, Contact.company_id == company_alias.uuid)
        if metadata["needs_company_meta"]:
            if self.entity_type == "contact":
                # Need company first for company_meta
                if not metadata["needs_company"]:
                    query = query.outerjoin(company_alias, Contact.company_id == company_alias.uuid)
                query = query.outerjoin(
                    company_meta_alias, company_alias.uuid == company_meta_alias.uuid
                )
            else:
                query = query.outerjoin(
                    company_meta_alias, Company.uuid == company_meta_alias.uuid
                )
        if metadata["needs_contact_meta"] and self.entity_type == "contact":
            query = query.outerjoin(
                contact_meta_alias, Contact.uuid == contact_meta_alias.uuid
            )

        # Apply filter expression after joins are set up
        if vql_query.filters and filter_expr is not None:
            query = query.where(filter_expr)

        # Apply sorting
        if vql_query.sort_by:
            sort_column = self._get_sort_column(
                vql_query.sort_by, company_alias, contact_meta_alias, company_meta_alias
            )
            if sort_column is not None:
                if vql_query.sort_direction == "desc":
                    query = query.order_by(sort_column.desc())
                else:
                    query = query.order_by(sort_column.asc())

        # Apply pagination
        if vql_query.limit:
            query = query.limit(vql_query.limit)
        if vql_query.offset:
            query = query.offset(vql_query.offset)

        return query, metadata

    def _build_filter(
        self,
        vql_filter: VQLFilter,
        company_alias: Company,
        contact_meta_alias: ContactMetadata,
        company_meta_alias: CompanyMetadata,
    ) -> Tuple[Optional[Any], dict]:
        """
        Build filter expression from VQL filter.

        Returns:
            Tuple of (SQLAlchemy expression, metadata dict)
        """
        metadata = {
            "needs_company": False,
            "needs_contact_meta": False,
            "needs_company_meta": False,
        }

        conditions: List[Any] = []

        # Process AND conditions
        if vql_filter.and_:
            and_conditions = []
            for item in vql_filter.and_:
                if isinstance(item, VQLCondition):
                    expr, item_metadata = self._build_condition(
                        item, company_alias, contact_meta_alias, company_meta_alias
                    )
                    if expr is not None:
                        and_conditions.append(expr)
                    metadata.update(item_metadata)
                elif isinstance(item, VQLFilter):
                    # Nested filter
                    nested_expr, nested_metadata = self._build_filter(
                        item, company_alias, contact_meta_alias, company_meta_alias
                    )
                    if nested_expr is not None:
                        and_conditions.append(nested_expr)
                    metadata.update(nested_metadata)

            if and_conditions:
                conditions.append(and_(*and_conditions))

        # Process OR conditions
        if vql_filter.or_:
            or_conditions = []
            for item in vql_filter.or_:
                if isinstance(item, VQLCondition):
                    expr, item_metadata = self._build_condition(
                        item, company_alias, contact_meta_alias, company_meta_alias
                    )
                    if expr is not None:
                        or_conditions.append(expr)
                    metadata.update(item_metadata)
                elif isinstance(item, VQLFilter):
                    # Nested filter
                    nested_expr, nested_metadata = self._build_filter(
                        item, company_alias, contact_meta_alias, company_meta_alias
                    )
                    if nested_expr is not None:
                        or_conditions.append(nested_expr)
                    metadata.update(nested_metadata)

            if or_conditions:
                conditions.append(or_(*or_conditions))

        if not conditions:
            return None, metadata

        if len(conditions) == 1:
            return conditions[0], metadata
        else:
            return and_(*conditions), metadata

    def _build_condition(
        self,
        condition: VQLCondition,
        company_alias: Company,
        contact_meta_alias: ContactMetadata,
        company_meta_alias: CompanyMetadata,
    ) -> Tuple[Optional[Any], dict]:
        """
        Build a single condition expression.

        Returns:
            Tuple of (SQLAlchemy expression, metadata dict)
        """
        metadata = {
            "needs_company": False,
            "needs_contact_meta": False,
            "needs_company_meta": False,
        }

        # Map field to column
        column, table_name, needs_join = self._resolve_field(
            condition.field, company_alias, contact_meta_alias, company_meta_alias
        )

        if column is None:
            # Field not found - skip this condition
            return None, metadata

        # Update metadata based on joins needed
        if needs_join == "company":
            metadata["needs_company"] = True
        elif needs_join == "company_meta":
            metadata["needs_company_meta"] = True
            metadata["needs_company"] = True  # CompanyMetadata requires Company
        elif needs_join == "contact_meta":
            metadata["needs_contact_meta"] = True

        # Apply operator
        try:
            expr = self.operator_handler.apply_operator(
                column, condition.operator, condition.value, condition.field, self.entity_type
            )
            return expr, metadata
        except Exception as e:
            # Invalid operator/value combination - skip condition
            return None, metadata

    def _resolve_field(
        self,
        field_name: str,
        company_alias: Company,
        contact_meta_alias: ContactMetadata,
        company_meta_alias: CompanyMetadata,
    ) -> Tuple[Optional[Any], Optional[str], Optional[str]]:
        """
        Resolve a field name to a SQLAlchemy column.

        Returns:
            Tuple of (Column, table_name, join_type)
        """
        if self.entity_type == "contact":
            column, table_name = FieldMapper.map_contact_field(field_name)
            if column is not None:
                if table_name == "contacts":
                    return column, table_name, None
                elif table_name == "contacts_metadata":
                    attr_name = FieldMapper.CONTACT_METADATA_FIELDS.get(field_name, field_name)
                    if hasattr(contact_meta_alias, attr_name):
                        return getattr(contact_meta_alias, attr_name), table_name, "contact_meta"

            # Try company fields (for cross-entity queries)
            column, table_name = FieldMapper.map_company_field(field_name)
            if column is not None:
                if table_name == "companies":
                    attr_name = FieldMapper.COMPANY_FIELDS.get(field_name, field_name)
                    if hasattr(company_alias, attr_name):
                        return getattr(company_alias, attr_name), table_name, "company"
                elif table_name == "companies_metadata":
                    attr_name = FieldMapper.COMPANY_METADATA_FIELDS.get(field_name, field_name)
                    if hasattr(company_meta_alias, attr_name):
                        return getattr(company_meta_alias, attr_name), table_name, "company_meta"
        else:
            # Company entity
            column, table_name = FieldMapper.map_company_field(field_name)
            if column is not None:
                if table_name == "companies":
                    return column, table_name, None
                elif table_name == "companies_metadata":
                    attr_name = FieldMapper.COMPANY_METADATA_FIELDS.get(field_name, field_name)
                    if hasattr(company_meta_alias, attr_name):
                        return getattr(company_meta_alias, attr_name), table_name, "company_meta"

        return None, None, None

    def _get_sort_column(
        self,
        sort_field: str,
        company_alias: Company,
        contact_meta_alias: ContactMetadata,
        company_meta_alias: CompanyMetadata,
    ) -> Optional[Any]:
        """Get column for sorting."""
        column, _, _ = self._resolve_field(
            sort_field, company_alias, contact_meta_alias, company_meta_alias
        )
        return column

