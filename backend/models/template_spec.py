from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Color = str
SectionName = Literal["summary", "skills", "experience", "projects", "education", "certifications", "achievements"]

_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


class PageSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    size: Literal["A4", "LETTER"] = "A4"
    orientation: Literal["portrait"] = "portrait"
    margin_inches: float = Field(default=0.65, ge=0.35, le=1.25)


class TypographySpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    font_family: Literal["Arial", "Calibri", "Georgia", "Helvetica", "Times New Roman"] = "Calibri"
    base_size_pt: int = Field(default=10, ge=8, le=14)
    heading_size_pt: int = Field(default=14, ge=12, le=24)

    @model_validator(mode="after")
    def heading_is_larger_than_body(self):
        if self.heading_size_pt <= self.base_size_pt:
            raise ValueError("heading size must be larger than base size")
        return self


class ColorSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: Color = "#1F2937"
    accent: Color = "#0072B4"
    muted: Color = "#64748B"

    @field_validator("text", "accent", "muted")
    @classmethod
    def valid_color(cls, value: str) -> str:
        if not _COLOR_RE.fullmatch(value):
            raise ValueError("must be a six-digit hexadecimal color")
        return value.upper()


class HeaderSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    layout: Literal["centered", "left"] = "centered"
    contact_layout: Literal["inline", "stacked"] = "inline"
    show_divider: bool = True


class LayoutSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    columns: Literal[1, 2] = 1
    sidebar_position: Literal["left", "right", "none"] = "none"
    section_alignment: Literal["left", "justified"] = "left"

    @field_validator("sidebar_position")
    @classmethod
    def sidebar_matches_columns(cls, value: str, info):
        columns = info.data.get("columns", 1)
        if columns == 1 and value != "none":
            raise ValueError("single-column layouts must use a 'none' sidebar position")
        if columns == 2 and value == "none":
            raise ValueError("two-column layouts require a sidebar position")
        return value


class SpacingSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section_gap_pt: int = Field(default=12, ge=4, le=28)
    line_height: float = Field(default=1.35, ge=1.0, le=1.8)
    divider_style: Literal["none", "solid", "accent"] = "solid"
    skill_style: Literal["inline", "bullets", "tags"] = "inline"


class TemplateSpec(BaseModel):
    """A constrained, non-executable description of a reusable resume layout."""

    model_config = ConfigDict(extra="forbid")

    page: PageSpec = Field(default_factory=PageSpec)
    typography: TypographySpec = Field(default_factory=TypographySpec)
    colors: ColorSpec = Field(default_factory=ColorSpec)
    header: HeaderSpec = Field(default_factory=HeaderSpec)
    layout: LayoutSpec = Field(default_factory=LayoutSpec)
    sections: list[SectionName] = Field(default_factory=lambda: ["summary", "skills", "experience", "education"])
    spacing: SpacingSpec = Field(default_factory=SpacingSpec)

    @field_validator("sections")
    @classmethod
    def valid_sections(cls, value: list[SectionName]) -> list[SectionName]:
        if not value:
            raise ValueError("must include at least one section")
        if len(value) != len(set(value)):
            raise ValueError("must not contain duplicate sections")
        return value
