"""Utility for mapping Apollo industry tag IDs to industry names."""

from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

from app.utils.logger import get_logger

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def _load_industry_mapping() -> dict[str, str]:
    """Load industry tag ID to industry name mapping from CSV file."""
    csv_path = Path(__file__).parent.parent / "data" / "industryids.csv"
    
    if not csv_path.exists():
        return {}
    
    mapping: dict[str, str] = {}
    
    try:
        # Use utf-8-sig to automatically handle BOM (Byte Order Mark) if present
        with open(csv_path, encoding="utf-8-sig", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            
            for row in reader:
                tag_id = row.get("Tag ID", "").strip()
                industry = row.get("Industry", "").strip()
                
                # Remove quotes from industry name if present
                if industry.startswith('"') and industry.endswith('"'):
                    industry = industry[1:-1]
                
                if tag_id and industry:
                    # Store as lowercase for consistent matching
                    mapping[tag_id] = industry.lower()
    except Exception as exc:
        return {}
    
    return mapping


def get_industry_names_from_ids(tag_ids: list[str]) -> list[str]:
    """
    Convert Apollo industry tag IDs to industry names.
    
    Uses lru_cache for the immutable industry mapping data, which is loaded once
    per process and cached for the lifetime of the application.
    
    Args:
        tag_ids: List of Apollo industry tag IDs
        
    Returns:
        List of industry names (lowercase) for valid tag IDs
    """
    # Load mapping using lru_cache (loaded once, cached forever)
    tag_id_to_industry = _load_industry_mapping()
    
    if not tag_ids:
        return []
    
    industry_names: list[str] = []
    invalid_ids: list[str] = []
    
    for tag_id in tag_ids:
        tag_id_clean = tag_id.strip()
        if not tag_id_clean:
            continue
        
        industry_name = tag_id_to_industry.get(tag_id_clean)
        if industry_name:
            industry_names.append(industry_name)
        else:
            invalid_ids.append(tag_id_clean)
    
    return industry_names

