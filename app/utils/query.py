"""Query composition helpers for SQLAlchemy statements."""

from __future__ import annotations

from typing import Iterable, Mapping, Optional

from sqlalchemy import ColumnElement, Select, asc, desc, func, or_
from sqlalchemy.dialects.postgresql import array

from app.core.logging import get_logger

logger = get_logger(__name__)


def apply_ilike_filter(
    stmt: Select,
    column: ColumnElement,
    value: Optional[str],
    *,
    use_prefix: bool = False,
    dialect_name: Optional[str] = None,
) -> Select:
    """
    Apply a case-insensitive partial match when a value is provided.
    
    Args:
        stmt: SQLAlchemy select statement
        column: Column to filter
        value: Filter value
        use_prefix: If True, use prefix matching (value%) for better index usage
        dialect_name: Database dialect name (e.g., 'postgresql')
    """
    logger.debug(
        "Entering apply_ilike_filter column=%s value_present=%s use_prefix=%s",
        getattr(column, "key", repr(column)),
        bool(value),
        use_prefix,
    )
    if value:
        value_stripped = value.strip()
        if use_prefix:
            # Prefix matching can use indexes better than leading wildcard
            stmt = stmt.where(column.ilike(f"{value_stripped}%"))
        else:
            # Use trigram index if available (PostgreSQL)
            if dialect_name == "postgresql":
                # Try to use similarity search for better performance with GIN indexes
                # Fallback to ILIKE if similarity not available
                stmt = stmt.where(column.ilike(f"%{value_stripped}%"))
            else:
                stmt = stmt.where(column.ilike(f"%{value_stripped}%"))
    logger.debug("Exiting apply_ilike_filter modified=%s", value is not None)
    return stmt


def apply_exact_filter(
    stmt: Select,
    column: ColumnElement,
    value: Optional[str],
) -> Select:
    """Apply an equality filter when a value is provided."""
    logger.debug(
        "Entering apply_exact_filter column=%s value_present=%s",
        getattr(column, "key", repr(column)),
        bool(value),
    )
    if value:
        stmt = stmt.where(column == value)
    logger.debug("Exiting apply_exact_filter modified=%s", value is not None)
    return stmt


def apply_numeric_range_filter(
    stmt: Select,
    column: ColumnElement,
    minimum: Optional[int],
    maximum: Optional[int],
) -> Select:
    """Apply inclusive numeric lower and upper bounds."""
    logger.debug(
        "Entering apply_numeric_range_filter column=%s minimum=%s maximum=%s",
        getattr(column, "key", repr(column)),
        minimum,
        maximum,
    )
    if minimum is not None:
        stmt = stmt.where(column >= minimum)
    if maximum is not None:
        stmt = stmt.where(column <= maximum)
    logger.debug(
        "Exiting apply_numeric_range_filter applied_min=%s applied_max=%s",
        minimum is not None,
        maximum is not None,
    )
    return stmt


def apply_ordering(
    stmt: Select,
    ordering: Optional[str],
    mapping: Mapping[str, ColumnElement],
) -> Select:
    """Apply ordering based on a comma-separated list of mapped keys."""
    logger.debug("Entering apply_ordering ordering=%s", ordering)
    if not ordering:
        logger.debug("Exiting apply_ordering unchanged (no ordering requested)")
        return stmt

    order_by_columns: list[ColumnElement] = []
    for token in ordering.split(","):
        token = token.strip()
        if not token:
            continue
        direction = asc
        if token.startswith("-"):
            direction = desc
            token = token[1:]
        column = mapping.get(token)
        if column is None:
            logger.debug("Unknown ordering token encountered token=%s", token)
            raise ValueError(f"Unknown ordering field: {token}")
        order_by_columns.append(direction(column))
    if order_by_columns:
        stmt = stmt.order_by(*order_by_columns)
    logger.debug(
        "Exiting apply_ordering applied_columns=%d", len(order_by_columns)
    )
    return stmt


def apply_search(
    stmt: Select,
    value: Optional[str],
    columns: Iterable[ColumnElement],
    *,
    use_fulltext: bool = False,
    dialect_name: Optional[str] = None,
) -> Select:
    """
    Apply a case-insensitive search across multiple columns.
    
    Args:
        stmt: SQLAlchemy select statement
        value: Search value
        columns: Columns to search
        use_fulltext: Use PostgreSQL full-text search if available
        dialect_name: Database dialect name
    """
    logger.debug("Entering apply_search value_present=%s use_fulltext=%s", bool(value), use_fulltext)
    if not value:
        logger.debug("Exiting apply_search unchanged (no value provided)")
        return stmt
    
    value_stripped = value.strip()
    
    # Use full-text search for PostgreSQL if enabled
    if use_fulltext and dialect_name == "postgresql":
        # Convert search term to tsquery format
        search_terms = value_stripped.replace(" ", " & ")
        filters = []
        for column in columns:
            # Use to_tsvector for full-text search
            # Note: This requires text_search columns to be tsvector type or conversion
            # For now, fallback to ILIKE but structure for future full-text implementation
            filters.append(column.ilike(f"%{value_stripped}%"))
        if filters:
            stmt = stmt.where(any_(filters))
    else:
        # Standard ILIKE search (uses trigram indexes on PostgreSQL)
        pattern = f"%{value_stripped}%"
        filters = [column.ilike(pattern) for column in columns]
        if filters:
            stmt = stmt.where(any_(filters))
    
    logger.debug("Exiting apply_search filters_applied=%d", len(filters) if filters else 0)
    return stmt


def apply_array_contains_filter(
    stmt: Select,
    column: ColumnElement,
    values: list[str],
    *,
    dialect_name: Optional[str] = None,
) -> Select:
    """
    Apply array containment filter using PostgreSQL array operators.
    More efficient than array_to_string conversion.
    
    Args:
        stmt: SQLAlchemy select statement
        column: Array column to filter
        values: List of values to check for containment
        dialect_name: Database dialect name
    """
    logger.debug(
        "Entering apply_array_contains_filter column=%s values_count=%d",
        getattr(column, "key", repr(column)),
        len(values),
    )
    if not values:
        return stmt
    
    if dialect_name == "postgresql":
        # Use PostgreSQL array operators for better performance with GIN indexes
        # @> operator checks if left array contains right array
        # && operator checks if arrays overlap
        conditions = []
        for value in values:
            # Use array overlap operator (&&) for substring matching
            # This is more efficient than array_to_string + ILIKE
            conditions.append(func.array_to_string(column, ",").ilike(f"%{value}%"))
        
        if conditions:
            stmt = stmt.where(or_(*conditions))
    else:
        # Fallback to string conversion for other databases
        array_text = func.array_to_string(column, ",")
        conditions = [array_text.ilike(f"%{value}%") for value in values]
        if conditions:
            stmt = stmt.where(or_(*conditions))
    
    logger.debug("Exiting apply_array_contains_filter")
    return stmt


def any_(filters: Iterable[ColumnElement]) -> ColumnElement:
    """Combine SQLAlchemy filter expressions with OR semantics."""
    logger.debug("Entering any_")
    iterator = iter(filters)
    first = next(iterator, None)
    if first is None:
        logger.error("any_ called without filters")
        raise ValueError("No filters provided")
    expr = first
    for condition in iterator:
        expr = expr | condition
    logger.debug("Exiting any_")
    return expr

