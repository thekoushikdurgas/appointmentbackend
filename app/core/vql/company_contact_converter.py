"""Converter for CompanyContactFilterParams to VQL filters."""

from typing import List, Optional

from app.core.vql.structures import VQLCondition, VQLFilter, VQLOperator
from app.schemas.filters import CompanyContactFilterParams
from app.utils.logger import get_logger

logger = get_logger(__name__)


class CompanyContactFilterConverter:
    """Converts CompanyContactFilterParams to VQL filter structures."""

    @staticmethod
    def to_vql_filter(
        filters: CompanyContactFilterParams,
        company_uuid: str,
    ) -> VQLFilter:
        """
        Convert CompanyContactFilterParams to VQL filter.

        Args:
            filters: CompanyContactFilterParams instance
            company_uuid: Company UUID to filter by (required)

        Returns:
            VQLFilter with all conditions
        """
        conditions: List[VQLCondition] = []

        # Always add company_id filter
        conditions.append(
            VQLCondition(
                field="company_id",
                operator=VQLOperator.EQ,
                value=company_uuid
            )
        )

        # Contact identity fields
        if filters.first_name:
            conditions.append(
                VQLCondition(
                    field="first_name",
                    operator=VQLOperator.CONTAINS,
                    value=filters.first_name
                )
            )

        if filters.last_name:
            conditions.append(
                VQLCondition(
                    field="last_name",
                    operator=VQLOperator.CONTAINS,
                    value=filters.last_name
                )
            )

        if filters.title:
            conditions.append(
                VQLCondition(
                    field="title",
                    operator=VQLOperator.CONTAINS,
                    value=filters.title
                )
            )

        if filters.seniority:
            conditions.append(
                VQLCondition(
                    field="seniority",
                    operator=VQLOperator.CONTAINS,
                    value=filters.seniority
                )
            )

        if filters.department:
            conditions.append(
                VQLCondition(
                    field="departments",
                    operator=VQLOperator.CONTAINS,
                    value=filters.department
                )
            )

        if filters.email_status:
            conditions.append(
                VQLCondition(
                    field="email_status",
                    operator=VQLOperator.CONTAINS,
                    value=filters.email_status
                )
            )

        if filters.status:
            conditions.append(
                VQLCondition(
                    field="status",
                    operator=VQLOperator.EQ,
                    value=filters.status
                )
            )

        if filters.email:
            conditions.append(
                VQLCondition(
                    field="email",
                    operator=VQLOperator.CONTAINS,
                    value=filters.email
                )
            )

        if filters.contact_location:
            conditions.append(
                VQLCondition(
                    field="text_search",
                    operator=VQLOperator.CONTAINS,
                    value=filters.contact_location
                )
            )

        # Contact metadata fields
        if filters.work_direct_phone:
            conditions.append(
                VQLCondition(
                    field="work_direct_phone",
                    operator=VQLOperator.CONTAINS,
                    value=filters.work_direct_phone
                )
            )

        if filters.home_phone:
            conditions.append(
                VQLCondition(
                    field="home_phone",
                    operator=VQLOperator.CONTAINS,
                    value=filters.home_phone
                )
            )

        if filters.mobile_phone:
            conditions.append(
                VQLCondition(
                    field="mobile_phone",
                    operator=VQLOperator.CONTAINS,
                    value=filters.mobile_phone
                )
            )

        if filters.other_phone:
            conditions.append(
                VQLCondition(
                    field="other_phone",
                    operator=VQLOperator.CONTAINS,
                    value=filters.other_phone
                )
            )

        if filters.city:
            conditions.append(
                VQLCondition(
                    field="city",
                    operator=VQLOperator.CONTAINS,
                    value=filters.city
                )
            )

        if filters.state:
            conditions.append(
                VQLCondition(
                    field="state",
                    operator=VQLOperator.CONTAINS,
                    value=filters.state
                )
            )

        if filters.country:
            conditions.append(
                VQLCondition(
                    field="country",
                    operator=VQLOperator.CONTAINS,
                    value=filters.country
                )
            )

        if filters.person_linkedin_url:
            conditions.append(
                VQLCondition(
                    field="linkedin_url",
                    operator=VQLOperator.CONTAINS,
                    value=filters.person_linkedin_url
                )
            )

        if filters.website:
            conditions.append(
                VQLCondition(
                    field="website",
                    operator=VQLOperator.CONTAINS,
                    value=filters.website
                )
            )

        if filters.facebook_url:
            conditions.append(
                VQLCondition(
                    field="facebook_url",
                    operator=VQLOperator.CONTAINS,
                    value=filters.facebook_url
                )
            )

        if filters.twitter_url:
            conditions.append(
                VQLCondition(
                    field="twitter_url",
                    operator=VQLOperator.CONTAINS,
                    value=filters.twitter_url
                )
            )

        if filters.stage:
            conditions.append(
                VQLCondition(
                    field="stage",
                    operator=VQLOperator.CONTAINS,
                    value=filters.stage
                )
            )

        # Exclusion filters (use NIN or NCONTAINS)
        if filters.exclude_titles:
            conditions.append(
                VQLCondition(
                    field="title",
                    operator=VQLOperator.NIN,
                    value=filters.exclude_titles
                )
            )

        if filters.exclude_contact_locations:
            # For text_search exclusion, we need to use OR logic with multiple conditions
            # This is complex, so we'll use a simple approach: exclude if any location matches
            # Note: VQL may need special handling for this
            for location in filters.exclude_contact_locations:
                conditions.append(
                    VQLCondition(
                        field="text_search",
                        operator=VQLOperator.NCONTAINS,
                        value=location
                    )
                )

        if filters.exclude_seniorities:
            conditions.append(
                VQLCondition(
                    field="seniority",
                    operator=VQLOperator.NIN,
                    value=filters.exclude_seniorities
                )
            )

        if filters.exclude_departments:
            # For array fields, we need to check that the array doesn't contain any excluded value
            for dept in filters.exclude_departments:
                conditions.append(
                    VQLCondition(
                        field="departments",
                        operator=VQLOperator.NCONTAINS,
                        value=dept
                    )
                )

        # Build filter with AND logic (all conditions must match)
        return VQLFilter(and_=conditions)

