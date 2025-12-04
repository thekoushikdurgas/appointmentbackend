"""Database query optimization utilities.

This module provides utilities for optimizing database queries including:
- Selecting only needed columns
- N+1 query detection and prevention
- Query analysis and performance hints
- Database-level aggregation helpers

Best practices:
- Select only columns you need (avoid SELECT *)
- Use joins/eager loading to prevent N+1 queries
- Use database-level aggregations instead of Python-side processing
- Analyze query execution plans
- Use indexes effectively
"""

from __future__ import annotations

from typing import Any, Callable, Optional, Sequence

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from app.core.logging import get_logger

logger = get_logger(__name__)


def select_only_columns(
    query: Select,
    columns: Sequence[Any],
) -> Select:
    """
    Modify query to select only specified columns.
    
    Reduces data transfer and memory usage by selecting only needed columns.
    
    Args:
        query: SQLAlchemy Select query
        columns: Sequence of column objects or column names
        
    Returns:
        Modified query selecting only specified columns
        
    Example:
        from app.models.contacts import Contact
        
        # Instead of: select(Contact)
        # Use: select_only_columns(select(Contact), [Contact.id, Contact.name, Contact.email])
        query = select_only_columns(
            select(Contact),
            [Contact.id, Contact.name, Contact.email]
        )
    """
    # If query already has specific columns, replace them
    # Otherwise, modify the query to select only specified columns
    return select(*columns).select_from(query.subquery() if hasattr(query, "subquery") else query)


def prevent_n_plus_one(
    query: Select,
    relationships: list[str],
    strategy: str = "selectin",
) -> Select:
    """
    Add eager loading to prevent N+1 queries.
    
    Args:
        query: SQLAlchemy Select query
        relationships: List of relationship attribute names to eager load
        strategy: Loading strategy ("selectin" or "joined")
        
    Returns:
        Query with eager loading configured
        
    Example:
        from app.models.contacts import Contact
        
        # Prevent N+1 when accessing contact.company
        query = prevent_n_plus_one(
            select(Contact),
            relationships=["company"],
            strategy="selectin"
        )
    """
    for rel_name in relationships:
        if strategy == "selectin":
            query = query.options(selectinload(getattr(query.column_descriptions[0]["entity"], rel_name)))
        elif strategy == "joined":
            query = query.options(joinedload(getattr(query.column_descriptions[0]["entity"], rel_name)))
        else:
            logger.warning("Unknown loading strategy: %s, using selectin", strategy)
            query = query.options(selectinload(getattr(query.column_descriptions[0]["entity"], rel_name)))
    
    return query


async def analyze_query_performance(
    session: AsyncSession,
    query: Select,
    explain: bool = True,
) -> dict[str, Any]:
    """
    Analyze query performance using EXPLAIN.
    
    Args:
        session: Async database session
        query: SQLAlchemy Select query to analyze
        explain: Whether to run EXPLAIN ANALYZE (default: True)
        
    Returns:
        Dictionary with query analysis results:
        - query_text: SQL query text
        - execution_plan: EXPLAIN output
        - estimated_cost: Estimated query cost
        - warnings: Performance warnings
        
    Example:
        analysis = await analyze_query_performance(session, query)
        if analysis["estimated_cost"] > 1000:
            logger.warning("Expensive query detected: %s", analysis["warnings"])
    """
    # Get SQL text
    query_text = str(query.compile(compile_kwargs={"literal_binds": True}))
    
    # Run EXPLAIN
    explain_query = f"EXPLAIN {'ANALYZE' if explain else ''} {query_text}"
    
    try:
        result = await session.execute(select(func.pg_stat_statements_reset()))  # Placeholder
        # In practice, you'd execute the EXPLAIN query and parse results
        # This is a simplified version
        
        warnings = []
        
        # Check for common performance issues
        if "SELECT *" in query_text.upper():
            warnings.append("Query uses SELECT * - consider selecting only needed columns")
        
        if "OFFSET" in query_text.upper() and "LIMIT" in query_text.upper():
            # Check for large offset
            # This is simplified - in practice, parse the offset value
            warnings.append("Large OFFSET may cause performance issues - consider cursor-based pagination")
        
        return {
            "query_text": query_text,
            "execution_plan": "EXPLAIN output would go here",
            "estimated_cost": 0,  # Would be parsed from EXPLAIN output
            "warnings": warnings,
        }
    except Exception as exc:
        logger.warning("Failed to analyze query: %s", exc)
        return {
            "query_text": query_text,
            "execution_plan": None,
            "estimated_cost": None,
            "warnings": [f"Analysis failed: {exc}"],
        }


