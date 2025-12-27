"""Custom SQLAlchemy type implementations."""

from __future__ import annotations

import enum
import json
from typing import Any, Optional

from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM
from sqlalchemy.sql.type_api import TypeEngine
from sqlalchemy.types import Text, TypeDecorator

from app.utils.logger import get_logger

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
        if dialect.name == "postgresql":
            descriptor = dialect.type_descriptor(ARRAY(Text))
        else:
            descriptor = dialect.type_descriptor(Text)
        return descriptor

    def process_bind_param(
        self,
        value: Optional[list[str]],
        dialect,
    ) -> Optional[str | list[str]]:
        """Serialize Python values before persistence."""
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        serialized = json.dumps(value)
        return serialized

    def process_result_value(
        self,
        value: Optional[str | list[str]],
        dialect,
    ) -> Optional[list[str]]:
        """Deserialize database values into Python lists."""
        if value is None:
            return None
        if dialect.name == "postgresql":
            result = list(value) if isinstance(value, tuple) else value  # type: ignore[return-value]
            return result
        deserialized = json.loads(value)
        return deserialized


class EnumValue(TypeDecorator[str]):
    """
    A TypeDecorator that ensures enum values (not names) are used when storing to database.
    Works with str-based enums to ensure the enum's .value property is used.
    """

    impl = Text
    cache_ok = True

    def __init__(self, enum_class: type[enum.Enum], enum_name: str, *args: Any, **kwargs: Any):
        """Initialize with the enum class and database enum type name."""
        super().__init__(*args, **kwargs)
        self.enum_class = enum_class
        self.enum_name = enum_name
        # Extract enum values (not names) for the PostgreSQL ENUM type
        # This ensures the database enum uses the enum values, not the member names
        enum_values = [member.value for member in enum_class]
        # Create SQLEnum with values_callable to use enum values instead of names
        # For PostgreSQL, we'll use PG_ENUM directly with the enum values
        self.sql_enum = SQLEnum(enum_class, name=enum_name, create_constraint=True)
        # Store enum values for PostgreSQL ENUM creation
        self.enum_values = enum_values

    def load_dialect_impl(self, dialect) -> TypeEngine[Any]:
        """
        Use the underlying SQL enum type for the database.
        
        For PostgreSQL, we use PG_ENUM with the enum values (not names) to ensure
        the database enum type matches the Python enum values. Our process_bind_param
        will convert enum objects to their string values before binding.
        """
        # For PostgreSQL, use PG_ENUM directly with enum values
        # Our process_bind_param will ensure enum objects are converted to their values
        if dialect.name == "postgresql":
            # Create PostgreSQL ENUM with the actual enum values (not names)
            # PG_ENUM accepts values as separate arguments or as a sequence
            # We'll unpack the list to pass values as separate arguments
            pg_enum = PG_ENUM(
                *self.enum_values,  # Unpack list: 'registration', 'login'
                name=self.enum_name,
                create_type=False,  # Don't create type, assume it exists in the database
            )
            # Return the type descriptor - our process_bind_param will be called first
            # to convert enum objects to their string values
            return dialect.type_descriptor(pg_enum)
        
        # For other dialects, use SQLEnum but ensure our process_bind_param handles conversion
        if hasattr(self.sql_enum, 'load_dialect_impl'):
            return self.sql_enum.load_dialect_impl(dialect)
        # Fallback: use dialect's type descriptor for the enum
        return dialect.type_descriptor(self.sql_enum)

    def process_bind_param(self, value: Optional[str | enum.Enum], dialect) -> Optional[str]:
        """
        Convert enum objects to their string values before storing.
        
        This method is called by SQLAlchemy before binding parameters to the database.
        It ensures that enum objects are converted to their .value property (not .name),
        which matches the database enum values.
        """
        if value is None:
            return None
        
        # If it's an enum, use its value (this ensures we always use the enum's value, not its name)
        if isinstance(value, enum.Enum):
            enum_value = value.value
            # Return the lowercase value to ensure it matches the database enum
            return enum_value
        
        # If it's already a string, validate it against the enum class
        if isinstance(value, str):
            # Try to find matching enum member by value (case-insensitive)
            normalized_value = value.lower()
            for enum_member in self.enum_class:
                if enum_member.value.lower() == normalized_value:
                    return enum_member.value
            # If no match found, return the original value
            return value
        
        # Fallback: convert to string
        return str(value)

    def process_result_value(self, value: Optional[str], dialect) -> Optional[str]:
        """Return the string value as-is from the database."""
        return value

