"""Utility for mapping Apollo industry tag IDs to industry names."""

from __future__ import annotations

import csv
from pathlib import Path

from app.core.logging import get_logger

logger = get_logger(__name__)

# Cache the mapping at module level
TAG_ID_TO_INDUSTRY: dict[str, str] = {}


def _load_industry_mapping() -> dict[str, str]:
    """Load industry tag ID to industry name mapping from CSV file."""
    csv_path = Path(__file__).parent.parent / "data" / "insdustryids.csv"
    
    if not csv_path.exists():
        logger.error("Industry mapping CSV file not found: %s", csv_path)
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
            
            logger.info(
                "Loaded %d industry tag ID mappings from CSV",
                len(mapping),
            )
    except Exception as exc:
        logger.exception("Failed to load industry mapping CSV: %s", exc)
        return {}
    
    return mapping


def get_industry_names_from_ids(tag_ids: list[str]) -> list[str]:
    """
    Convert Apollo industry tag IDs to industry names.
    
    Args:
        tag_ids: List of Apollo industry tag IDs
        
    Returns:
        List of industry names (lowercase) for valid tag IDs
    """
    global TAG_ID_TO_INDUSTRY
    
    # Load mapping on first use if not already loaded
    if not TAG_ID_TO_INDUSTRY:
        TAG_ID_TO_INDUSTRY = _load_industry_mapping()
    
    if not tag_ids:
        return []
    
    industry_names: list[str] = []
    invalid_ids: list[str] = []
    
    for tag_id in tag_ids:
        tag_id_clean = tag_id.strip()
        if not tag_id_clean:
            continue
        
        industry_name = TAG_ID_TO_INDUSTRY.get(tag_id_clean)
        if industry_name:
            industry_names.append(industry_name)
            logger.debug("Mapped industry tag ID '%s' → '%s'", tag_id_clean, industry_name)
        else:
            invalid_ids.append(tag_id_clean)
            logger.warning("Industry tag ID '%s' not found in mapping", tag_id_clean)
    
    # Log summary
    if industry_names:
        logger.info(
            "Mapped %d/%d industry tag IDs to: %s",
            len(industry_names),
            len(tag_ids),
            ", ".join(industry_names[:5]),  # Show first 5 industry names
        )
        pass
    
    if invalid_ids:
        logger.warning(
            "Found %d invalid industry tag IDs (not in mapping): %s",
            len(invalid_ids),
            invalid_ids[:5],  # Show first 5 invalid IDs
        )
    
    return industry_names