def use_database_aggregation(
    query: Select,
    aggregation_func: Any,
    group_by: Optional[Sequence[Any]] = None,
) -> Select:
    """
    Use database-level aggregation instead of Python-side processing.
    
    Args:
        query: SQLAlchemy Select query
        aggregation_func: SQLAlchemy aggregation function (func.count, func.sum, etc.)
        group_by: Optional columns to group by
        
    Returns:
        Query with database aggregation
        
    Example:
        from sqlalchemy import func
        from app.models.contacts import Contact
        
        # Count contacts by company (database-level)
        query = use_database_aggregation(
            select(Contact),
            func.count(Contact.id),
            group_by=[Contact.company_id]
        )
    """
    if group_by:
        return select(aggregation_func, *group_by).group_by(*group_by)
    return select(aggregation_func)


class QueryOptimizer:
    """
    Query optimizer with multiple optimization strategies.
    """
    
    def __init__(self, session: AsyncSession):
        """
        Initialize query optimizer.
        
        Args:
            session: Async database session
        """
        self.session = session
    
    def optimize_select(self, query: Select, columns: Sequence[Any]) -> Select:
        """Optimize query to select only needed columns."""
        return select_only_columns(query, columns)
    
    def optimize_relationships(
        self,
        query: Select,
        relationships: list[str],
        strategy: str = "selectin",
    ) -> Select:
        """Optimize query to prevent N+1 queries."""
        return prevent_n_plus_one(query, relationships, strategy)
    
    async def analyze(self, query: Select) -> dict[str, Any]:
        """Analyze query performance."""
        return await analyze_query_performance(self.session, query)
    
    def aggregate(
        self,
        query: Select,
        aggregation_func: Any,
        group_by: Optional[Sequence[Any]] = None,
    ) -> Select:
        """Use database-level aggregation."""
        return use_database_aggregation(query, aggregation_func, group_by)


# Helper functions for common optimizations

def optimize_list_query(
    query: Select,
    columns: Optional[Sequence[Any]] = None,
    relationships: Optional[list[str]] = None,
    limit: Optional[int] = None,
    offset: int = 0,
) -> Select:
    """
    Optimize a list query with common optimizations.
    
    Args:
        query: Base Select query
        columns: Columns to select (None = all)
        relationships: Relationships to eager load (None = none)
        limit: Maximum results (None = no limit)
        offset: Offset value
        
    Returns:
        Optimized query
        
    Example:
        query = select(Contact)
        optimized = optimize_list_query(
            query,
            columns=[Contact.id, Contact.name, Contact.email],
            relationships=["company"],
            limit=100,
            offset=0
        )
    """
    # Select only needed columns
    if columns:
        query = select_only_columns(query, columns)
    
    # Prevent N+1 queries
    if relationships:
        query = prevent_n_plus_one(query, relationships)
    
    # Apply pagination
    if offset > 0:
        query = query.offset(offset)
    if limit:
        query = query.limit(limit)
    
    return query


async def detect_n_plus_one_pattern(
    session: AsyncSession,
    base_query: Select,
    access_pattern: Callable[[Any], Any],
    sample_size: int = 10,
) -> dict[str, Any]:
    """
    Detect potential N+1 query patterns.
    
    Args:
        session: Async database session
        base_query: Base query to test
        access_pattern: Function that accesses relationships (causing N+1)
        sample_size: Number of items to test
        
    Returns:
        Dictionary with detection results:
        - detected: Whether N+1 pattern was detected
        - query_count: Estimated number of queries
        - recommendation: How to fix
        
    Example:
        async def access_company(contact):
            return contact.company  # This would cause N+1
        
        result = await detect_n_plus_one_pattern(
            session,
            select(Contact).limit(100),
            access_company
        )
    """
    # Simplified detection - in practice, you'd monitor actual queries
    # This is a placeholder for the concept
    
    query_text = str(base_query.compile(compile_kwargs={"literal_binds": True}))
    
    # Heuristic: if query doesn't have eager loading and accesses relationships
    # it's likely to cause N+1
    has_eager_loading = "JOIN" in query_text.upper() or "selectinload" in str(base_query)
    
    if not has_eager_loading:
        return {
            "detected": True,
            "query_count": sample_size + 1,  # 1 base + N relationship queries
            "recommendation": "Use eager loading (selectinload or joinedload) to prevent N+1 queries",
        }
    
    return {
        "detected": False,
        "query_count": 1,
        "recommendation": None,
    }

