from __future__ import annotations

from dataclasses import dataclass

from models.resume import Project, ResumeData


@dataclass(frozen=True)
class Format2ViewModel:
    resume: ResumeData

    @property
    def name(self) -> str:
        return self.resume.contact.name or "CANDIDATE NAME"

    @property
    def projects(self) -> list[Project]:
        return self.resume.projects or [project for experience in self.resume.experience for project in experience.projects]

    @staticmethod
    def project_label(index: int) -> str:
        numerals = ("I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X")
        return f"Project – {numerals[index - 1] if index <= len(numerals) else index}"