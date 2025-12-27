"""VQL parser for validating and parsing JSON VQL queries."""

import json
from typing import Any, Dict

from pydantic import ValidationError

from app.core.vql.structures import VQLQuery
from app.utils.logger import get_logger

logger = get_logger(__name__)


class VQLParser:
    """Parser for VQL query JSON."""

    @staticmethod
    def parse(query_data: Dict[str, Any]) -> VQLQuery:
        """
        Parse and validate a VQL query from a dictionary.

        Args:
            query_data: Dictionary containing VQL query structure

        Returns:
            Validated VQLQuery instance

        Raises:
            ValueError: If query data is invalid
        """
        try:
            return VQLQuery.model_validate(query_data)
        except ValidationError as e:
            error_messages = []
            for error in e.errors():
                field = " -> ".join(str(loc) for loc in error["loc"])
                msg = error["msg"]
                error_messages.append(f"{field}: {msg}")
            raise ValueError(f"Invalid VQL query: {'; '.join(error_messages)}") from e

    @staticmethod
    def parse_json(json_str: str) -> VQLQuery:
        """
        Parse and validate a VQL query from JSON string.

        Args:
            json_str: JSON string containing VQL query

        Returns:
            Validated VQLQuery instance

        Raises:
            ValueError: If JSON is invalid or query structure is invalid
        """
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}") from e

        return VQLParser.parse(data)

