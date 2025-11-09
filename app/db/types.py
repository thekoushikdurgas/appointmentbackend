"""Custom SQLAlchemy type implementations."""

from __future__ import annotations

import json
from typing import Any, Optional

from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.sql.type_api import TypeEngine
from sqlalchemy.types import Text, TypeDecorator

from app.core.logging import get_logger

logger = get_logger(__name__)


class StringList(TypeDecorator[list[str]]):
    """
    A TypeDecorator that stores lists of strings as PostgreSQL ARRAY
    when available, and falls back to JSON-encoded TEXT for other dialects
    (e.g., SQLite used in tests).
    """

    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect) -> TypeEngine[Any]:
        """Resolve the underlying database type for the current dialect."""
        logger.debug("Entering StringList.load_dialect_impl dialect=%s", dialect.name)
        if dialect.name == "postgresql":
            descriptor = dialect.type_descriptor(ARRAY(Text))
        else:
            descriptor = dialect.type_descriptor(Text)
        logger.debug(
            "Exiting StringList.load_dialect_impl dialect=%s impl=%s",
            dialect.name,
            descriptor,
        )
        return descriptor

    def process_bind_param(
        self,
        value: Optional[list[str]],
        dialect,
    ) -> Optional[str | list[str]]:
        """Serialize Python values before persistence."""
        logger.debug(
            "Entering StringList.process_bind_param dialect=%s value_present=%s",
            dialect.name,
            value is not None,
        )
        if value is None:
            logger.debug("Exiting StringList.process_bind_param result=None")
            return None
        if dialect.name == "postgresql":
            logger.debug("Exiting StringList.process_bind_param passthrough array")
            return value
        serialized = json.dumps(value)
        logger.debug("Exiting StringList.process_bind_param serialized_length=%d", len(serialized))
        return serialized

    def process_result_value(
        self,
        value: Optional[str | list[str]],
        dialect,
    ) -> Optional[list[str]]:
        """Deserialize database values into Python lists."""
        logger.debug(
            "Entering StringList.process_result_value dialect=%s value_present=%s",
            dialect.name,
            value is not None,
        )
        if value is None:
            logger.debug("Exiting StringList.process_result_value result=None")
            return None
        if dialect.name == "postgresql":
            result = list(value) if isinstance(value, tuple) else value  # type: ignore[return-value]
            logger.debug(
                "Exiting StringList.process_result_value postgres result_length=%d",
                len(result) if result else 0,
            )
            return result
        deserialized = json.loads(value)
        logger.debug(
            "Exiting StringList.process_result_value json result_length=%d",
            len(deserialized),
        )
        return deserialized

