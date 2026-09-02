from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _text(value: Any) -> str:
    return str(value or "").strip()


def _text_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    return [_text(item) for item in value if _text(item)]


class ContactInfo(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    linkedin: str = ""
    github: str = ""

    _clean_text = field_validator("*", mode="before")(_text)


class Project(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str = ""
    client: str = ""
    duration: str = ""
    role: str = ""
    description: str = ""
    technologies: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)

    _clean_text = field_validator("name", "client", "duration", "role", "description", mode="before")(_text)
    _clean_lists = field_validator("technologies", "responsibilities", mode="before")(_text_list)


class Experience(BaseModel):
    model_config = ConfigDict(extra="ignore")

    company: str = ""
    company_name: str = ""
    company_sector: str = ""
    title: str = ""
    location: str = ""
    dates: str = ""
    responsibilities: list[str] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)

    _clean_text = field_validator(
        "company", "company_name", "company_sector", "title", "location", "dates", mode="before"
    )(_text)
    _clean_responsibilities = field_validator("responsibilities", mode="before")(_text_list)


class Education(BaseModel):
    model_config = ConfigDict(extra="ignore")

    degree: str = ""
    institution: str = ""
    year: str = ""
    gpa: str = ""

    _clean_text = field_validator("*", mode="before")(_text)


class ResumeData(BaseModel):
    """Canonical, template-independent representation of an extracted resume."""

    model_config = ConfigDict(extra="ignore")

    contact: ContactInfo = Field(default_factory=ContactInfo)
    summary: str = ""
    skills: dict[str, list[str]] = Field(default_factory=dict)
    experience: list[Experience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)
    additional_sections: dict[str, list[str]] = Field(default_factory=dict)

    _clean_summary = field_validator("summary", mode="before")(_text)
    _clean_lists = field_validator("certifications", "achievements", mode="before")(_text_list)

    @field_validator("skills", mode="before")
    @classmethod
    def clean_skills(cls, value: Any) -> dict[str, list[str]]:
        if isinstance(value, list):
            return {"Technical Skills": _text_list(value)}
        if not isinstance(value, dict):
            return {}
        return {_text(key) or "Technical Skills": _text_list(items) for key, items in value.items()}

    @field_validator("additional_sections", mode="before")
    @classmethod
    def clean_additional_sections(cls, value: Any) -> dict[str, list[str]]:
        if not isinstance(value, dict):
            return {}
        return {_text(key): _text_list(items) for key, items in value.items() if _text(key)}