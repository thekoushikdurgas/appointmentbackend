"""Performance tests comparing VQL vs Direct DB query performance."""

import time
from typing import Dict, List

import pytest

from app.core.config import get_settings

settings = get_settings()


@pytest.mark.asyncio
@pytest.mark.performance
class TestVQLPerformance:
    """Performance benchmarks for VQL queries vs direct database queries."""

    @pytest.mark.skip(reason="Requires test database and Connectra service")
    async def test_single_contact_retrieval_performance(self):
        """Benchmark single contact retrieval: VQL vs Direct query."""
        # This test would:
        # 1. Measure time for VQL query via Connectra
        # 2. Measure time for direct repository query
        # 3. Compare results and ensure VQL is within acceptable threshold (≤20% slower)
        pass

    @pytest.mark.skip(reason="Requires test database and Connectra service")
    async def test_company_contacts_listing_performance(self):
        """Benchmark company contacts listing: VQL vs Direct query."""
        # This test would:
        # 1. Measure time for VQL query with company_id filter
        # 2. Measure time for direct repository query
        # 3. Compare results
        pass

    @pytest.mark.skip(reason="Requires test database and Connectra service")
    async def test_batch_export_performance(self):
        """Benchmark batch export queries: VQL vs Direct query."""
        # This test would:
        # 1. Measure time for VQL batch queries (100-1000 records)
        # 2. Measure time for direct repository batch queries
        # 3. Compare memory usage
        pass

    @pytest.mark.skip(reason="Requires test database and Connectra service")
    async def test_linkedin_search_performance(self):
        """Benchmark LinkedIn search: VQL vs Direct query."""
        # This test would:
        # 1. Measure time for VQL keyword_match on linkedin_url
        # 2. Measure time for direct repository query on ContactMetadata/CompanyMetadata
        # 3. Compare results
        pass


@pytest.mark.asyncio
@pytest.mark.performance
class TestVQLScalability:
    """Test VQL performance at scale."""

    @pytest.mark.skip(reason="Requires large test dataset")
    async def test_large_export_performance(self):
        """Test export performance with large datasets (10k+ records)."""
        # This test would:
        # 1. Test VQL batch queries with 10k+ UUIDs
        # 2. Measure chunking performance
        # 3. Monitor memory usage
        pass

    @pytest.mark.skip(reason="Requires large test dataset")
    async def test_complex_filter_performance(self):
        """Test VQL performance with complex filters."""
        # This test would:
        # 1. Test VQL queries with multiple filter conditions
        # 2. Compare with direct repository queries
        # 3. Measure query planning time
        pass


def benchmark_query(
    query_func,
    iterations: int = 10,
    warmup: int = 2
) -> Dict[str, float]:
    """
    Helper function to benchmark a query function.
    
    Args:
        query_func: Async function to benchmark
        iterations: Number of iterations to run
        warmup: Number of warmup iterations (not counted)
    
    Returns:
        Dictionary with min, max, avg, median times in seconds
    """
    # Warmup
    for _ in range(warmup):
        await query_func()
    
    # Actual benchmark
    times: List[float] = []
    for _ in range(iterations):
        start = time.time()
        await query_func()
        elapsed = time.time() - start
        times.append(elapsed)
    
    times.sort()
    return {
        "min": times[0],
        "max": times[-1],
        "avg": sum(times) / len(times),
        "median": times[len(times) // 2],
        "p95": times[int(len(times) * 0.95)],
        "p99": times[int(len(times) * 0.99)] if len(times) > 1 else times[0],
    }


def compare_performance(
    vql_times: Dict[str, float],
    direct_times: Dict[str, float],
    threshold: float = 1.2
) -> Dict[str, any]:
    """
    Compare VQL and direct query performance.
    
    Args:
        vql_times: Performance metrics for VQL query
        direct_times: Performance metrics for direct query
        threshold: Acceptable slowdown threshold (1.2 = 20% slower)
    
    Returns:
        Comparison results with pass/fail status
    """
    vql_avg = vql_times["avg"]
    direct_avg = direct_times["avg"]
    
    ratio = vql_avg / direct_avg if direct_avg > 0 else float('inf')
    passed = ratio <= threshold
    
    return {
        "vql_avg": vql_avg,
        "direct_avg": direct_avg,
        "ratio": ratio,
        "slowdown_percent": (ratio - 1) * 100,
        "passed": passed,
        "threshold": threshold,
    }

