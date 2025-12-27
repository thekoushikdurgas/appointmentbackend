"""VQL operator implementations for SQLAlchemy queries."""

from typing import Any, List

from sqlalchemy import Column, and_, or_
from sqlalchemy.sql.elements import BinaryExpression

from app.core.vql.field_mapper import FieldMapper
from app.core.vql.structures import VQLOperator
from app.utils.logger import get_logger

logger = get_logger(__name__)


class VQLOperatorHandler:
    """Handles VQL operator logic and converts to SQLAlchemy expressions."""

    @staticmethod
    def apply_operator(
        column: Column,
        operator: VQLOperator,
        value: Any,
        field_name: str,
        entity_type: str = "contact",
    ) -> BinaryExpression:
        """
        Apply a VQL operator to a column and value.

        Args:
            column: SQLAlchemy column
            operator: VQL operator
            value: Value to compare
            field_name: Field name for type detection
            entity_type: "contact" or "company"

        Returns:
            SQLAlchemy binary expression
        """
        field_type = FieldMapper.get_field_type(field_name, entity_type)

        if operator == VQLOperator.EQ:
            return column == value

        elif operator == VQLOperator.NE:
            return column != value

        elif operator == VQLOperator.GT:
            return column > value

        elif operator == VQLOperator.GTE:
            return column >= value

        elif operator == VQLOperator.LT:
            return column < value

        elif operator == VQLOperator.LTE:
            return column <= value

        elif operator == VQLOperator.IN:
            if not isinstance(value, list):
                value = [value]
            return column.in_(value)

        elif operator == VQLOperator.NIN:
            if not isinstance(value, list):
                value = [value]
            return ~column.in_(value)

        elif operator == VQLOperator.CONTAINS:
            if field_type == "array":
                # PostgreSQL array contains operator
                return column.any(value)
            else:
                # String contains (case-insensitive)
                return column.ilike(f"%{value}%")

        elif operator == VQLOperator.NCONTAINS:
            if field_type == "array":
                # PostgreSQL array doesn't contain
                return ~column.any(value)
            else:
                # String doesn't contain (case-insensitive)
                return ~column.ilike(f"%{value}%")

        elif operator == VQLOperator.EXISTS:
            return column.isnot(None)

        elif operator == VQLOperator.NEXISTS:
            return column.is_(None)

        else:
            raise ValueError(f"Unsupported operator: {operator}")

    @staticmethod
    def combine_conditions(
        conditions: List[BinaryExpression], use_and: bool = True
    ) -> BinaryExpression:
        """
        Combine multiple conditions with AND or OR.

        Args:
            conditions: List of SQLAlchemy binary expressions
            use_and: If True, use AND; if False, use OR

        Returns:
            Combined SQLAlchemy expression
        """
        if not conditions:
            raise ValueError("Cannot combine empty conditions list")

        if len(conditions) == 1:
            return conditions[0]

        if use_and:
            return and_(*conditions)
        else:
            return or_(*conditions)

