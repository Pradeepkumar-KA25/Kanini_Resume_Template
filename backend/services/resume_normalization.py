from __future__ import annotations

import re

from models.resume import Experience, Project, ResumeData

_SUMMARY_HEAD_RE = re.compile(
    r"(?is)(?:^|\n)\s*(?:profile\s+summary|professional\s+summary|summary\s+of\s+experience|"
    r"professional\s+profile|career\s+summary|objective)\s*:?\s*(.+?)(?=\n\s*(?:technical\s+skills|skills|"
    r"work(?:ing)?\s+experience|employment\s+history|education|projects?)\s*:?(?:\n|$)|\Z)"
)
_ROLE_RE = re.compile(r"\b(?:engineer|developer|manager|analyst|architect|consultant|lead|senior|junior|associate|intern)\b", re.I)
_SKILL_NOISE_RE = re.compile(r"\b(?:company(?:\s+name)?|designation|position|duration|role|responsibilities?|project\s+[ivx]+|working\s+experience|employment|till\s+date|present|current)\b", re.I)
_PROJECT_ACTION_RE = re.compile(r"\b(?:developed|integrated|managed|improved|created|implemented|designed|streamline|enhance|workflow|application|api)\b", re.I)
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}")
_PHONE_RE = re.compile(r"(?:\+?\d{1,3}[\s\-.]?)?(?:\(?\d{3}\)?[\s\-.]?)?\d{3}[\s\-.]?\d{4}")


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        cleaned = str(value or "").strip()
        key = cleaned.casefold()
        if cleaned and key not in seen:
            seen.add(key)
            result.append(cleaned)
    return result


def normalise_resume(resume: ResumeData, raw_text: str = "") -> ResumeData:
    """Apply model-safe normalization while retaining optional parsed information."""
    skills: dict[str, list[str]] = {}
    for category, items in resume.skills.items():
        name = category.rstrip(":").strip() or "Technical Skills"
        target = next((key for key in skills if key.casefold() == name.casefold()), name)
        skills.setdefault(target, []).extend(item for item in items if not _skill_is_noise(item))
    resume.skills = {category: _unique(items) for category, items in skills.items() if _unique(items)}

    resume.summary = _clean_summary(resume.summary)
    if _summary_is_weak(resume.summary) and raw_text:
        resume.summary = _recover_summary(raw_text) or resume.summary
    resume.certifications = _unique(resume.certifications)
    resume.achievements = _unique(resume.achievements)

    for experience in resume.experience:
        _normalise_experience(experience)
        experience.responsibilities = _unique(experience.responsibilities)
        experience.company_name = experience.company_name or experience.company
        for project in experience.projects:
            _normalise_project(project)

    for project in resume.projects:
        _normalise_project(project)
    resume.experience = _merge_experience(resume.experience)
    if not resume.experience and raw_text:
        resume.experience = _recover_pdf_experience(raw_text)
    resume.projects = [project for project in resume.projects if not _project_is_noisy(project)]
    resume.education = [education for education in resume.education if not _PROJECT_ACTION_RE.search(education.institution) and len(education.institution.split()) <= 14]
    return resume


def _normalise_project(project: Project) -> None:
    project.technologies = _unique(project.technologies)
    project.responsibilities = _unique(project.responsibilities)


def _clean_summary(summary: str) -> str:
    lines = []
    for line in str(summary or "").replace("\r", "\n").split("\n"):
        line = re.sub(r"^\s*(?:[\u2022\u2023\u25e6\u2043\u2219\-*]+|\d+[.)])\s*", "", line).strip()
        if line and not re.search(r"\b(?:linkedin|github|@)\b", line, re.I):
            lines.append(line)
    return "\n".join(_unique(lines))


def _summary_is_weak(summary: str) -> bool:
    return not summary or len(summary.split()) <= 4


def _recover_summary(raw_text: str) -> str:
    match = _SUMMARY_HEAD_RE.search(str(raw_text or ""))
    return _clean_summary(match.group(1)) if match else ""


def _normalise_experience(experience: Experience) -> None:
    experience.company = re.sub(r"^(?:company(?:\s+name)?|client|employer|organization|designation|role|title)\s*[:\-]\s*", "", experience.company, flags=re.I).strip()
    experience.title = re.sub(r"^(?:designation|position|role|title)\s*[:\-]\s*", "", experience.title, flags=re.I).strip()
    if _ROLE_RE.search(experience.company) and not _ROLE_RE.search(experience.title):
        experience.company, experience.title = experience.title, experience.company


def _merge_experience(experiences: list[Experience]) -> list[Experience]:
    merged: list[Experience] = []
    for experience in experiences:
        if not any((experience.company, experience.title, experience.dates, experience.responsibilities)):
            continue
        previous = merged[-1] if merged else None
        if previous and previous.company and not previous.title and experience.title and not experience.company:
            previous.title = experience.title
            previous.dates = previous.dates or experience.dates
            previous.responsibilities = _unique(previous.responsibilities + experience.responsibilities)
        else:
            merged.append(experience)
    return merged


def _recover_pdf_experience(raw_text: str) -> list[Experience]:
    lines = [line.strip() for line in str(raw_text or "").splitlines()]
    try:
        heading_index = next(index for index, line in enumerate(lines) if re.match(r"^Working Experience:?$", line, re.I))
    except StopIteration:
        return []
    values = [re.sub(r"^:\s*", "", line).strip() for line in lines[:heading_index] if re.match(r"^:\s*.+$", line)]
    if len(values) < 3:
        return []
    company = next((value for value in values if not _ROLE_RE.search(value) and not re.search(r"\d{4}", value)), "")
    title = next((value for value in values if _ROLE_RE.search(value)), "")
    dates = next((value for value in values if re.search(r"\d{4}", value)), "")
    return [Experience(company=company, company_name=company, title=title, dates=dates)] if company or title or dates else []


def _project_is_noisy(project: Project) -> bool:
    if not any((project.name, project.client, project.role, project.description, project.technologies, project.responsibilities)):
        return True
    return "," in project.name and len(project.client.split()) == 1 and not project.technologies and len(project.description) > 180


def _skill_is_noise(value: str) -> bool:
    text = str(value or "").strip()
    if not text or _SKILL_NOISE_RE.search(text):
        return True
    if len(text.split()) > 6:
        return True
    return bool(_ROLE_RE.search(text) and len(text.split()) >= 2)


def validate_resume(resume: ResumeData, raw_text: str = "") -> tuple[bool, str]:
    """Validate only structural requirements enforced by the current upload contract."""
    if raw_text and len(re.sub(r"\s+", "", raw_text)) < 40:
        return False, "Could not extract readable text from the file (too little content or unreadable format)."
    if raw_text and not resume.contact.email:
        match = _EMAIL_RE.search(raw_text)
        if match:
            resume.contact.email = match.group(0)
    if raw_text and not resume.contact.phone:
        match = _PHONE_RE.search(re.sub(r"\d{4}[-\u2013]\d{4}", "", raw_text))
        if match:
            resume.contact.phone = match.group(0).strip()
    if not resume.contact.email and not resume.contact.phone:
        return False, "Could not find an email address or phone number in the resume."
    if not resume.contact.email:
        return False, "Could not find an email address in the resume."
    if not resume.contact.phone:
        return False, "Could not find a phone number in the resume."
    return True, ""