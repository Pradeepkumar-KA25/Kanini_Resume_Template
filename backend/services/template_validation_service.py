from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from models.template_spec import TemplateSpec


class TemplateSpecValidationError(ValueError):
    """Raised when generated template JSON is outside the safe specification."""


def validate_template_spec(payload: Any) -> TemplateSpec:
    if not isinstance(payload, dict):
        raise TemplateSpecValidationError("Template specification must be a JSON object.")
    try:
        return TemplateSpec.model_validate(payload)
    except ValidationError as exc:
        details = "; ".join(error["msg"] for error in exc.errors()[:3])
        raise TemplateSpecValidationError(f"Generated template specification is invalid: {details}") from exc
