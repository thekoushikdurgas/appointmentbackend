"""Query composition helpers for SQLAlchemy statements."""

from __future__ import annotations

from typing import Iterable, Mapping, Optional

from sqlalchemy import ColumnElement, Select, asc, desc

from app.core.logging import get_logger

logger = get_logger(__name__)


def apply_ilike_filter(
    stmt: Select,
    column: ColumnElement,
    value: Optional[str],
) -> Select:
    """Apply a case-insensitive partial match when a value is provided."""
    logger.debug(
        "Entering apply_ilike_filter column=%s value_present=%s",
        getattr(column, "key", repr(column)),
        bool(value),
    )
    if value:
        stmt = stmt.where(column.ilike(f"%{value.strip()}%"))
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
) -> Select:
    """Apply a case-insensitive search across multiple columns."""
    logger.debug("Entering apply_search value_present=%s", bool(value))
    if not value:
        logger.debug("Exiting apply_search unchanged (no value provided)")
        return stmt
    pattern = f"%{value.strip()}%"
    filters = [column.ilike(pattern) for column in columns]
    if filters:
        stmt = stmt.where(any_(filters))
        logger.debug("Exiting apply_search filters_applied=%d", len(filters))
    else:
        logger.debug("Exiting apply_search no filters generated")
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

