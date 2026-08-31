"""
Vector database layer for the Kanini Resume Builder.

Ingestion strategy:
    - Parse once upstream into structured resume JSON.
    - Expand into one vector row per project.
    - Duplicate common sections into every row:
            profile_summary, technical_skills, working_experience,
            project_summary, education_qualification.
    - Build one embedding document per row (common sections + one project).

ChromaDB runs fully embedded (no separate server) and uses the bundled
all-MiniLM-L6-v2 ONNX model for embeddings, so no API key is required.
"""

from __future__ import annotations

import os
import json
import datetime
import re
from typing import Dict, List, Optional, Any

# Store the database next to this file so it is stable regardless of CWD.
_DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chroma_db")
_COLLECTION_NAME = "resumes"
_SECTOR_COLLECTION_NAME = "company_sector_index"
_SECTION_COLLECTION_NAME = "resume_section_index"
_SECTOR_LABEL_COLLECTION_NAME = "sector_label_index"

# Module-level singletons (initialised lazily on first use).
_client = None
_collection = None
_sector_collection = None
_section_collection = None
_sector_label_collection = None


def _get_collection():
    """Return the shared ChromaDB collection, creating it on first access."""
    global _client, _collection
    if _collection is not None:
        return _collection

    import chromadb
    from chromadb.utils import embedding_functions

    os.makedirs(_DB_DIR, exist_ok=True)
    _client = chromadb.PersistentClient(path=_DB_DIR)
    embed_fn = embedding_functions.DefaultEmbeddingFunction()
    _collection = _client.get_or_create_collection(
        name=_COLLECTION_NAME,
        embedding_function=embed_fn,
        metadata={"hnsw:space": "cosine"},
    )
    return _collection


def _get_sector_collection():
    """Return the company-sector index collection, creating it on first use."""
    global _client, _sector_collection
    if _sector_collection is not None:
        return _sector_collection

    if _client is None:
        _ = _get_collection()

    from chromadb.utils import embedding_functions

    embed_fn = embedding_functions.DefaultEmbeddingFunction()
    _sector_collection = _client.get_or_create_collection(
        name=_SECTOR_COLLECTION_NAME,
        embedding_function=embed_fn,
        metadata={"hnsw:space": "cosine"},
    )
    return _sector_collection


def _get_section_collection():
    """Return the structured section-row index collection, creating it on first use."""
    global _client, _section_collection
    if _section_collection is not None:
        return _section_collection

    if _client is None:
        _ = _get_collection()

    from chromadb.utils import embedding_functions

    embed_fn = embedding_functions.DefaultEmbeddingFunction()
    _section_collection = _client.get_or_create_collection(
        name=_SECTION_COLLECTION_NAME,
        embedding_function=embed_fn,
        metadata={"hnsw:space": "cosine"},
    )
    return _section_collection


def _get_sector_label_collection():
    """Return the sector label catalog collection, creating it on first use."""
    global _client, _sector_label_collection
    if _sector_label_collection is not None:
        return _sector_label_collection

    if _client is None:
        _ = _get_collection()

    from chromadb.utils import embedding_functions

    embed_fn = embedding_functions.DefaultEmbeddingFunction()
    _sector_label_collection = _client.get_or_create_collection(
        name=_SECTOR_LABEL_COLLECTION_NAME,
        embedding_function=embed_fn,
        metadata={"hnsw:space": "cosine"},
    )
    return _sector_label_collection


# ─── Section extraction & row building ───────────────────────────────────────

def _to_text(value: Any) -> str:
    return str(value or "").strip()


def _join_non_empty(lines: List[str], sep: str = "\n") -> str:
    return sep.join([ln for ln in lines if ln and ln.strip()]).strip()


