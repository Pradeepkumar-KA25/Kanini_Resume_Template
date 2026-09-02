from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

SupportedOutput = Literal["html", "docx", "pdf"]


class TemplateMetadata(BaseModel):
    """Stable, renderer-independent metadata loaded from a template manifest."""

    model_config = ConfigDict(extra="forbid")

    id: str
    display_name: str
    description: str
    version: str
    enabled: bool
    supported_outputs: list[SupportedOutput]
    page_size: Literal["LETTER", "A4"]
    aliases: list[str] = Field(default_factory=list)
    assets: dict[str, str] = Field(default_factory=dict)
    download_base_name: str = "resume"
    user_created: bool = False

    @field_validator("id", "display_name", "description", "version", "download_base_name", mode="before")
    @classmethod
    def required_text(cls, value: object) -> str:
        text = str(value or "").strip()
        if not text:
            raise ValueError("must not be empty")
        return text

    @field_validator("aliases", mode="before")
    @classmethod
    def clean_aliases(cls, value: object) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("must be a list")
        return [str(alias).strip() for alias in value if str(alias).strip()]

    @field_validator("supported_outputs")
    @classmethod
    def require_outputs(cls, value: list[SupportedOutput]) -> list[SupportedOutput]:
        if not value:
            raise ValueError("must include at least one output")
        if len(set(value)) != len(value):
            raise ValueError("must not contain duplicate outputs")
        return value

    def public_dict(self) -> dict[str, object]:
        return self.model_dump(exclude={"aliases", "assets", "download_base_name"})