from pydantic import ConfigDict
from datetime import datetime, timezone
from typing import Any
from app.utils.datetime_utils import ensure_utc_datetime, format_utc_datetime

class BaseModelConfig:
    """Base configuration for all Pydantic models to ensure consistent datetime handling"""
    
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: format_utc_datetime(v) if v else None
        },
        validate_assignment=True,
        arbitrary_types_allowed=True
    )

def validate_datetime_fields(model: Any) -> Any:
    """
    Validate and normalize datetime fields in a model instance.
    This ensures all datetime fields are UTC timezone-aware.
    """
    for field_name, field_value in model.__dict__.items():
        if isinstance(field_value, datetime):
            normalized_dt = ensure_utc_datetime(field_value)
            if normalized_dt != field_value:
                setattr(model, field_name, normalized_dt)
                # Log the change for debugging
                import logging
                logger = logging.getLogger(__name__)
                logger.debug(f"Normalized datetime field {field_name}: {field_value} -> {normalized_dt}")
    
    return model