def _skills_text(skills: Any) -> str:
    if not isinstance(skills, dict):
        return ""
    lines: List[str] = []
    for category, items in skills.items():
        cat = _to_text(category)
        if isinstance(items, list):
            vals = [_to_text(item) for item in items if _to_text(item)]
            if vals:
                lines.append(f"{cat}: {', '.join(vals)}" if cat else ", ".join(vals))
        else:
            val = _to_text(items)
            if val:
                lines.append(f"{cat}: {val}" if cat else val)
    return _join_non_empty(lines)


def _experience_text(experience: Any) -> str:
    if not isinstance(experience, list):
        return ""
    chunks: List[str] = []
    for exp in experience:
        if not isinstance(exp, dict):
            continue
        title = _to_text(exp.get("title"))
        company = _to_text(exp.get("company"))
        location = _to_text(exp.get("location"))
        dates = _to_text(exp.get("dates"))
        header_parts = [p for p in [title, company, location, dates] if p]
        header = " | ".join(header_parts)

        resp_lines: List[str] = []
        responsibilities = exp.get("responsibilities")
        if isinstance(responsibilities, list):
            for item in responsibilities:
                txt = _to_text(item)
                if txt:
                    resp_lines.append(f"- {txt}")

        chunks.append(_join_non_empty([header, _join_non_empty(resp_lines)]))
    return _join_non_empty(chunks, sep="\n\n")


def _education_text(education: Any) -> str:
    if not isinstance(education, list):
        return ""
    lines: List[str] = []
    for edu in education:
        if not isinstance(edu, dict):
            continue
        degree = _to_text(edu.get("degree"))
        institution = _to_text(edu.get("institution"))
        year = _to_text(edu.get("year"))
        gpa = _to_text(edu.get("gpa"))
        parts = [p for p in [degree, institution, year, gpa] if p]
        if parts:
            lines.append(" | ".join(parts))
    return _join_non_empty(lines)


def _normalise_sector_values(sector_text: str) -> List[str]:
    raw = str(sector_text or "").strip()
    if not raw:
        return []
    parts = [p.strip() for p in re.split(r"\s*/\s*", raw) if p.strip()]
    return parts or [raw]


def _experience_company_names(experience: Any) -> str:
    if not isinstance(experience, list):
        return ""
    names: List[str] = []
    for exp in experience:
        if not isinstance(exp, dict):
            continue
        name = _to_text(exp.get("company_name") or exp.get("company"))
        if name:
            names.append(name)
    return _join_non_empty(_unique(names), sep="\n") if names else ""


def _experience_company_sectors(experience: Any) -> str:
    if not isinstance(experience, list):
        return ""
    sectors: List[str] = []
    for exp in experience:
        if not isinstance(exp, dict):
            continue
        raw_sector = _to_text(exp.get("company_sector"))
        if not raw_sector:
            continue
        sectors.extend(_normalise_sector_values(raw_sector))
    cleaned = [s for s in sectors if s]
    return _join_non_empty(_unique(cleaned), sep="\n") if cleaned else ""


