from __future__ import annotations

from typing import Iterable, Mapping, Optional

from sqlalchemy import ColumnElement, Select, asc, desc
from sqlalchemy.sql import Select as SelectType


def apply_ilike_filter(
    stmt: Select,
    column: ColumnElement,
    value: Optional[str],
) -> Select:
    if value:
        stmt = stmt.where(column.ilike(f"%{value.strip()}%"))
    return stmt


def apply_exact_filter(
    stmt: Select,
    column: ColumnElement,
    value: Optional[str],
) -> Select:
    if value:
        stmt = stmt.where(column == value)
    return stmt


def apply_numeric_range_filter(
    stmt: Select,
    column: ColumnElement,
    minimum: Optional[int],
    maximum: Optional[int],
) -> Select:
    if minimum is not None:
        stmt = stmt.where(column >= minimum)
    if maximum is not None:
        stmt = stmt.where(column <= maximum)
    return stmt


def apply_ordering(
    stmt: Select,
    ordering: Optional[str],
    mapping: Mapping[str, ColumnElement],
) -> Select:
    if not ordering:
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
        if column is not None:
            order_by_columns.append(direction(column))
    if order_by_columns:
        stmt = stmt.order_by(*order_by_columns)
    return stmt


def apply_search(
    stmt: Select,
    value: Optional[str],
    columns: Iterable[ColumnElement],
) -> Select:
    if not value:
        return stmt
    pattern = f"%{value.strip()}%"
    filters = [column.ilike(pattern) for column in columns]
    if filters:
        stmt = stmt.where(any_(filters))
    return stmt


def any_(filters: Iterable[ColumnElement]) -> ColumnElement:
    iterator = iter(filters)
    first = next(iterator, None)
    if first is None:
        raise ValueError("No filters provided")
    expr = first
    for condition in iterator:
        expr = expr | condition
    return expr

