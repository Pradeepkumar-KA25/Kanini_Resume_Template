from __future__ import annotations

from dataclasses import dataclass

from models.resume import ResumeData


def _roman(number: int) -> str:
    values = ((10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"))
    result = ""
    for value, symbol in values:
        while number >= value:
            result += symbol
            number -= value
    return result


@dataclass(frozen=True)
class Format1ViewModel:
    resume: ResumeData

    @property
    def name(self) -> str:
        return self.resume.contact.name or "CANDIDATE NAME"

    @property
    def contact_parts(self) -> list[str]:
        contact = self.resume.contact
        values = []
        if contact.phone:
            values.append(f"Mobile No: {contact.phone}")
        if contact.email:
            values.append(f"Email Id: {contact.email}")
        values.extend(value for value in (contact.location, contact.linkedin, contact.github) if value)
        return values

    @property
    def projects(self):
        return self.resume.projects or [project for experience in self.resume.experience for project in experience.projects]

    @staticmethod
    def project_label(index: int) -> str:
        return f"Project {_roman(index)}"