def _unique(items: List[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for item in items:
        key = str(item).strip().casefold()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(str(item).strip())
    return out


def _company_key(company_name: str) -> str:
    import re as _re
    return _re.sub(r"[^a-z0-9]+", "", str(company_name or "").casefold())


def _sector_row_id(company_name: str) -> str:
    return f"company_sector::{_company_key(company_name)}"


def _sector_label_key(label: str) -> str:
    import re as _re
    return _re.sub(r"[^a-z0-9]+", "", str(label or "").casefold())


def _sector_label_row_id(label: str) -> str:
    return f"sector_label::{_sector_label_key(label)}"


def _split_sector_tokens(raw_label: str) -> List[str]:
    """Split labels on '/' and return cleaned unique tokens.

    Example:
        "A / B / C" -> ["A", "B", "C"]
    """
    raw = _to_text(raw_label)
    if not raw:
        return []
    tokens = [part.strip() for part in re.split(r"\s*/\s*", raw) if part and part.strip()]
    return _unique(tokens)


def _project_text(project: Any) -> str:
    if not isinstance(project, dict):
        return ""
    name = _to_text(project.get("name"))
    description = _to_text(project.get("description"))
    techs = project.get("technologies") if isinstance(project.get("technologies"), list) else []
    responsibilities = project.get("responsibilities") if isinstance(project.get("responsibilities"), list) else []

    tech_line = ""
    tech_vals = [_to_text(t) for t in techs if _to_text(t)]
    if tech_vals:
        tech_line = "Technologies: " + ", ".join(tech_vals)

    resp_lines = [f"- {_to_text(r)}" for r in responsibilities if _to_text(r)]
    return _join_non_empty([name, description, tech_line, _join_non_empty(resp_lines)])


def _extract_sections(resume_data: Dict[str, Any]) -> Dict[str, Any]:
    projects_raw = resume_data.get("projects") if isinstance(resume_data.get("projects"), list) else []
    project_summaries = [_project_text(project) for project in projects_raw]
    project_summaries = [proj for proj in project_summaries if proj]
    if not project_summaries:
        project_summaries = [""]

    return {
        "profile_summary": _to_text(resume_data.get("summary")),
        "technical_skills": _skills_text(resume_data.get("skills")),
        "working_experience": _experience_text(resume_data.get("experience")),
        "company_names": _experience_company_names(resume_data.get("experience")),
        "company_sectors": _experience_company_sectors(resume_data.get("experience")),
        "education_qualification": _education_text(resume_data.get("education")),
        "project_summaries": project_summaries,
    }


def _build_embedding_document(row: Dict[str, str], name: str = "") -> str:
    sections: List[str] = []
    if name:
        sections.append(f"Candidate: {name}")
    sections.append(f"Profile Summary:\n{row.get('profile_summary', '')}")
    sections.append(f"Technical Skills:\n{row.get('technical_skills', '')}")
    sections.append(f"Working Experience:\n{row.get('working_experience', '')}")
    sections.append(f"Company Names:\n{row.get('company_names', '')}")
    sections.append(f"Company Sectors:\n{row.get('company_sectors', '')}")
    sections.append(f"Project Summary:\n{row.get('project_summary', '')}")
    sections.append(f"Education Qualification:\n{row.get('education_qualification', '')}")
    return _join_non_empty(sections, sep="\n\n") or "(empty resume row)"


def _build_project_rows(
    resume_id: str,
    resume_data: Dict[str, Any],
    filename: str,
    created_at: str,
) -> List[Dict[str, Any]]:
    sections = _extract_sections(resume_data)
    contact = resume_data.get("contact") if isinstance(resume_data.get("contact"), dict) else {}
    name = _to_text(contact.get("name")) or "Unknown"
    email = _to_text(contact.get("email"))

    rows: List[Dict[str, Any]] = []
    projects = sections["project_summaries"]
    total_projects = len(projects)

    common = {
        "profile_summary": sections["profile_summary"],
        "technical_skills": sections["technical_skills"],
        "working_experience": sections["working_experience"],
        "company_names": sections["company_names"],
        "company_sectors": sections["company_sectors"],
        "education_qualification": sections["education_qualification"],
    }

    for idx, project_summary in enumerate(projects, start=1):
        row_id = f"{resume_id}::project::{idx}"
        row_payload = {
            **common,
            "project_summary": project_summary,
        }
        metadata = {
            "resume_id": resume_id,
            "row_id": row_id,
            "project_index": idx,
            "project_count": total_projects,
            "name": name,
            "email": email,
            "filename": str(filename or ""),
            "created_at": created_at,
            "profile_summary": row_payload["profile_summary"],
            "technical_skills": row_payload["technical_skills"],
            "working_experience": row_payload["working_experience"],
            "company_names": row_payload["company_names"],
            "company_sectors": row_payload["company_sectors"],
            "project_summary": row_payload["project_summary"],
            "education_qualification": row_payload["education_qualification"],
            # Keep full structured payload for backwards-compatible retrieval.
            "resume_json": json.dumps(resume_data, ensure_ascii=False),
        }
        rows.append(
            {
                "id": row_id,
                "document": _build_embedding_document(row_payload, name=name),
                "metadata": metadata,
            }
        )

    return rows


def _build_section_rows(
    resume_id: str,
    resume_data: Dict[str, Any],
    filename: str,
    created_at: str,
) -> List[Dict[str, Any]]:
    """Build one row per logical section and one row per work-experience entry."""
    contact = resume_data.get("contact") if isinstance(resume_data.get("contact"), dict) else {}
    name = _to_text(contact.get("name")) or "Unknown"
    email = _to_text(contact.get("email"))

    rows: List[Dict[str, Any]] = []

    def add_row(
        section_name: str,
        section_index: int,
        content: str,
        extra_meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        section_id = f"{resume_id}::section::{section_name}::{section_index}"
        metadata: Dict[str, Any] = {
            "resume_id": resume_id,
            "row_id": section_id,
            "section_name": section_name,
            "section_index": section_index,
            "name": name,
            "email": email,
            "filename": str(filename or ""),
            "created_at": created_at,
            "content": _to_text(content),
        }
        if extra_meta:
            metadata.update(extra_meta)

        doc = (
            f"Candidate: {name}\n"
            f"Section: {section_name}\n"
            f"Index: {section_index}\n"
            f"Content:\n{_to_text(content)}"
        )
        rows.append({"id": section_id, "document": doc, "metadata": metadata})

    # Profile summary row.
    add_row("profile_summary", 1, _to_text(resume_data.get("summary")))

    # Technical skills row + raw JSON payload to preserve category structure.
    skills_obj = resume_data.get("skills") if isinstance(resume_data.get("skills"), dict) else {}
    add_row(
        "technical_skills",
        1,
        _skills_text(skills_obj),
        {
            "skills_json": json.dumps(skills_obj, ensure_ascii=False),
        },
    )

    # Working experience rows (one row per entry with dedicated columns in metadata).
    experience = resume_data.get("experience") if isinstance(resume_data.get("experience"), list) else []
    if experience:
        for idx, exp in enumerate(experience, start=1):
            if not isinstance(exp, dict):
                continue
            company_name = _to_text(exp.get("company_name") or exp.get("company"))
            designation = _to_text(exp.get("title"))
            duration = _to_text(exp.get("dates"))
            location = _to_text(exp.get("location"))
            company_sector = _to_text(exp.get("company_sector"))
            responsibilities = exp.get("responsibilities") if isinstance(exp.get("responsibilities"), list) else []
            resp_json = json.dumps([_to_text(r) for r in responsibilities if _to_text(r)], ensure_ascii=False)

            content = _join_non_empty(
                [
                    f"Company Name: {company_name}",
                    f"Designation: {designation}",
                    f"Duration: {duration}",
                    f"Location: {location}",
                    f"Company Sector: {company_sector}",
                ]
            )
            add_row(
                "working_experience",
                idx,
                content,
                {
                    "company_name": company_name,
                    "designation": designation,
                    "duration": duration,
                    "location": location,
                    "company_sector": company_sector,
                    "responsibilities_json": resp_json,
                },
            )
    else:
        add_row("working_experience", 1, "")

    # Education rows.
    education = resume_data.get("education") if isinstance(resume_data.get("education"), list) else []
    if education:
        for idx, edu in enumerate(education, start=1):
            if not isinstance(edu, dict):
                continue
            degree = _to_text(edu.get("degree"))
            institution = _to_text(edu.get("institution"))
            year = _to_text(edu.get("year"))
            gpa = _to_text(edu.get("gpa"))
            content = _join_non_empty(
                [
                    f"Degree: {degree}",
                    f"Institution: {institution}",
                    f"Year: {year}",
                    f"GPA: {gpa}",
                ]
            )
            add_row(
                "education_qualification",
                idx,
                content,
                {
                    "degree": degree,
                    "institution": institution,
                    "year": year,
                    "gpa": gpa,
                },
            )
    else:
        add_row("education_qualification", 1, "")

    # Project rows.
    projects = resume_data.get("projects") if isinstance(resume_data.get("projects"), list) else []
    if projects:
        for idx, proj in enumerate(projects, start=1):
            if not isinstance(proj, dict):
                continue
            pname = _to_text(proj.get("name"))
            pdesc = _to_text(proj.get("description"))
            techs = proj.get("technologies") if isinstance(proj.get("technologies"), list) else []
            resp = proj.get("responsibilities") if isinstance(proj.get("responsibilities"), list) else []
            techs_json = json.dumps([_to_text(t) for t in techs if _to_text(t)], ensure_ascii=False)
            resp_json = json.dumps([_to_text(r) for r in resp if _to_text(r)], ensure_ascii=False)
            content = _join_non_empty(
                [
                    f"Project: {pname}",
                    f"Description: {pdesc}",
                    f"Technologies: {', '.join([_to_text(t) for t in techs if _to_text(t)])}",
                ]
            )
            add_row(
                "project_summary",
                idx,
                content,
                {
                    "project_name": pname,
                    "project_description": pdesc,
                    "technologies_json": techs_json,
                    "responsibilities_json": resp_json,
                },
            )
    else:
        add_row("project_summary", 1, "")

    # Certifications and achievements as individual rows for retrieval fidelity.
    certs = resume_data.get("certifications") if isinstance(resume_data.get("certifications"), list) else []
    if certs:
        for idx, cert in enumerate(certs, start=1):
            add_row("certifications", idx, _to_text(cert))

    achievements = resume_data.get("achievements") if isinstance(resume_data.get("achievements"), list) else []
    if achievements:
        for idx, ach in enumerate(achievements, start=1):
            add_row("achievements", idx, _to_text(ach))

    return rows


def _rebuild_resume_from_section_rows(section_metas: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Reconstruct structured resume JSON from section-wise rows."""
    if not section_metas:
        return None

    metas = [m for m in section_metas if isinstance(m, dict)]
    if not metas:
        return None

    def _idx(meta: Dict[str, Any]) -> int:
        try:
            return int(meta.get("section_index") or 0)
        except Exception:
            return 0

    first = metas[0]
    rebuilt: Dict[str, Any] = {
        "contact": {
            "name": _to_text(first.get("name")),
            "email": _to_text(first.get("email")),
            "phone": "",
            "location": "",
            "linkedin": "",
            "github": "",
        },
        "summary": "",
        "skills": {},
        "experience": [],
        "education": [],
        "certifications": [],
        "projects": [],
        "achievements": [],
    }

    by_section: Dict[str, List[Dict[str, Any]]] = {}
    for meta in metas:
        key = _to_text(meta.get("section_name")).lower()
        by_section.setdefault(key, []).append(meta)

    # Summary
    summary_rows = sorted(by_section.get("profile_summary", []), key=_idx)
    if summary_rows:
        rebuilt["summary"] = _to_text(summary_rows[0].get("content"))

    # Skills
    skill_rows = sorted(by_section.get("technical_skills", []), key=_idx)
    if skill_rows:
        skills_json = _to_text(skill_rows[0].get("skills_json"))
        if skills_json:
            try:
                parsed = json.loads(skills_json)
                if isinstance(parsed, dict):
                    rebuilt["skills"] = parsed
            except Exception:
                rebuilt["skills"] = {}

    # Experience
    exp_rows = sorted(by_section.get("working_experience", []), key=_idx)
    for row in exp_rows:
        company_name = _to_text(row.get("company_name"))
        designation = _to_text(row.get("designation"))
        duration = _to_text(row.get("duration"))
        location = _to_text(row.get("location"))
        company_sector = _to_text(row.get("company_sector"))
        responsibilities_json = _to_text(row.get("responsibilities_json"))
        responsibilities: List[str] = []
        if responsibilities_json:
            try:
                parsed = json.loads(responsibilities_json)
                if isinstance(parsed, list):
                    responsibilities = [_to_text(x) for x in parsed if _to_text(x)]
            except Exception:
                responsibilities = []

        if company_name or designation or duration or location or company_sector or responsibilities:
            rebuilt["experience"].append(
                {
                    "company": company_name,
                    "company_name": company_name,
                    "company_sector": company_sector,
                    "title": designation,
                    "dates": duration,
                    "location": location,
                    "responsibilities": responsibilities,
                }
            )

    # Education
    edu_rows = sorted(by_section.get("education_qualification", []), key=_idx)
    for row in edu_rows:
        degree = _to_text(row.get("degree"))
        institution = _to_text(row.get("institution"))
        year = _to_text(row.get("year"))
        gpa = _to_text(row.get("gpa"))
        if degree or institution or year or gpa:
            rebuilt["education"].append(
                {
                    "degree": degree,
                    "institution": institution,
                    "year": year,
                    "gpa": gpa,
                }
            )

    # Projects
    proj_rows = sorted(by_section.get("project_summary", []), key=_idx)
    for row in proj_rows:
        pname = _to_text(row.get("project_name"))
        pdesc = _to_text(row.get("project_description"))
        tech_json = _to_text(row.get("technologies_json"))
        resp_json = _to_text(row.get("responsibilities_json"))
        techs: List[str] = []
        if tech_json:
            try:
                parsed = json.loads(tech_json)
                if isinstance(parsed, list):
                    techs = [_to_text(x) for x in parsed if _to_text(x)]
            except Exception:
                techs = []
        responsibilities: List[str] = []
        if resp_json:
            try:
                parsed = json.loads(resp_json)
                if isinstance(parsed, list):
                    responsibilities = [_to_text(x) for x in parsed if _to_text(x)]
            except Exception:
                responsibilities = []

        if pname or pdesc or techs or responsibilities:
            rebuilt["projects"].append(
                {
                    "name": pname,
                    "description": pdesc,
                    "technologies": techs,
                    "responsibilities": responsibilities,
                }
            )

    # Certifications and achievements.
    cert_rows = sorted(by_section.get("certifications", []), key=_idx)
    rebuilt["certifications"] = [_to_text(r.get("content")) for r in cert_rows if _to_text(r.get("content"))]

    ach_rows = sorted(by_section.get("achievements", []), key=_idx)
    rebuilt["achievements"] = [_to_text(r.get("content")) for r in ach_rows if _to_text(r.get("content"))]

    return rebuilt


def _summary_for(resume_id: str, meta: Dict[str, Any]) -> Dict[str, Any]:
    """Lightweight record for list/search responses (no full JSON payload)."""
    return {
        "id": meta.get("resume_id") or resume_id,
        "name": meta.get("name") or "Unknown",
        "email": meta.get("email") or "",
        "filename": meta.get("filename") or "",
        "created_at": meta.get("created_at") or "",
    }


def _load_resume_json_from_meta(meta: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    raw = (meta or {}).get("resume_json")
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None


# ─── Public API ─────────────────────────────────────────────────────────────────

def store_resume(resume_id: str, resume_data: Dict[str, Any], filename: str = "") -> None:
    """Insert or update a resume in the vector database.

    One row is stored per project. Common sections are duplicated in each row.
    """
    collection = _get_collection()
    section_collection = _get_section_collection()

    # Replace all existing rows for this resume id (project-wise rows).
    collection.delete(where={"resume_id": resume_id})
    section_collection.delete(where={"resume_id": resume_id})

    created_at = datetime.datetime.now().isoformat(timespec="seconds")
    rows = _build_project_rows(resume_id, resume_data, filename, created_at)

    ids = [row["id"] for row in rows]
    docs = [row["document"] for row in rows]
    metas = [row["metadata"] for row in rows]
    collection.upsert(
        ids=ids,
        documents=docs,
        metadatas=metas,
    )

    # Store section-wise rows to preserve strict template mapping by section.
    section_rows = _build_section_rows(resume_id, resume_data, filename, created_at)
    if section_rows:
        section_collection.upsert(
            ids=[row["id"] for row in section_rows],
            documents=[row["document"] for row in section_rows],
            metadatas=[row["metadata"] for row in section_rows],
        )

    # Keep a compact company->sector index for future enrichments.
    experience = resume_data.get("experience") if isinstance(resume_data, dict) else []
    if isinstance(experience, list):
        for exp in experience:
            if not isinstance(exp, dict):
                continue
            company_name = _to_text(exp.get("company_name") or exp.get("company"))
            company_sector = _to_text(exp.get("company_sector"))
            if company_name and company_sector and company_sector.casefold() != "industry not determined":
                upsert_company_sector(company_name, company_sector, source="resume", resume_id=resume_id)


def upsert_company_sector(company_name: str, company_sector: str, source: str = "system", resume_id: str = "") -> None:
    """Insert or update a company-sector row in the dedicated sector index."""
    company = _to_text(company_name)
    sector = _to_text(company_sector)
    if not company or not sector:
        return
    if sector.casefold() == "industry not determined":
        return

    collection = _get_sector_collection()
    rid = _sector_row_id(company)
    now = datetime.datetime.now().isoformat(timespec="seconds")
    meta = {
        "company_name": company,
        "company_key": _company_key(company),
        "company_sector": sector,
        "source": _to_text(source) or "system",
        "resume_id": _to_text(resume_id),
        "updated_at": now,
    }
    doc = f"Company: {company}\nSector: {sector}"
    collection.upsert(ids=[rid], documents=[doc], metadatas=[meta])


def upsert_sector_label(label: str, source: str = "seed", parent_label: str = "") -> bool:
    """Insert one sector label token into sector catalog; skip if it exists.

    Returns:
        True if inserted, False if skipped.
    """
    sector_label = _to_text(label)
    if not sector_label:
        return False

    collection = _get_sector_label_collection()
    rid = _sector_label_row_id(sector_label)

    existing = collection.get(ids=[rid], include=["metadatas"])
    metas = existing.get("metadatas") or []
    if metas:
        return False

    now = datetime.datetime.now().isoformat(timespec="seconds")
    meta = {
        "sector_label": sector_label,
        "sector_key": _sector_label_key(sector_label),
        "source": _to_text(source) or "seed",
        "parent_label": _to_text(parent_label),
        "created_at": now,
    }
    doc = f"Sector Label: {sector_label}"
    collection.upsert(ids=[rid], documents=[doc], metadatas=[meta])
    return True


def seed_sector_labels(labels: List[str], source: str = "seed") -> Dict[str, int]:
    """Seed sector catalog from a list with slash-splitting and dedupe.

    Behavior:
        - Splits every input by '/'.
        - Stores each token as a separate catalog row.
        - Skips duplicates (existing rows are not duplicated).
    """
    inserted = 0
    skipped = 0

    seen_in_batch = set()

    for raw in labels or []:
        parent = _to_text(raw)
        tokens = _split_sector_tokens(parent)
        for token in tokens:
            key = _sector_label_key(token)
            if not key or key in seen_in_batch:
                skipped += 1
                continue
            seen_in_batch.add(key)
            if upsert_sector_label(token, source=source, parent_label=parent):
                inserted += 1
            else:
                skipped += 1

    return {"inserted": inserted, "skipped": skipped, "total_tokens": inserted + skipped}


def get_company_sector(company_name: str) -> str:
    """Return sector for a company if present in sector index or resume metadata."""
    company = _to_text(company_name)
    if not company:
        return ""

    collection = _get_sector_collection()
    rid = _sector_row_id(company)
    row = collection.get(ids=[rid], include=["metadatas"])
    metas = row.get("metadatas") or []
    if metas and isinstance(metas[0], dict):
        sector = _to_text(metas[0].get("company_sector"))
        if sector:
            return sector
    return ""


def get_resume(resume_id: str) -> Optional[Dict[str, Any]]:
    """Return the full structured resume_data for an id, or None if absent."""
    collection = _get_collection()

    # New schema: one or more rows where metadata.resume_id == resume_id.
    grouped = collection.get(where={"resume_id": resume_id}, include=["metadatas"])
    grouped_metas = grouped.get("metadatas") or []
    if grouped_metas:
        loaded = _load_resume_json_from_meta(grouped_metas[0] or {})
        if loaded is not None:
            return loaded

    # Fallback: rebuild from section-wise rows when full JSON payload is absent.
    section_collection = _get_section_collection()
    section_rows = section_collection.get(where={"resume_id": resume_id}, include=["metadatas"])
    section_metas = section_rows.get("metadatas") or []
    rebuilt = _rebuild_resume_from_section_rows(section_metas)
    if rebuilt is not None:
        return rebuilt

    # Backward compatibility: legacy one-document-per-resume layout.
    res = collection.get(ids=[resume_id], include=["metadatas"])
    metas = res.get("metadatas") or []
    if not metas:
        return None
    return _load_resume_json_from_meta(metas[0] or {})


def list_resumes() -> List[Dict[str, Any]]:
    """Return one summary per resume, newest first."""
    collection = _get_collection()
    res = collection.get(include=["metadatas"])
    ids = res.get("ids") or []
    metas = res.get("metadatas") or []

    deduped: Dict[str, Dict[str, Any]] = {}
    for rid, meta in zip(ids, metas):
        item = _summary_for(rid, meta or {})
        base_id = item["id"]
        existing = deduped.get(base_id)
        if not existing or item.get("created_at", "") > existing.get("created_at", ""):
            deduped[base_id] = item

    out = list(deduped.values())
    out.sort(key=lambda r: r.get("created_at", ""), reverse=True)
    return out


def search_resumes(query: str, n_results: int = 5) -> List[Dict[str, Any]]:
    """Semantic search over stored rows. Returns best match per resume + score."""
    collection = _get_collection()
    if collection.count() == 0 or not query.strip():
        return []
    n = max(1, min(n_results, collection.count()))
    res = collection.query(query_texts=[query], n_results=n, include=["metadatas", "distances"])
    ids = (res.get("ids") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    dists = (res.get("distances") or [[]])[0]
    best_by_resume: Dict[str, Dict[str, Any]] = {}
    for rid, meta, dist in zip(ids, metas, dists):
        summary = _summary_for(rid, meta or {})
        # Cosine distance → similarity score in [0, 1] (higher is better).
        summary["score"] = round(max(0.0, 1.0 - float(dist)), 4)
        summary["project_summary"] = str((meta or {}).get("project_summary") or "")

        resume_key = summary["id"]
        existing = best_by_resume.get(resume_key)
        if not existing or summary["score"] > existing.get("score", 0.0):
            best_by_resume[resume_key] = summary

    results = list(best_by_resume.values())
    results.sort(key=lambda r: r.get("score", 0.0), reverse=True)
    return results[:n_results]


def delete_resume(resume_id: str) -> None:
    """Remove a resume from the vector database."""
    collection = _get_collection()
    section_collection = _get_section_collection()
    # New schema rows
    collection.delete(where={"resume_id": resume_id})
    section_collection.delete(where={"resume_id": resume_id})
    # Legacy single-id row
    collection.delete(ids=[resume_id])


def count() -> int:
    """Total number of stored resumes."""
    return _get_collection().count()
