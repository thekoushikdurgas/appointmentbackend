"""Database-level aggregation utilities for PostgreSQL.

This module provides utilities for performing aggregations and transformations
at the database level using PostgreSQL functions, reducing data transfer and
Python-side processing.

Usage:
    from app.utils.db_aggregations import build_json_object, aggregate_array
    
    # Build JSON object in database
    query = select(
        build_json_object(
            id=Contact.id,
            name=Contact.first_name,
            email=Contact.email
        )
    )
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql.elements import ColumnElement

from app.core.logging import get_logger

logger = get_logger(__name__)


def build_json_object(**kwargs: Any) -> ColumnElement:
    """
    Build a JSON object at the database level using PostgreSQL's json_build_object.
    
    This is more efficient than building JSON objects in Python, especially for
    large datasets, as it reduces data transfer and processing.
    
    Args:
        **kwargs: Key-value pairs where keys are JSON keys and values are SQLAlchemy columns/expressions
        
    Returns:
        SQLAlchemy column element representing the JSON object
        
    Example:
        query = select(
            build_json_object(
                id=Contact.id,
                name=func.concat(Contact.first_name, ' ', Contact.last_name),
                email=Contact.email
            )
        )
    """
    # PostgreSQL json_build_object takes alternating key-value pairs
    # We need to flatten kwargs into a list: [key1, value1, key2, value2, ...]
    args = []
    for key, value in kwargs.items():
        args.append(key)
        args.append(value)
    
    return func.json_build_object(*args)


def build_jsonb_object(**kwargs: Any) -> ColumnElement:
    """
    Build a JSONB object at the database level using PostgreSQL's jsonb_build_object.
    
    Similar to build_json_object but returns JSONB type for better performance
    with JSON operations and indexing.
    
    Args:
        **kwargs: Key-value pairs where keys are JSON keys and values are SQLAlchemy columns/expressions
        
    Returns:
        SQLAlchemy column element representing the JSONB object
    """
    args = []
    for key, value in kwargs.items():
        args.append(key)
        args.append(value)
    
    return func.jsonb_build_object(*args)


def aggregate_array(
    column: ColumnElement,
    distinct: bool = False,
    order_by: Optional[ColumnElement] = None,
) -> ColumnElement:
    """
    Aggregate values into an array at the database level.
    
    More efficient than collecting values in Python, especially for large result sets.
    
    Args:
        column: Column to aggregate
        distinct: If True, only include distinct values
        order_by: Optional column to order the array by
        
    Returns:
        SQLAlchemy column element representing the aggregated array
        
    Example:
        # Get all unique email domains
        query = select(
            aggregate_array(Contact.email, distinct=True)
        ).group_by(func.split_part(Contact.email, '@', 2))
    """
    if distinct:
        if order_by:
            return func.array_agg(column.distinct().order_by(order_by))
        return func.array_agg(column.distinct())
    else:
        if order_by:
            return func.array_agg(column.order_by(order_by))
        return func.array_agg(column)


def json_agg(column: ColumnElement, order_by: Optional[ColumnElement] = None) -> ColumnElement:
    """
    Aggregate rows into a JSON array at the database level.
    
    Useful for building nested JSON structures directly in the database.
    
    Args:
        column: Column or expression to aggregate (often a JSON object)
        order_by: Optional column to order the array by
        
    Returns:
        SQLAlchemy column element representing the JSON array
        
    Example:
        # Get contacts as JSON array grouped by company
        query = select(
            Company.name,
            json_agg(
                build_json_object(
                    id=Contact.id,
                    name=Contact.first_name
                )
            )
        ).group_by(Company.name)
    """
    if order_by:
        return func.json_agg(column.order_by(order_by))
    return func.json_agg(column)


def array_to_string(column: ColumnElement, delimiter: str = ",") -> ColumnElement:
    """
    Convert an array column to a delimited string at the database level.
    
    More efficient than converting arrays to strings in Python.
    
    Args:
        column: Array column to convert
        delimiter: String delimiter (default: comma)
        
    Returns:
        SQLAlchemy column element representing the string
    """
    return func.array_to_string(column, delimiter)


def string_to_array(column: ColumnElement, delimiter: str = ",") -> ColumnElement:
    """
    Convert a string column to an array at the database level.
    
    Args:
        column: String column to convert
        delimiter: String delimiter (default: comma)
        
    Returns:
        SQLAlchemy column element representing the array
    """
    return func.string_to_array(column, delimiter)

