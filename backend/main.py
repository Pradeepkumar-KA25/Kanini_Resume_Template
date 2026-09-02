"""
Kanini Resume Builder — FastAPI Backend
"""

import os
import sys
import uuid
import shutil
import tempfile
import re
import json
import logging
import hashlib
import copy
import asyncio
from pathlib import Path
from typing import Dict, Any, Tuple

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from resume_parser import parse_resume, parse_skill_set, extract_text
from template_generator import (
    generate_template1,
    generate_template_deloitte,
    generate_preview_html_template1,
    generate_preview_html_deloitte,
    convert_html_to_pdf,
    convert_to_pdf,
    _inject_logo_into_html,
)
import ai_parser
import vector_store
from services.resume_adapter import ResumeAdapter
from services.resume_normalization import normalise_resume, validate_resume
from services.template_generation_service import TemplateGenerationError, generate_template_spec
from services.template_validation_service import TemplateSpecValidationError, validate_template_spec
from services.user_template_store import UserTemplateValidationError, delete_user_template, describe_template_spec, load_user_template, save_user_template, update_user_template, validate_template_description, validate_template_name
from models.resume import ResumeData
from templates.registry import TemplateNotFoundError, TemplateRegistry
from renderers import RendererFactory
from renderers.base import LatexUnavailableError
from renderers.template_draft_renderer import render_template_draft_preview

app = FastAPI(title="Kanini Resume Builder API", version="1.0.0")
TEMPLATE_REGISTRY = TemplateRegistry.discover()
RENDERER_FACTORY = RendererFactory(TEMPLATE_REGISTRY)

logger = logging.getLogger("kanini.resume")
PDF_DEBUG_ENABLED = os.getenv("PDF_PARSE_DEBUG", "0").strip().lower() in {"1", "true", "yes", "on"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Session Storage ──────────────────────────────────────────────────────────
# Maps session_id → { "resume_data": {...}, "files": { "t1_docx": path, ... } }
SESSIONS: Dict[str, Dict[str, Any]] = {}
TEMP_DIR = Path(tempfile.gettempdir()) / "kanini_resume_builder"
TEMP_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATE_DRAFT_DIR = Path(__file__).resolve().parent / "template_drafts"
TEMPLATE_DRAFT_DIR.mkdir(parents=True, exist_ok=True)
USER_TEMPLATES_DIR = Path(__file__).resolve().parent / "user_templates"
USER_TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)


class RenderRequest(BaseModel):
    template_id: str
    output_format: str = "html"


class SaveTemplateDraftRequest(BaseModel):
    template_name: str
    description: str


class UpdateUserTemplateRequest(BaseModel):
    template_name: str
    description: str
    template_spec: dict[str, Any]


class SelectedTemplateRequest(BaseModel):
    template_id: str


def _configure_pdf_debug_logging() -> None:
    """Write PDF parse diagnostics to console and a local log file when enabled."""
    if not PDF_DEBUG_ENABLED:
        return

    logger.setLevel(logging.WARNING)
    logger.propagate = False

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    has_stream = any(isinstance(h, logging.StreamHandler) for h in logger.handlers)
    if not has_stream:
        sh = logging.StreamHandler()
        sh.setLevel(logging.WARNING)
        sh.setFormatter(formatter)
        logger.addHandler(sh)

    log_path = Path(__file__).resolve().parent / "pdf_parse_debug.log"
    has_file = any(
        isinstance(h, logging.FileHandler) and getattr(h, "baseFilename", "") == str(log_path)
        for h in logger.handlers
    )
    if not has_file:
        fh = logging.FileHandler(log_path, encoding="utf-8")
        fh.setLevel(logging.WARNING)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    logger.warning("[PDF DEBUG] enabled. log_file=%s", log_path)


_configure_pdf_debug_logging()

ALLOWED_EXTENSIONS = {"pdf", "docx", "doc"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
INVALID_RESUME_MSG = "Resume upload is invalid. Please upload a valid resume."

_SECTOR_RAW_LABELS = [
    "Software Product (SaaS)",
    "Platform as a Service (PaaS)",
    "Infrastructure as a Service (IaaS) / Cloud Providers",
    "Cloud Management & Orchestration",
    "Managed IT Services (MSP)",
    "IT Consulting / Professional Services",
    "System Integration",
    "Outsourcing / Offshoring / BPO / KPO",
    "Cybersecurity / InfoSec / Threat Intelligence",
    "Identity & Access Management (IAM) / PAM",
    "Compliance, Risk & Governance (GRC) / Security Ops (SecOps)",
    "Data Engineering / Data Platforms",
    "Business Intelligence & Analytics / BI",
    "Big Data / Data Lakes / Data Warehousing",
    "Artificial Intelligence / Machine Learning / MLOps",
    "Generative AI / LLM Platforms & Applications",
    "Computer Vision / NLP / Speech Tech",
    "Edge Computing / Fog Computing",
    "Internet of Things (IoT) / IIoT / Industrial IoT",
    "Embedded Systems & Firmware",
    "Networking / SD-WAN / Telecom Infrastructure",
    "5G / Wireless Communications",
    "DevOps / CI/CD / Site Reliability Engineering (SRE)",
    "Observability / Monitoring / APM / Log Management",
    "Database Management & Storage Systems",
    "High Performance Computing (HPC) / GPU Computing",
    "Quantum Computing & Quantum Software",
    "Cloud-native / Microservices / Containers / Kubernetes",
    "Application Development (Web & Mobile)",
    "Low-code / No-code / Citizen Development Platforms",
    "CRM / ERP / Enterprise Applications",
    "Digital Transformation / Enterprise Architecture",
    "E-commerce Platforms & Marketplaces",
    "Fintech / Payments / Digital Banking Tech",
    "Healthtech / Medtech / Digital Health Platforms",
    "Edtech / Learning Platforms & LMS",
    "Gaming / Game Engines / Esports Tech",
    "AR / VR / Mixed Reality / Metaverse Tech",
    "Blockchain / Web3 / DeFi / NFTs",
    "Robotics / Automation / RPA (Robotic Process Automation)",
    "Test & QA / Test Automation / QA Tools",
    "Digital Experience / UX / Frontend Frameworks",
    "Content Delivery Networks (CDN) & Streaming Tech",
    "Digital Marketing Tech / MarTech / AdTech",
    "Identity, Privacy & Data Protection Tech (privacy-enhancing tech)",
    "Green IT / Sustainability Tech / Energy-efficient IT",
    "IT Hardware / Semiconductors / Chip Design",
    "IT Research & Development / Labs / Innovation Hubs",
    "Legal Tech",
    "Government Tech (GovTech) / Public Sector IT",
    "Open Source Platforms & Foundations",
    "IT Training / Certification / Professional Education",
]


def _norm_sector_token(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(text or "").casefold())


def _build_sector_alias_map() -> tuple[list[str], dict[str, str]]:
    options: list[str] = []
    alias_to_primary: dict[str, str] = {}

    for raw in _SECTOR_RAW_LABELS:
        parts = [p.strip() for p in re.split(r"\s*/\s*", raw) if p.strip()]
        if not parts:
            continue
        primary = parts[0]
        for part in parts:
            key = _norm_sector_token(part)
            if key and key not in alias_to_primary:
                alias_to_primary[key] = primary
            if part not in options:
                options.append(part)
    return options, alias_to_primary


_SECTOR_OPTIONS, _SECTOR_ALIAS_TO_PRIMARY = _build_sector_alias_map()
_SECTOR_LOOKUP_CACHE: dict[str, str] = {}

_COMPANY_CLASSIFICATION_SECTORS = [
    "Technology",
    "Financial Services",
    "Healthcare",
    "Manufacturing",
    "Retail",
    "Energy",
    "Telecommunications",
    "Transportation",
    "Consumer Goods",
    "Real Estate",
    "Education",
    "Media",
    "Hospitality",
    "Agriculture",
    "Utilities",
    "Construction",
    "Pharmaceuticals",
    "Automotive",
    "Mining",
    "Aerospace & Defense",
    "Logistics",
    "Insurance",
    "Government",
    "Non-Profit",
    "Other",
    "Unknown",
]

_DATE_LIKE_COMPANY_RE = re.compile(
    r"^(?:to\s+)?\d{1,2}(?:st|nd|rd|th)?\s+"
    r"(?:jan|january|feb|february|mar|march|apr|april|may|jun|june|jul|july|aug|august|sep|september|oct|october|nov|november|dec|december)"
    r"\s+\d{4}$",
    re.IGNORECASE,
)


def _looks_like_valid_company_name(company_name: str) -> bool:
    company = str(company_name or "").strip()
    if not company:
        return False
    if _DATE_LIKE_COMPANY_RE.match(company):
        return False
    if len(company) < 2:
        return False
    if not re.search(r"[A-Za-z]", company):
        return False
    if company in {"-", ":", "\u2022", "\u25cf", "\uf0b7", "\u0b95"}:
        return False
    return True


def _normalise_sector_label(sector: str) -> str:
    raw = str(sector or "").strip()
    if not raw:
        return ""

    candidates = [p.strip() for p in re.split(r"\s*(?:/|,|\|)\s*", raw) if p.strip()]
    for cand in candidates:
        key = _norm_sector_token(cand)
        if key in _SECTOR_ALIAS_TO_PRIMARY:
            return _SECTOR_ALIAS_TO_PRIMARY[key]
    return candidates[0] if candidates else raw


def _sector_cache_key(company_name: str, context: str) -> str:
    payload = (str(company_name or "") + "\n" + str(context or "")).encode("utf-8", errors="ignore")
    return hashlib.sha1(payload).hexdigest()


def _truthy_env(name: str, default: str = "1") -> bool:
    raw = os.getenv(name, default)
    return str(raw or "").strip().lower() in {"1", "true", "yes", "on"}


def _normalise_openai_sector_answer(answer: str) -> str:
    text = str(answer or "").strip()
    if not text:
        return ""

    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text).strip()

    # If the model returned JSON, extract likely keys first.
    try:
        payload = json.loads(text)
        if isinstance(payload, dict):
            for key in ("sector", "company_sector", "label", "industry"):
                val = str(payload.get(key) or "").strip()
                if val:
                    return _normalise_sector_label(val)
    except Exception:
        pass

    return _normalise_sector_label(text)


def _parse_company_classification_response(answer: str) -> Dict[str, Any]:
    text = str(answer or "").strip()
    if not text:
        return {"sector": "Unknown", "industry": "Unknown", "confidence": 0.0}

    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text).strip()

    payload: Dict[str, Any] = {}
    try:
        raw = json.loads(text)
        if isinstance(raw, dict):
            payload = raw
    except Exception:
        return {"sector": "Unknown", "industry": "Unknown", "confidence": 0.0}

    sector = str(payload.get("sector") or "").strip()
    industry = str(payload.get("industry") or "").strip()

    try:
        confidence = float(payload.get("confidence", 0.0))
    except Exception:
        confidence = 0.0
    confidence = max(0.0, min(1.0, confidence))

    allowed = set(_COMPANY_CLASSIFICATION_SECTORS)
    if sector not in allowed:
        sector = "Unknown"

    if confidence < 0.35:
        sector = "Unknown"

    if not industry:
        industry = "Unknown"

    return {
        "sector": sector or "Unknown",
        "industry": industry,
        "confidence": confidence,
    }


def _sector_lookup_with_openai(company_name: str, context_text: str) -> str:
    import urllib.error
    import urllib.parse
    import urllib.request

    def _fetch_public_company_context(company: str) -> str:
        snippets: list[str] = []

        # DuckDuckGo Instant Answer API (public, no key).
        try:
            ddg_params = urllib.parse.urlencode(
                {
                    "q": f"{company} company industry sector",
                    "format": "json",
                    "no_html": "1",
                    "skip_disambig": "1",
                }
            )
            ddg_url = f"https://api.duckduckgo.com/?{ddg_params}"
            ddg_req = urllib.request.Request(ddg_url, headers={"User-Agent": "kanini-resume-builder/1.0"})
            with urllib.request.urlopen(ddg_req, timeout=10) as resp:
                ddg_payload = json.loads(resp.read().decode("utf-8", errors="ignore"))

            abstract = str(ddg_payload.get("AbstractText") or "").strip()
            heading = str(ddg_payload.get("Heading") or "").strip()
            if heading and abstract:
                snippets.append(f"{heading}: {abstract}")
            elif abstract:
                snippets.append(abstract)

            related = ddg_payload.get("RelatedTopics") or []
            for item in related[:8]:
                if not isinstance(item, dict):
                    continue
                text = str(item.get("Text") or "").strip()
                if text:
                    snippets.append(text)
                nested = item.get("Topics") or []
                for n_item in nested[:4]:
                    if isinstance(n_item, dict):
                        n_text = str(n_item.get("Text") or "").strip()
                        if n_text:
                            snippets.append(n_text)
        except Exception:
            pass

        # Wikipedia summary as an additional public source.
        try:
            wiki_params = urllib.parse.urlencode(
                {
                    "action": "opensearch",
                    "search": company,
                    "limit": "1",
                    "namespace": "0",
                    "format": "json",
                }
            )
            opensearch_url = f"https://en.wikipedia.org/w/api.php?{wiki_params}"
            opensearch_req = urllib.request.Request(opensearch_url, headers={"User-Agent": "kanini-resume-builder/1.0"})
            with urllib.request.urlopen(opensearch_req, timeout=10) as resp:
                payload = json.loads(resp.read().decode("utf-8", errors="ignore"))

            titles = payload[1] if isinstance(payload, list) and len(payload) > 1 else []
            if titles:
                title = str(titles[0]).strip()
                if title:
                    summary_url = (
                        "https://en.wikipedia.org/api/rest_v1/page/summary/"
                        + urllib.parse.quote(title, safe="")
                    )
                    summary_req = urllib.request.Request(summary_url, headers={"User-Agent": "kanini-resume-builder/1.0"})
                    with urllib.request.urlopen(summary_req, timeout=10) as resp:
                        summary_payload = json.loads(resp.read().decode("utf-8", errors="ignore"))
                    extract = str(summary_payload.get("extract") or "").strip()
                    if extract:
                        snippets.append(f"Wikipedia: {extract}")
        except Exception:
            pass

        if not snippets:
            return ""

        # Keep prompt size bounded and de-duplicate lines.
        deduped: list[str] = []
        seen = set()
        for line in snippets:
            key = line.casefold()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(line)
            if len(deduped) >= 12:
                break
        return "\n".join(deduped)[:3000]

    base_url = (os.getenv("OLLAMA_BASE_URL") or os.getenv("OLLAMA_HOST") or "").strip().rstrip("/")
    if not base_url:
        return ""

    company = str(company_name or "").strip()
    if not company:
        return ""

    context = str(context_text or "").strip()[:2000]
    web_context = _fetch_public_company_context(company)
    if not web_context:
        return ""

    cache_key = _sector_cache_key(company, context + "\n" + web_context)
    cached = _SECTOR_LOOKUP_CACHE.get(cache_key)
    if cached is not None:
        return cached

    model = (
        os.getenv("OLLAMA_SECTOR_MODEL")
        or os.getenv("OLLAMA_MODEL")
        or "llama3.1"
    ).strip() or "llama3.1"
    options_block = "\n".join(f"- {item}" for item in _COMPANY_CLASSIFICATION_SECTORS)
    prompt = (
        "Role:\n"
        "You are an expert business intelligence and company classification assistant.\n\n"
        "Objective:\n"
        "Given a company name, determine its primary business sector and industry based on publicly known information and general business knowledge.\n\n"
        "Instructions:\n"
        "1. Analyze the provided company name.\n"
        "2. Identify the company's primary business activity.\n"
        "3. Classify the company into exactly one business sector.\n"
        "4. Identify the most appropriate industry.\n"
        "5. If the company operates in multiple sectors, choose the sector that generates the majority of its revenue.\n"
        "6. If the company cannot be confidently identified, return Unknown.\n"
        "7. Never guess when confidence is low.\n"
        "8. Return ONLY valid JSON.\n"
        "9. Do not include explanations.\n"
        "10. Do not include markdown.\n"
        "11. Do not include additional text before or after the JSON.\n\n"
        "Use one of these sectors only:\n"
        f"{options_block}\n\n"
        "Output JSON Schema:\n"
        "{\n"
        "  \"company_name\": \"\",\n"
        "  \"sector\": \"\",\n"
        "  \"industry\": \"\",\n"
        "  \"confidence\": 0.00\n"
        "}\n\n"
        "Public web context:\n"
        f"{web_context}\n\n"
        "Resume context:\n"
        f"{context}\n\n"
        "Now classify the following company.\n\n"
        f"Input:\n{company}\n\n"
        "Return ONLY the JSON object."
    )

    payload = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0},
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        f"{base_url}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            body = json.loads(response.read().decode("utf-8", errors="ignore"))
    except urllib.error.URLError:
        return ""
    except Exception:
        return ""

    text_content = str(body.get("response") or "").strip()
    if not text_content:
        return ""

    classification = _parse_company_classification_response(text_content)
    sector = _normalise_sector_label(classification.get("sector") or "")
    if sector:
        _SECTOR_LOOKUP_CACHE[cache_key] = sector
    return sector


def _sector_lookup_fallback(company_name: str, context_text: str) -> str:
    company = str(company_name or "").casefold()

    strict_company_map = {
        "deloitte": "Technology",
        "kanini": "Technology",
        "exterro": "Technology",
        "infosys": "Technology",
        "tata consultancy services": "Technology",
        "tcs": "Technology",
        "wipro": "Technology",
        "accenture": "Technology",
    }

    for key, label in strict_company_map.items():
        if key in company:
            return _normalise_sector_label(label)
    return ""


def _enrich_experience_with_company_sectors(resume_data: Dict[str, Any], raw_text: str = "") -> None:
    exps = resume_data.get("experience")
    if not isinstance(exps, list):
        return

    context_chunks = [
        str(resume_data.get("summary") or ""),
        json.dumps(resume_data.get("skills") or {}, ensure_ascii=False),
        str(raw_text or ""),
    ]
    context_text = "\n".join([chunk for chunk in context_chunks if chunk]).strip()[:3500]

    for exp in exps:
        if not isinstance(exp, dict):
            continue
        company_name = str(exp.get("company") or "").strip()
        if not company_name:
            continue

        if not _looks_like_valid_company_name(company_name):
            exp["company_name"] = company_name
            exp["company_sector"] = "Industry Not Determined"
            continue

        exp["company_name"] = company_name

        # Priority 1: previously stored sector mapping in vector DB.
        db_sector = _normalise_sector_label(vector_store.get_company_sector(company_name))
        if db_sector and db_sector.casefold() != company_name.casefold():
            exp["company_sector"] = db_sector
            continue

        sector = _sector_lookup_with_openai(company_name, context_text)
        if not sector:
            sector = _sector_lookup_fallback(company_name, context_text)

        if sector and sector.casefold() != company_name.casefold():
            exp["company_sector"] = sector
            vector_store.upsert_company_sector(company_name, sector, source="ollama-web-or-fallback")
        else:
            exp["company_sector"] = "Industry Not Determined"


def _should_fallback_on_strict_ai_error(err: Exception) -> bool:
    """Allow strict selected-model requests to degrade gracefully on transient/provider quota failures."""
    text = str(err or "").lower()
    if not text:
        return False

    retryable_markers = (
        "insufficient_quota",
        "exceeded your current quota",
        "rate limit",
        "too many requests",
        "error code: 429",
        "timed out",
        "timeout",
        "temporarily unavailable",
        "service unavailable",
    )
    return any(marker in text for marker in retryable_markers)


def _template_download_name(template_id: str) -> str:
    template = TEMPLATE_REGISTRY.get(template_id)
    return template.display_name if template.user_created else template.download_base_name


def _safe_filename_component(value: str, fallback: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", str(value or "").strip()).strip("_")
    return cleaned or fallback


def _ensure_resume_name(resume_data: Dict[str, Any], filename: str = "") -> None:
    contact = resume_data.setdefault("contact", {})
    if str(contact.get("name") or "").strip():
        return
    fallback = Path(filename).stem if filename else "Untitled Resume"
    contact["name"] = re.sub(r"[_-]+", " ", fallback).strip()[:80] or "Untitled Resume"


def _reload_template_registry() -> None:
    global TEMPLATE_REGISTRY, RENDERER_FACTORY
    TEMPLATE_REGISTRY = TemplateRegistry.discover(user_templates_dir=USER_TEMPLATES_DIR)
    RENDERER_FACTORY = RendererFactory(TEMPLATE_REGISTRY)


def _generate_session_artifacts(session_id: str, resume_data: Dict[str, Any], filename: str = "") -> Dict[str, Any]:
    """Generate both template documents and their HTML previews for a resume."""
    primary_dir = TEMP_DIR / session_id
    fallback_dir = TEMP_DIR / f"{session_id}_{uuid.uuid4().hex[:8]}"
    last_error: Exception | None = None

    for idx, session_dir in enumerate((primary_dir, fallback_dir)):
        try:
            if idx == 0 and session_dir.exists():
                shutil.rmtree(session_dir, ignore_errors=True)
            session_dir.mkdir(parents=True, exist_ok=True)

            t1_docx = str(session_dir / "kanini_classic.docx")
            t2_docx = str(session_dir / "deloitte_format.docx")
            t1_pdf = str(session_dir / "kanini_classic.pdf")
            t2_pdf = str(session_dir / "deloitte_format.pdf")

            canonical_resume = ResumeAdapter.from_legacy(resume_data)
            format1_renderer = RENDERER_FACTORY.get("kanini-format-1")
            format2_renderer = RENDERER_FACTORY.get("kanini-format-2")
            format1_html = format1_renderer.render_html(canonical_resume).content or ""
            format2_html = format2_renderer.render_html(canonical_resume).content or ""

            preview_html = {
                "template1": format1_html,
                "template2": format2_html,
            }

            return {
                "resume_data": resume_data,
                "filename": filename,
                "files": {
                    "template1_docx": "",
                    "template2_docx": "",
                    "template1_pdf": "",
                    "template2_pdf": "",
                },
                "preview_html": preview_html,
            }
        except PermissionError as exc:
            last_error = exc
            continue

    if last_error is not None:
        raise last_error
    raise RuntimeError("Failed to generate session artifacts.")


def _anonymise_resume_for_template(resume_data: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy safe for template rendering without candidate personal details.

    Keeps only the candidate name so it can be displayed on the template;
    removes email, phone, address and other personal/contact fields.
    """
    if not isinstance(resume_data, dict):
        return {}

    redacted = copy.deepcopy(resume_data)
    old_contact = redacted.get("contact") if isinstance(redacted.get("contact"), dict) else {}
    name = str(old_contact.get("name") or "").strip()
    redacted["contact"] = {"name": name} if name else {}

    # Drop common top-level personal fields if present in parser output.
    for key in ("email", "phone", "mobile", "address", "linkedin", "github", "portfolio", "website"):
        redacted.pop(key, None)

    return redacted


def _persist_resume(session_id: str, resume_data: Dict[str, Any], filename: str = "") -> None:
    try:
        vector_store.store_resume(session_id, resume_data, filename)
    except Exception as exc:
        print(f"[vector_store] store failed for {session_id}: {exc}")


def _allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _dedupe_keep_order(values):
    seen = set()
    out = []
    for value in values:
        text = str(value).strip()
        if not text:
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
    return out


_SKILL_NOISE_RE = re.compile(
    r"\b(?:company(?:\s+name)?|designation|position|duration|role|responsibilities?"
    r"|roles?\s+and\s+responsibilities|project\s+[ivx]+|project\s*[-:]?\s*\d+"
    r"|working\s+experience|employment|till\s+date|present|current)\b",
    re.IGNORECASE,
)

_MONTH_RE = re.compile(
    r"\b(?:jan|january|feb|february|mar|march|apr|april|may|jun|june|jul|july|aug|august"
    r"|sep|september|oct|october|nov|november|dec|december)\b",
    re.IGNORECASE,
)

_SKILL_PROFICIENCY_RE = re.compile(
    r"^(?:expert|intermediate|experienced|beginner|advanced|proficient|familiar|novice|basic)$",
    re.IGNORECASE,
)

_SUMMARY_HEAD_RE = re.compile(
    r"(?is)(?:^|\n)\s*(?:profile\s+summary|professional\s+summary|summary\s+of\s+experience|"
    r"professional\s+profile|career\s+summary|objective)\s*:?\s*(.+?)(?=\n\s*(?:technical\s+skills|skills|"
    r"work(?:ing)?\s+experience|employment\s+history|education|projects?)\s*:?(?:\n|$)|\Z)"
)

_EDU_NOISE_RE = re.compile(
    r"\b(?:developed|integrated|managed|improved|created|implemented|designed|"
    r"streamline|enhance|workflow|application|api)\b",
    re.IGNORECASE,
)

_SUMMARY_CONTACT_LINE_RE = re.compile(
    r"\b(?:contact|mobile|phone|email|e-?mail|linkedin|github|portfolio|www\.|http[s]?://)\b",
    re.IGNORECASE,
)

_SUMMARY_ADDRESS_HINT_RE = re.compile(
    r"\b(?:india|tamil\s*nadu|coimbatore|chennai|bangalore|hyderabad|address|pin(?:code)?)\b",
    re.IGNORECASE,
)


def _summary_is_weak(summary: str) -> bool:
    text = str(summary or "").strip()
    if not text:
        return True

    if len(text.split()) <= 4:
        return True
    if re.fullmatch(r"[A-Za-z\s,.-]+\n?\d{5,6}", text):
        return True
    if re.search(r"\b(?:coimbatore|chennai|bangalore|india)\b", text, re.IGNORECASE) and len(text.split()) <= 6:
        return True
    return False


def _recover_summary_from_raw_text(raw_text: str) -> str:
    text = str(raw_text or "")
    if not text.strip():
        return ""

    m = _SUMMARY_HEAD_RE.search(text)
    if not m:
        return ""

    block = m.group(1)
    lines = [ln.strip() for ln in block.replace("\r", "\n").split("\n") if ln.strip()]
    cleaned: list[str] = []
    for ln in lines:
        item = re.sub(r"^\s*(?:[•\u2022\u2023\u25E6\u2043\u2219\-\*\u2192\u25BA\uf0b7]+|\d+[.)])\s*", "", ln).strip()
        if not item:
            continue
        if re.search(r"\b(?:linkedin|github|@)\b", item, re.IGNORECASE):
            continue
        cleaned.append(item)

    return "\n".join(cleaned[:6]).strip()


def _is_contact_like_summary_line(line: str) -> bool:
    text = str(line or "").strip()
    if not text:
        return True

    # Pure marker/noise lines from PDF bullets.
    if re.fullmatch(r"[+|:\-\u2022\u2023\u25E6\u2043\u2219\uf0b7\s]+", text):
        return True

    if _SUMMARY_CONTACT_LINE_RE.search(text):
        return True

    # Phone-like lines, e.g. "91-63809 51390".
    digits = re.sub(r"\D", "", text)
    if len(digits) >= 10 and len(text.split()) <= 4:
        return True

    # Address-ish short lines (city/state/pincode only).
    if re.search(r"\b\d{5,6}\b", text) and len(text.split()) <= 7:
        return True
    if _SUMMARY_ADDRESS_HINT_RE.search(text) and len(text.split()) <= 7:
        return True

    return False


def _clean_summary_text(summary: str) -> str:
    raw = str(summary or "").strip()
    if not raw:
        return ""

    lines = [ln.strip() for ln in raw.replace("\r", "\n").split("\n") if ln.strip()]
    cleaned: list[str] = []
    for ln in lines:
        line = re.sub(r"^\s*(?:[•\u2022\u2023\u25E6\u2043\u2219\-\*\u2192\u25BA\uf0b7]+|\d+[.)])\s*", "", ln).strip()
        if not line:
            continue
        if _is_contact_like_summary_line(line):
            continue
        cleaned.append(line)

    # De-duplicate while preserving order.
    out: list[str] = []
    seen = set()
    for ln in cleaned:
        key = ln.casefold()
        if key not in seen:
            seen.add(key)
            out.append(ln)

    return "\n".join(out).strip()


def _project_looks_noisy(project: Dict[str, Any]) -> bool:
    name = str(project.get("name") or "").strip()
    client = str(project.get("client") or "").strip()
    role = str(project.get("role") or "").strip()
    description = str(project.get("description") or "").strip()
    technologies = project.get("technologies") if isinstance(project.get("technologies"), list) else []
    responsibilities = project.get("responsibilities") if isinstance(project.get("responsibilities"), list) else []

    if not (name or client or role or description or technologies or responsibilities):
        return True

    # Misparsed projects often look like a comma list in name, one-word client,
    # empty technologies, and a huge generic sentence blob in description.
    if "," in name and len(client.split()) == 1 and not technologies and len(description) > 180:
        return True

    if name.count(",") >= 2 and len(client.split()) <= 2 and not technologies and not responsibilities:
        return True

    return False


def _tokenize_skill_text(value: Any) -> list[str]:
    text = str(value or "").strip()
    if not text:
        return []

    text = re.sub(r"[\u2022\u2023\u25E6\u2043\u2219\uf0b7]+", ",", text)
    text = re.sub(r"\s+", " ", text)

    out: list[str] = []
    for chunk in re.split(r",|;|\n", text):
        chunk = re.sub(r"^[\s:]+", "", chunk.strip()).strip(".")
        if not chunk:
            continue

        # If chunk is like "Programming Languages: Python" keep only value part.
        m = re.match(r"^[A-Za-z][A-Za-z\s&/\-]{1,40}:\s*(.+)$", chunk)
        if m:
            chunk = m.group(1).strip()
        if chunk:
            out.append(chunk)

    return out


def _looks_like_skill_noise(token: str, banned_terms: list[str]) -> bool:
    t = str(token or "").strip()
    if not t:
        return True

    if _SKILL_NOISE_RE.search(t):
        return True
    if _MONTH_RE.search(t) and re.search(r"\b\d{4}\b", t):
        return True
    if _SKILL_PROFICIENCY_RE.match(t):
        return True
    if re.search(r"\b(?:troubleshoot|issues?|environment(?:s)?|workflow|maintainability)\b", t, re.IGNORECASE):
        return True
    if len(t.split()) > 6:
        return True
    if re.search(r"\b(?:associate|developer|engineer|analyst|manager|consultant)\b", t, re.IGNORECASE) and len(t.split()) >= 2:
        # Looks like a job title rather than a skill.
        return True

    low = t.casefold()
    for banned in banned_terms:
        b = banned.casefold().strip()
        if not b:
            continue
        if low == b or (len(b) >= 8 and b in low):
            return True

    return False


_EXP_LABEL_PREFIX_RE = re.compile(
    r"^(?:company(?:\s+name)?|client|employer|organization|organisation|designation|role|title)\s*[:\-]\s*",
    re.IGNORECASE,
)

_ROLE_HINT_RE = re.compile(
    r"\b(?:engineer|developer|manager|analyst|architect|designer|consultant|lead|"
    r"senior|junior|director|head|chief|officer|programmer|specialist|associate|"
    r"coordinator|intern|trainee|administrator|tester|qa|sdet|devops|scrum|owner)\b",
    re.IGNORECASE,
)

_COMPANY_HINT_RE = re.compile(
    r"\b(?:inc\.?|llc|ltd\.?|pvt\.?|corp\.?|corporation|technologies|technology|"
    r"solutions|systems|services|consulting|group|bank|university|labs?|software|"
    r"company|co\.?|limited|private)\b",
    re.IGNORECASE,
)

_NON_COMPANY_EXP_VALUE_RE = re.compile(
    r"\b(?:windows|visual\s+studio|sql\s+server|client\s+server|n-?tier|react|asp\.?net|"
    r"api|framework|platforms?|architecture|technologies|development\s+environments?)\b",
    re.IGNORECASE,
)

_EXP_PLACEHOLDER_VALUES = {
    "company name", "designation", "duration", "role", "position", "title",
    "company", "client", "employer", "organization", "organisation", ":", "-", "--",
}

_EXP_LABEL_RE = re.compile(
    r"^(Company Name|Designation|Duration|Role|Position|Title|Client|Employer|"
    r"Organization|Organisation|Company|Location)\s*[:\-]?\s*(.*)$",
    re.IGNORECASE,
)

_EXP_DATE_RE = re.compile(
    r"\b(?:\d{1,2}[/-]\d{4}|\d{4}\s*[-–—]\s*(?:\d{4}|present|current|till\s+date)"
    r"|(?:jan|january|feb|february|mar|march|apr|april|may|jun|june|jul|july|aug|august"
    r"|sep|september|oct|october|nov|november|dec|december)\s*\d{2,4})\b",
    re.IGNORECASE,
)


def _clean_exp_field(value: Any) -> str:
    text = str(value or "").strip()
    return _EXP_LABEL_PREFIX_RE.sub("", text).strip()


def _is_placeholder_exp_value(value: str) -> bool:
    v = str(value or "").strip().casefold().strip(" :.-")
    return not v or v in _EXP_PLACEHOLDER_VALUES


def _coalesce_experience_label_lines(lines: list[str]) -> list[str]:
    out: list[str] = []
    i = 0
    n = len(lines)
    while i < n:
        line = str(lines[i] or "").strip()
        if not line:
            i += 1
            continue
        if line in {":", "-", "–", "—"}:
            i += 1
            continue

        m = _EXP_LABEL_RE.match(line)
        if not m:
            out.append(line)
            i += 1
            continue

        label = m.group(1).strip()
        value = m.group(2).strip()
        if value:
            out.append(f"{label}: {value}")
            i += 1
            continue

        j = i + 1
        while j < n and not str(lines[j] or "").strip():
            j += 1
        if j < n and str(lines[j] or "").strip() in {":", "-", "–", "—"}:
            j += 1
            while j < n and not str(lines[j] or "").strip():
                j += 1

        if j < n:
            cand = str(lines[j] or "").strip()
            if cand and not _EXP_LABEL_RE.match(cand):
                out.append(f"{label}: {cand}")
                i = j + 1
                continue

        out.append(f"{label}:")
        i += 1
    return out


def _recover_experience_from_raw_text(raw_text: str) -> list[Dict[str, Any]]:
    if not raw_text:
        return []

    def _recover_implicit_triplet() -> list[Dict[str, Any]]:
        """Recover experience when PDF extraction loses labels but preserves values.

        Observed pattern in failing PDFs:
          : KANINI SOFTWARE SOLUTIONS
          : Associate Developer.
          : July 2022- Till date.
        appearing before an empty `Working Experience:` block.
        """
        raw_lines = [str(line or "").strip() for line in raw_text.splitlines()]
        work_idx = None
        for idx, line in enumerate(raw_lines):
            if re.match(r"^Working Experience:?$", line, re.IGNORECASE):
                work_idx = idx
                break
        if work_idx is None:
            return []

        # Look backward from the Work Experience heading for short colon-prefixed values.
        colon_values: list[str] = []
        for line in reversed(raw_lines[:work_idx]):
            stripped = line.strip()
            if not stripped:
                if colon_values:
                    break
                continue
            if re.match(r"^(Technical Skills|Professional Summary)[:]?$", stripped, re.IGNORECASE):
                break
            if re.match(r"^[:]\s*.+$", stripped):
                colon_values.append(re.sub(r"^[:]\s*", "", stripped).strip())
                if len(colon_values) >= 5:
                    break
                continue
            if colon_values:
                break

        if not colon_values:
            return []

        colon_values.reverse()
        company = ""
        title = ""
        dates = ""
        def _looks_like_implicit_company_candidate(text: str) -> bool:
            cleaned = str(text or "").strip().strip(".")
            if not cleaned:
                return False
            if _NON_COMPANY_EXP_VALUE_RE.search(cleaned):
                return False
            if "/" in cleaned and not re.search(
                r"\b(?:pvt|ltd|inc|llc|corp|solutions|software|technologies)\b",
                cleaned,
                re.IGNORECASE,
            ):
                return False
            return _looks_like_company(cleaned)

        for value in colon_values:
            cleaned = value.strip().strip(".")
            if not cleaned:
                continue
            if not dates and _EXP_DATE_RE.search(cleaned):
                dates = cleaned
                continue
            if not company and _looks_like_implicit_company_candidate(cleaned) and not _looks_like_role(cleaned):
                company = cleaned
                continue
            if not title and _looks_like_role(cleaned):
                title = cleaned
                continue

        if company or title or dates:
            return [_normalise_experience_entry({
                "company": company,
                "title": title,
                "dates": dates,
                "location": "",
                "responsibilities": [],
            })]
        return []

    implicit_recovery = _recover_implicit_triplet()

    lines = _coalesce_experience_label_lines(raw_text.splitlines())
    recovered: list[Dict[str, Any]] = []
    current: Dict[str, Any] = {
        "title": "",
        "company": "",
        "location": "",
        "dates": "",
        "responsibilities": [],
    }

    def _flush_current() -> None:
        nonlocal current
        entry = _normalise_experience_entry(dict(current))
        if not (_is_placeholder_exp_value(entry.get("company", "")) and _is_placeholder_exp_value(entry.get("title", ""))):
            recovered.append(entry)
        current = {"title": "", "company": "", "location": "", "dates": "", "responsibilities": []}

    for line in lines:
        m = _EXP_LABEL_RE.match(line)
        if not m:
            continue
        label = m.group(1).strip().lower()
        value = m.group(2).strip()

        if label in {"company name", "client", "employer", "organization", "organisation", "company"}:
            if current.get("company") and value and value.casefold() != str(current.get("company", "")).casefold():
                _flush_current()
            current["company"] = value
            continue

        if label in {"designation", "role", "position", "title"}:
            current["title"] = value
            continue

        if label == "duration":
            current["dates"] = value
            continue

        if label == "location":
            current["location"] = value

    _flush_current()

    # As a safety net, include entries only when at least company or title is meaningful.
    cleaned = [
        e for e in _merge_experience_fragments(recovered)
        if not (_is_placeholder_exp_value(e.get("company", "")) and _is_placeholder_exp_value(e.get("title", "")))
    ]

    explicit_bad_heading = any(
        re.search(r"\b(project summary|roles? and responsibilities|working experience)\b", str(e.get("title") or ""), re.IGNORECASE)
        or re.search(r"\b(project summary|roles? and responsibilities|working experience)\b", str(e.get("dates") or ""), re.IGNORECASE)
        for e in cleaned
    )

    if implicit_recovery and (_experience_quality_score(implicit_recovery) > _experience_quality_score(cleaned) or explicit_bad_heading):
        return implicit_recovery
    if cleaned:
        return cleaned
    return implicit_recovery


def _experience_is_broken(exps: Any) -> bool:
    if not isinstance(exps, list) or not exps:
        return True

    meaningful = 0
    for exp in exps:
        if not isinstance(exp, dict):
            continue
        company = str(exp.get("company") or "").strip()
        title = str(exp.get("title") or "").strip()
        dates = str(exp.get("dates") or "").strip()

        if company.casefold() == "designation" and title.casefold() == "company name":
            continue
        if _is_placeholder_exp_value(company) and _is_placeholder_exp_value(title) and not dates:
            continue
        meaningful += 1

    return meaningful == 0


def _experience_quality_score(exps: Any) -> int:
    if not isinstance(exps, list):
        return 0
    score = 0
    for exp in exps:
        if not isinstance(exp, dict):
            continue
        company = str(exp.get("company") or "").strip()
        title = str(exp.get("title") or "").strip()
        dates = str(exp.get("dates") or "").strip()

        if _is_placeholder_exp_value(company) and _is_placeholder_exp_value(title):
            score -= 3
            continue
        if company and not _is_placeholder_exp_value(company):
            score += 2
        if title and not _is_placeholder_exp_value(title):
            score += 2
        if dates:
            score += 1
        if company.casefold() == "designation" or title.casefold() == "company name":
            score -= 4
    return score


def _skills_quality_score(skills: Any) -> int:
    if not isinstance(skills, dict):
        return 0
    score = 0
    for _, items in skills.items():
        if not isinstance(items, list):
            continue
        for item in items:
            token = str(item or "").strip()
            if not token:
                continue
            if _SKILL_NOISE_RE.search(token):
                score -= 3
                continue
            if len(token.split()) > 6:
                score -= 2
                continue
            score += 1
    return score


def _summary_quality_score(summary: Any) -> int:
    text = str(summary or "").strip()
    if not text:
        return 0

    score = 0
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    words = re.findall(r"[A-Za-z][A-Za-z+.#\-/]{1,}", text)

    score += min(len(words), 40)
    if len(lines) >= 2:
        score += 4

    if re.search(r"\b(?:company\s+name|designation|duration|roles?\s+and\s+responsibilities|project\s+summary)\b", text, re.IGNORECASE):
        score -= 8
    if re.search(r"[\w.+-]+@[\w-]+\.[A-Za-z]{2,}", text) or re.search(
        r"(?:\+?\d{1,3}[\s\-.]?)?(?:\(?\d{3}\)?[\s\-.]?)?\d{3}[\s\-.]?\d{4}",
        text,
    ):
        score -= 6

    return max(score, 0)


def _pick_better_pdf_sections(ai_data: Dict[str, Any], regex_data: Dict[str, Any]) -> Dict[str, Any]:
    """For PDF uploads, blend AI and regex outputs by section quality."""
    ai_norm = ResumeAdapter.to_legacy(normalise_resume(ResumeAdapter.from_legacy(ai_data)))
    rx_norm = ResumeAdapter.to_legacy(normalise_resume(ResumeAdapter.from_legacy(regex_data)))

    # Keep AI as base for narrative fields, but override sections that are clearly
    # better in regex output for noisy PDF extraction.
    merged = dict(ai_norm)

    ai_exp_score = _experience_quality_score(ai_norm.get("experience"))
    rx_exp_score = _experience_quality_score(rx_norm.get("experience"))
    if rx_exp_score > ai_exp_score:
        merged["experience"] = rx_norm.get("experience", [])

    ai_sk_score = _skills_quality_score(ai_norm.get("skills"))
    rx_sk_score = _skills_quality_score(rx_norm.get("skills"))
    if rx_sk_score > ai_sk_score:
        merged["skills"] = rx_norm.get("skills", {})

    ai_summary_score = _summary_quality_score(ai_norm.get("summary"))
    rx_summary_score = _summary_quality_score(rx_norm.get("summary"))
    if rx_summary_score > ai_summary_score:
        merged["summary"] = str(rx_norm.get("summary") or "").strip()

    # If AI missed contact name but regex found it, trust regex contact.
    ai_contact = merged.get("contact") if isinstance(merged.get("contact"), dict) else {}
    rx_contact = rx_norm.get("contact") if isinstance(rx_norm.get("contact"), dict) else {}
    if (not str(ai_contact.get("name") or "").strip()) and str(rx_contact.get("name") or "").strip():
        merged["contact"] = rx_contact

    return merged


def _log_pdf_debug(
    stage: str,
    raw_text: str,
    data: Dict[str, Any],
    regex_data: Dict[str, Any] | None = None,
    *,
    session_id: str = "",
    filename: str = "",
) -> None:
    """Emit focused diagnostics for PDF parsing when PDF_PARSE_DEBUG=1."""
    if not PDF_DEBUG_ENABLED:
        return

    try:
        exp = data.get("experience") if isinstance(data, dict) else []
        skills = data.get("skills") if isinstance(data, dict) else {}
        exp_score = _experience_quality_score(exp)
        sk_score = _skills_quality_score(skills)

        suspicious_skill_tokens = []
        if isinstance(skills, dict):
            for items in skills.values():
                if not isinstance(items, list):
                    continue
                for item in items:
                    token = str(item or "").strip()
                    if token and _SKILL_NOISE_RE.search(token):
                        suspicious_skill_tokens.append(token)

        preview_lines = [ln for ln in raw_text.splitlines() if ln.strip()][:40]
        preview = "\\n".join(preview_lines)

        logger.warning(
            "[PDF DEBUG][%s] session=%s file=%s chars=%d exp_score=%d skills_score=%d exp_count=%d skill_cats=%d suspicious_tokens=%d",
            stage,
            session_id,
            filename,
            len(raw_text or ""),
            exp_score,
            sk_score,
            len(exp) if isinstance(exp, list) else 0,
            len(skills) if isinstance(skills, dict) else 0,
            len(suspicious_skill_tokens),
        )
        logger.warning("[PDF DEBUG][%s] experience=%s", stage, json.dumps(exp, ensure_ascii=True)[:4000])
        logger.warning("[PDF DEBUG][%s] skills=%s", stage, json.dumps(skills, ensure_ascii=True)[:4000])
        if suspicious_skill_tokens:
            logger.warning("[PDF DEBUG][%s] suspicious_skill_tokens=%s", stage, json.dumps(suspicious_skill_tokens[:30], ensure_ascii=True))
        logger.warning("[PDF DEBUG][%s] raw_preview=\n%s", stage, preview)

        if regex_data is not None:
            rx_exp = regex_data.get("experience") if isinstance(regex_data, dict) else []
            rx_sk = regex_data.get("skills") if isinstance(regex_data, dict) else {}
            logger.warning(
                "[PDF DEBUG][%s] regex_exp_score=%d regex_skills_score=%d",
                stage,
                _experience_quality_score(rx_exp),
                _skills_quality_score(rx_sk),
            )
    except Exception as exc:
        logger.warning("[PDF DEBUG] log failure: %s", exc)


def _looks_like_role(text: str) -> bool:
    return bool(text and _ROLE_HINT_RE.search(text))


def _looks_like_company(text: str) -> bool:
    if not text:
        return False
    if _COMPANY_HINT_RE.search(text):
        return True
    # Multi-word proper-name strings are often company names
    words = [w for w in re.split(r"\s+", text.strip()) if w]
    return len(words) >= 2 and text[0].isupper() and not _looks_like_role(text)


def _split_title_company(text: str) -> tuple[str, str]:
    raw = str(text or "").strip()
    if not raw:
        return "", ""

    m = re.match(r"^(.+?)\s+(?:at|@)\s+(.+)$", raw, flags=re.IGNORECASE)
    if m:
        left, right = m.group(1).strip(), m.group(2).strip()
        return left, right

    for sep in ("|", " - ", " – ", " — "):
        if sep in raw:
            parts = [p.strip() for p in raw.split(sep) if p.strip()]
            if len(parts) >= 2:
                return parts[0], parts[1]

    return raw, ""


def _normalise_experience_entry(exp: Dict[str, Any]) -> Dict[str, Any]:
    title = _clean_exp_field(exp.get("title"))
    company = _clean_exp_field(exp.get("company"))

    title = re.sub(r"^(?:position|designation|role|title)\s*[:\-]\s*", "", title, flags=re.IGNORECASE).strip()
    company = re.sub(r"^(?:company(?:\s+name)?|client|employer|organization|organisation)\s*[:\-]\s*", "", company, flags=re.IGNORECASE).strip()

    # Recover when a parser returns a combined role/company string in one field.
    if title and not company:
        split_title, split_company = _split_title_company(title)
        if split_company:
            title, company = split_title, split_company
    elif company and not title:
        split_title, split_company = _split_title_company(company)
        if split_company:
            title, company = split_title, split_company

    # Fix obvious swapped fields: role text in company and org text in title.
    if company and title:
        company_looks_role = _looks_like_role(company)
        title_looks_role = _looks_like_role(title)
        title_looks_company = _looks_like_company(title)
        company_looks_company = _looks_like_company(company)

        should_swap = False
        if company_looks_role and not title_looks_role:
            should_swap = True
        elif company_looks_role and title_looks_company and not company_looks_company:
            should_swap = True

        if should_swap:
            title, company = company, title

    exp["title"] = title
    exp["company"] = company
    return exp


def _merge_experience_fragments(exps: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
    merged: list[Dict[str, Any]] = []

    for exp in exps:
        if not isinstance(exp, dict):
            continue

        cur = _normalise_experience_entry(exp)
        title = str(cur.get("title") or "").strip()
        company = str(cur.get("company") or "").strip()
        dates = str(cur.get("dates") or "").strip()
        responsibilities = cur.get("responsibilities") if isinstance(cur.get("responsibilities"), list) else []

        # Company-only fragment often lands in title when parsing table-like text.
        if not company and title and _looks_like_company(title) and not _looks_like_role(title):
            company, title = title, ""

        cur["title"] = title
        cur["company"] = company

        if merged:
            prev = merged[-1]
            prev_title = str(prev.get("title") or "").strip()
            prev_company = str(prev.get("company") or "").strip()

            # Merge role-only continuation into prior company-only entry.
            if prev_company and not prev_title and title and not company and (_looks_like_role(title) or title.lower().startswith("position:")):
                prev["title"] = title.removeprefix("Position:").removeprefix("position:").strip()
                if not prev.get("dates") and dates:
                    prev["dates"] = dates
                if responsibilities:
                    prev_resps = prev.get("responsibilities") if isinstance(prev.get("responsibilities"), list) else []
                    prev["responsibilities"] = _dedupe_keep_order(prev_resps + responsibilities)
                continue

            # Merge obvious descriptive orphan lines into previous responsibilities.
            if not company and title and len(title.split()) >= 8 and not dates:
                prev_resps = prev.get("responsibilities") if isinstance(prev.get("responsibilities"), list) else []
                prev["responsibilities"] = _dedupe_keep_order(prev_resps + [title])
                continue

        # Drop completely empty fragments.
        if not (title or company or dates or responsibilities):
            continue

        merged.append(cur)

    return merged


def _experience_entry_score(exp: Dict[str, Any]) -> int:
    company = str(exp.get("company") or "").strip()
    title = str(exp.get("title") or "").strip()
    dates = str(exp.get("dates") or "").strip()
    responsibilities = exp.get("responsibilities") if isinstance(exp.get("responsibilities"), list) else []

    score = 0
    if company and not _is_placeholder_exp_value(company):
        score += 3
    if title and not _is_placeholder_exp_value(title):
        score += 3
    if dates:
        score += 2
    if responsibilities:
        score += min(len(responsibilities), 3)
    if len(company.split()) > 8:
        score -= 2
    if len(title.split()) > 8:
        score -= 2
    if re.search(r"\b(project summary|roles? and responsibilities|working experience|designation|company name|duration)\b", f"{company} {title} {dates}", re.IGNORECASE):
        score -= 4
    return score


def _canonicalise_company_name(company: str) -> str:
    text = str(company or "").strip().strip(".")
    if not text:
        return ""
    # Trim descriptive company blurbs: "Exterro, a company that specializes ..."
    text = re.split(r",\s+a\s+company\s+that\b|,\s+which\s+|\s+speciali[sz]es\s+in\b", text, maxsplit=1, flags=re.IGNORECASE)[0].strip()
    return text.rstrip(",")


def _finalise_experience_entries(exps: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
    def _title_key(text: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", str(text or "").casefold())

    def _company_key(text: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", str(text or "").casefold())

    cleaned_entries: list[Dict[str, Any]] = []

    for raw in exps:
        if not isinstance(raw, dict):
            continue

        exp = _normalise_experience_entry(dict(raw))
        exp["company"] = _canonicalise_company_name(exp.get("company", ""))
        exp["title"] = str(exp.get("title") or "").strip().strip(".")
        exp["dates"] = str(exp.get("dates") or "").strip().strip(".")
        responsibilities = exp.get("responsibilities") if isinstance(exp.get("responsibilities"), list) else []
        exp["responsibilities"] = _dedupe_keep_order(responsibilities)

        # Drop weak narrative/company-only fragments that usually duplicate a
        # stronger entry in PDF resumes.
        if exp["company"] and not exp["title"] and not exp["dates"] and len(exp["company"].split()) >= 6:
            continue

        if _experience_entry_score(exp) <= 0:
            continue

        merged_into_existing = False
        for existing in cleaned_entries:
            same_company = exp["company"] and existing.get("company") and exp["company"].casefold() == str(existing.get("company") or "").casefold()
            exp_company_key = _company_key(exp["company"])
            existing_company_key = _company_key(existing.get("company") or "")
            similar_company = bool(
                exp_company_key
                and existing_company_key
                and (
                    exp_company_key.startswith(existing_company_key)
                    or existing_company_key.startswith(exp_company_key)
                )
            )
            same_title = exp["title"] and existing.get("title") and _title_key(exp["title"]) == _title_key(existing.get("title") or "")
            same_dates = exp["dates"] and existing.get("dates") and exp["dates"].casefold() == str(existing.get("dates") or "").casefold()

            if same_company or similar_company or same_title or (same_title and same_dates):
                if not existing.get("company") and exp["company"]:
                    existing["company"] = exp["company"]
                if not existing.get("title") and exp["title"]:
                    existing["title"] = exp["title"]
                if not existing.get("dates") and exp["dates"]:
                    existing["dates"] = exp["dates"]
                if not existing.get("location") and exp.get("location"):
                    existing["location"] = exp.get("location")
                existing_resps = existing.get("responsibilities") if isinstance(existing.get("responsibilities"), list) else []
                existing["responsibilities"] = _dedupe_keep_order(existing_resps + exp["responsibilities"])

                # Prefer the better company/title if one entry only contains prose.
                if _experience_entry_score(exp) > _experience_entry_score(existing):
                    if exp["company"]:
                        existing["company"] = exp["company"]
                    if exp["title"]:
                        existing["title"] = exp["title"]
                    if exp["dates"]:
                        existing["dates"] = exp["dates"]
                merged_into_existing = True
                break

        if not merged_into_existing:
            cleaned_entries.append(exp)

    cleaned_entries.sort(key=_experience_entry_score, reverse=True)
    return cleaned_entries


def _frontend_dist_dir() -> Path | None:
    """Locate built Angular assets for local and packaged (PyInstaller) runs."""
    backend_dir = Path(__file__).resolve().parent
    exe_dir = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else None
    candidates = [
        backend_dir.parent / "frontend-ng" / "dist" / "frontend-ng" / "browser",
        backend_dir.parent / "frontend-ng" / "dist" / "frontend-ng",
    ]

    # PyInstaller runtime extraction folder.
    meipass = getattr(sys, "_MEIPASS", "")
    if meipass:
        candidates.insert(0, Path(meipass) / "frontend-dist")

    # PyInstaller --onedir runtime paths.
    if exe_dir is not None:
        candidates.insert(0, exe_dir / "_internal" / "frontend-dist")
        candidates.insert(0, exe_dir / "frontend-dist")
        candidates.insert(0, backend_dir / "frontend-dist")

    for candidate in candidates:
        if candidate.exists() and candidate.is_dir() and (candidate / "index.html").exists():
            return candidate
    return None


# ─── Routes ──────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/llm-models")
async def llm_models():
    """Return model dropdown options with availability flags."""
    return {"models": ai_parser.get_model_dropdown_options()}


@app.get("/api/templates")
async def list_templates():
    """Return enabled template metadata without filesystem implementation details."""
    return {"templates": [template.public_dict() for template in TEMPLATE_REGISTRY.list_enabled()]}


@app.post("/api/template-drafts")
async def create_template_draft(file: UploadFile = File(...)):
    """Store a sample PDF and extract normalized content for later template generation."""
    filename = file.filename or ""
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="A sample resume must be a PDF file.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail="The uploaded PDF is empty.")
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 10 MB).")

    draft_id = str(uuid.uuid4())
    draft_dir = TEMPLATE_DRAFT_DIR / draft_id
    try:
        draft_dir.mkdir(parents=True, exist_ok=False)
        source_path = draft_dir / "original.pdf"
        source_path.write_bytes(content)
        raw_text = extract_text(str(source_path), "pdf")
        if not raw_text.strip():
            raise ValueError("Could not extract readable text from the PDF.")

        parsed = ResumeAdapter.adapt_regex_output(parse_resume(str(source_path), "pdf"))
        extracted_data = ResumeAdapter.to_legacy(normalise_resume(parsed, raw_text=raw_text))
        draft_payload = {
            "draft_id": draft_id,
            "status": "uploaded",
            "filename": filename,
            "extracted_data": extracted_data,
            "raw_text": raw_text,
        }
        (draft_dir / "extracted_data.json").write_text(json.dumps(draft_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except ValueError as exc:
        shutil.rmtree(draft_dir, ignore_errors=True)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        shutil.rmtree(draft_dir, ignore_errors=True)
        logger.error("Template draft upload failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to create template draft.") from exc

    return {
        "draft_id": draft_id,
        "status": "uploaded",
        "filename": filename,
        "extracted_data": extracted_data,
    }


@app.post("/api/template-drafts/{draft_id}/generate")
async def generate_template_draft(draft_id: str):
    """Generate and validate a non-executable template draft from uploaded resume data."""
    try:
        normalized_draft_id = str(uuid.UUID(draft_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Template draft was not found.") from exc

    draft_dir = TEMPLATE_DRAFT_DIR / normalized_draft_id
    extracted_path = draft_dir / "extracted_data.json"
    if not draft_dir.is_dir() or not extracted_path.is_file():
        raise HTTPException(status_code=404, detail="Template draft was not found.")

    try:
        draft_data = json.loads(extracted_path.read_text(encoding="utf-8"))
        extracted_data = draft_data["extracted_data"]
        if not isinstance(extracted_data, dict):
            raise ValueError("Draft data is invalid.")
    except (OSError, json.JSONDecodeError, KeyError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Template draft data is invalid.") from exc

    try:
        generated = await asyncio.wait_for(run_in_threadpool(generate_template_spec, extracted_data), timeout=95)
        spec = validate_template_spec(generated)
        canonical_resume = ResumeAdapter.from_legacy(extracted_data)
        preview_html = render_template_draft_preview(canonical_resume, spec)
        (draft_dir / "template_spec.json").write_text(json.dumps(spec.model_dump(), indent=2), encoding="utf-8")
        (draft_dir / "preview.html").write_text(preview_html, encoding="utf-8")
    except asyncio.TimeoutError as exc:
        raise HTTPException(status_code=504, detail="Template generation timed out. Please try again.") from exc
    except ai_parser.ProviderUnavailableError as exc:
        raise HTTPException(status_code=503, detail="Ollama is unavailable. Check that the configured model is running.") from exc
    except (TemplateGenerationError, TemplateSpecValidationError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Template draft generation failed for %s: %s", normalized_draft_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to generate the template draft. Please try again.") from exc

    return {
        "draft_id": normalized_draft_id,
        "status": "generated",
        "filename": str(draft_data.get("filename") or "sample.pdf"),
        "extracted_data": extracted_data,
        "template_spec": spec.model_dump(),
        "suggested_description": describe_template_spec(spec),
        "preview_html": preview_html,
    }


@app.post("/api/template-drafts/{draft_id}/save")
async def save_template_draft(draft_id: str, request: SaveTemplateDraftRequest):
    """Persist a validated generated draft as a user template package without registry registration."""
    try:
        normalized_draft_id = str(uuid.UUID(draft_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Template draft was not found.") from exc

    spec_path = TEMPLATE_DRAFT_DIR / normalized_draft_id / "template_spec.json"
    if not spec_path.is_file():
        raise HTTPException(status_code=404, detail="Generated template draft was not found.")
    try:
        spec = validate_template_spec(json.loads(spec_path.read_text(encoding="utf-8")))
        name = validate_template_name(request.template_name)
        description = validate_template_description(request.description)
        saved = save_user_template(USER_TEMPLATES_DIR, spec, name, description, TEMPLATE_DRAFT_DIR / normalized_draft_id)
        _reload_template_registry()
        return saved
    except (OSError, json.JSONDecodeError, TemplateSpecValidationError) as exc:
        raise HTTPException(status_code=422, detail="Generated template specification is invalid.") from exc
    except UserTemplateValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Template draft save failed for %s: %s", normalized_draft_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to save the template. Please try again.") from exc


def _user_template_detail(template_id: str) -> tuple[dict, Any, Path]:
    try:
        return load_user_template(USER_TEMPLATES_DIR, template_id)
    except UserTemplateValidationError as exc:
        raise HTTPException(status_code=404, detail="User template was not found.") from exc


@app.get("/api/user-templates/{template_id}")
async def get_user_template(template_id: str):
    manifest, spec, package = _user_template_detail(template_id)
    return {"template_id": template_id, "display_name": manifest["display_name"], "description": manifest["description"], "template_spec": spec.model_dump(), "has_source": (package / "original.pdf").is_file()}


@app.put("/api/user-templates/{template_id}")
async def update_saved_user_template(template_id: str, request: UpdateUserTemplateRequest):
    _user_template_detail(template_id)
    try:
        result = update_user_template(USER_TEMPLATES_DIR, template_id, validate_template_spec(request.template_spec), validate_template_name(request.template_name), validate_template_description(request.description))
        _reload_template_registry()
        return result
    except (TemplateSpecValidationError, UserTemplateValidationError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.delete("/api/user-templates/{template_id}")
async def delete_saved_user_template(template_id: str):
    _user_template_detail(template_id)
    try:
        delete_user_template(USER_TEMPLATES_DIR, template_id)
        _reload_template_registry()
    except UserTemplateValidationError as exc:
        raise HTTPException(status_code=404, detail="User template was not found.") from exc
    return {"template_id": template_id, "status": "deleted"}


@app.post("/api/user-templates/{template_id}/regenerate")
async def regenerate_user_template(template_id: str):
    manifest, _, package = _user_template_detail(template_id)
    source = package / "original.pdf"
    if not source.is_file():
        raise HTTPException(status_code=409, detail="This template has no retained sample PDF for regeneration.")
    try:
        raw_text = extract_text(str(source), "pdf")
        extracted = ResumeAdapter.to_legacy(normalise_resume(ResumeAdapter.adapt_regex_output(parse_resume(str(source), "pdf")), raw_text=raw_text))
        spec = validate_template_spec(await asyncio.wait_for(run_in_threadpool(generate_template_spec, extracted), timeout=95))
        preview = render_template_draft_preview(ResumeAdapter.from_legacy(extracted), spec)
        (package / "regeneration_spec.json").write_text(json.dumps(spec.model_dump(), indent=2), encoding="utf-8")
        (package / "regeneration_preview.html").write_text(preview, encoding="utf-8")
        return {"template_id": template_id, "display_name": manifest["display_name"], "template_spec": spec.model_dump(), "preview_html": preview, "status": "regenerated"}
    except (ai_parser.ProviderUnavailableError, asyncio.TimeoutError):
        raise HTTPException(status_code=503, detail="Template regeneration is currently unavailable. Please try again.")
    except Exception as exc:
        logger.error("Template regeneration failed for %s: %s", template_id, exc, exc_info=True)
        raise HTTPException(status_code=422, detail="Unable to generate a new template draft.") from exc


@app.post("/api/user-templates/{template_id}/regenerate/confirm")
async def confirm_user_template_regeneration(template_id: str):
    _, _, package = _user_template_detail(template_id)
    candidate = package / "regeneration_spec.json"
    if not candidate.is_file():
        raise HTTPException(status_code=404, detail="Regenerated template draft was not found.")
    try:
        spec = validate_template_spec(json.loads(candidate.read_text(encoding="utf-8")))
        (package / "template-spec.json").write_text(json.dumps(spec.model_dump(), indent=2), encoding="utf-8")
        candidate.unlink(missing_ok=True)
        (package / "regeneration_preview.html").unlink(missing_ok=True)
        _reload_template_registry()
    except (OSError, json.JSONDecodeError, TemplateSpecValidationError) as exc:
        raise HTTPException(status_code=422, detail="Regenerated template specification is invalid.") from exc
    return {"template_id": template_id, "status": "updated"}


@app.delete("/api/user-templates/{template_id}/regenerate")
async def cancel_user_template_regeneration(template_id: str):
    _, _, package = _user_template_detail(template_id)
    (package / "regeneration_spec.json").unlink(missing_ok=True)
    (package / "regeneration_preview.html").unlink(missing_ok=True)
    return {"template_id": template_id, "status": "cancelled"}


@app.post("/api/upload")
async def upload_resume(file: UploadFile = File(...), llm_model: str = Form("auto")):
    """
    Accept a resume file (PDF / DOCX / DOC), parse it, generate both
    Kanini templates, and return structured data + HTML previews.
    """
    filename = file.filename or ""
    if not _allowed_file(filename):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Read file content and check size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 10 MB).")

    # Generate session
    session_id = str(uuid.uuid4())

    # Save uploaded file
    ext = filename.rsplit(".", 1)[1].lower()
    session_dir = TEMP_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    upload_path = session_dir / f"original.{ext}"
    upload_path.write_bytes(content)

    # Parse resume — use AI when API key is configured, fall back to regex parser
    try:
        raw_text = extract_text(str(upload_path), ext)
    except Exception:
        shutil.rmtree(session_dir, ignore_errors=True)
        raise HTTPException(status_code=422, detail=INVALID_RESUME_MSG)

    if not raw_text or not raw_text.strip():
        shutil.rmtree(session_dir, ignore_errors=True)
        raise HTTPException(status_code=422, detail=INVALID_RESUME_MSG)

    resume_data = None
    regex_data = None
    selected_llm_model = ai_parser.normalise_selected_model(llm_model)
    strict_selected_model = str(llm_model or "").strip().lower() != "auto"
    llm_used = ""

    # PDFs are more layout-noisy after extraction, so run regex parse too and
    # select better sections instead of trusting one parser blindly.
    if ext == "pdf":
        try:
            regex_data = ResumeAdapter.to_legacy(
                ResumeAdapter.adapt_regex_output(parse_resume(str(upload_path), ext))
            )
        except Exception:
            regex_data = None

    has_ai_provider = ai_parser.has_configured_provider()

    # In auto mode we still require at least one AI provider. In strict mode,
    # we degrade gracefully to regex parsing when a selected model is unavailable.
    if not strict_selected_model and not has_ai_provider:
        shutil.rmtree(session_dir, ignore_errors=True)
        raise HTTPException(
            status_code=503,
            detail="No AI service is available. Configure Ollama via OLLAMA_BASE_URL or OLLAMA_HOST.",
        )

    try:
        resume_data, llm_used = ai_parser.parse_resume_with_ai(raw_text, llm_model)
        resume_data = ResumeAdapter.to_legacy(ResumeAdapter.adapt_ai_output(resume_data))
    except Exception as ai_err:
        print(f"[AI parser fallback] {ai_err}")
        llm_used = "regex"
        resume_data = None

    if resume_data is None:
        try:
            resume_data = regex_data if regex_data is not None else ResumeAdapter.to_legacy(
                ResumeAdapter.adapt_regex_output(parse_resume(str(upload_path), ext))
            )
        except Exception:
            shutil.rmtree(session_dir, ignore_errors=True)
            raise HTTPException(status_code=422, detail=INVALID_RESUME_MSG)

    if ext == "pdf":
        _log_pdf_debug(
            "ai_or_primary_before_blend",
            raw_text,
            resume_data,
            regex_data=None,
            session_id=session_id,
            filename=filename,
        )
        if regex_data is not None:
            _log_pdf_debug(
                "regex_before_blend",
                raw_text,
                regex_data,
                regex_data=None,
                session_id=session_id,
                filename=filename,
            )

    # PDF-only hybrid correction: choose cleaner skills/experience sections.
    # In strict selected-model mode, keep model output as authoritative and skip
    # regex hybrid override so template reflects the chosen model's parse.
    apply_pdf_hybrid = (
        ext == "pdf"
        and regex_data is not None
        and resume_data is not None
        and not (strict_selected_model and llm_used != "regex")
    )

    if apply_pdf_hybrid:
        try:
            resume_data = _pick_better_pdf_sections(resume_data, regex_data)
            _log_pdf_debug(
                "after_hybrid",
                raw_text,
                resume_data,
                regex_data=regex_data,
                session_id=session_id,
                filename=filename,
            )
        except Exception as blend_err:
            print(f"[PDF hybrid parse warning] {blend_err}")

    canonical_resume = normalise_resume(ResumeAdapter.from_legacy(resume_data), raw_text=raw_text)
    resume_data = ResumeAdapter.to_legacy(canonical_resume)
    _enrich_experience_with_company_sectors(resume_data, raw_text=raw_text)
    if ext == "pdf":
        _log_pdf_debug(
            "after_normalise",
            raw_text,
            resume_data,
            regex_data=regex_data,
            session_id=session_id,
            filename=filename,
        )
    canonical_resume = normalise_resume(ResumeAdapter.from_legacy(resume_data))
    is_valid, invalid_reason = validate_resume(canonical_resume, raw_text)
    resume_data = ResumeAdapter.to_legacy(canonical_resume)
    _ensure_resume_name(resume_data, filename)
    if not is_valid:
        print(f"[upload rejected] reason={invalid_reason}")
        shutil.rmtree(session_dir, ignore_errors=True)
        raise HTTPException(status_code=422, detail=f"Resume upload is invalid: {invalid_reason}")

    template_resume_data = _anonymise_resume_for_template(resume_data)

    try:
        artifacts = _generate_session_artifacts(session_id, template_resume_data, filename)
    except Exception:
        shutil.rmtree(session_dir, ignore_errors=True)
        raise HTTPException(status_code=422, detail=INVALID_RESUME_MSG)

    # Store session
    SESSIONS[session_id] = {
        "resume_data": artifacts["resume_data"],
        "review_data": resume_data,
        "files": artifacts["files"],
        "filename": filename,
    }

    _persist_resume(session_id, resume_data, filename)

    return JSONResponse({
        "session_id": session_id,
        "resume_data": artifacts["resume_data"],
        "llm_requested": selected_llm_model,
        "llm_used": llm_used,
        "preview_html": artifacts["preview_html"],
    })


@app.post("/api/skills-only")
async def upload_resume_skills_only(file: UploadFile = File(...)):
    """Accept a resume file and return only the parsed skill set."""
    filename = file.filename or ""
    if not _allowed_file(filename):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    content = await file.read()
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 10 MB).")

    ext = filename.rsplit(".", 1)[1].lower()
    session_id = str(uuid.uuid4())
    session_dir = TEMP_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    upload_path = session_dir / f"skills_only_original.{ext}"

    try:
        upload_path.write_bytes(content)
        skills = parse_skill_set(str(upload_path), ext)
    except Exception:
        raise HTTPException(status_code=422, detail=INVALID_RESUME_MSG)
    finally:
        shutil.rmtree(session_dir, ignore_errors=True)

    return JSONResponse({
        "filename": filename,
        "skills": skills,
    })


@app.get("/api/resumes")
async def list_saved_resumes():
    """List all resumes stored in the vector database."""
    resumes = vector_store.list_resumes()
    return {"resumes": resumes, "count": len(resumes)}


@app.get("/api/resumes/search")
async def search_saved_resumes(q: str = "", n_results: int = 5):
    """Semantic search across stored resumes."""
    results = vector_store.search_resumes(q, n_results=n_results)
    return {"results": results, "count": len(results)}


@app.get("/api/resumes/{resume_id}")
async def get_saved_resume(resume_id: str):
    """Load a stored resume and regenerate both template outputs."""
    resume_data = vector_store.get_resume(resume_id)
    if not resume_data:
        raise HTTPException(status_code=404, detail="Resume not found.")

    try:
        _enrich_experience_with_company_sectors(resume_data)
        template_resume_data = _anonymise_resume_for_template(resume_data)
        artifacts = _generate_session_artifacts(resume_id, template_resume_data)
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to regenerate resume templates.")

    SESSIONS[resume_id] = {
        "resume_data": artifacts["resume_data"],
        "review_data": resume_data,
        "files": artifacts["files"],
        "filename": artifacts.get("filename", ""),
    }

    return JSONResponse({
        "session_id": resume_id,
        "resume_data": artifacts["resume_data"],
        "selected_template_id": resume_data.get("selected_template_id", ""),
        "preview_html": artifacts["preview_html"],
    })


def _get_review_session(session_id: str) -> Dict[str, Any]:
    session = SESSIONS.get(session_id)
    if not session or not isinstance(session.get("review_data"), dict):
        raise HTTPException(status_code=404, detail="Review session not found or expired.")
    return session


@app.get("/api/resumes/{session_id}/review")
async def get_review_data(session_id: str):
    """Return only the canonical editable data for an active upload session."""
    session = _get_review_session(session_id)
    return {"session_id": session_id, "resume_data": ResumeAdapter.from_legacy(session["review_data"]).model_dump()}


@app.put("/api/resumes/{session_id}/review")
async def update_review_data(session_id: str, resume: ResumeData):
    """Persist user-reviewed data and regenerate the current session artifacts."""
    session = _get_review_session(session_id)
    reviewed = normalise_resume(resume)
    is_valid, reason = validate_resume(reviewed)
    if not is_valid:
        raise HTTPException(status_code=422, detail=f"Invalid reviewed resume: {reason}")
    full_data = ResumeAdapter.to_legacy(reviewed)
    previous = session.get("review_data") if isinstance(session.get("review_data"), dict) else {}
    full_data["additional_sections"] = previous.get("additional_sections", {})
    for index, experience in enumerate(full_data.get("experience", [])):
        if index < len(previous.get("experience", [])) and isinstance(previous["experience"][index], dict):
            existing = previous["experience"][index]
            experience["location"] = existing.get("location", experience.get("location", ""))
            experience["company_sector"] = existing.get("company_sector", experience.get("company_sector", ""))
    full_data["selected_template_id"] = previous.get("selected_template_id", "")
    _ensure_resume_name(full_data, session.get("filename", ""))
    try:
        artifacts = _generate_session_artifacts(session_id, _anonymise_resume_for_template(full_data), session.get("filename", ""))
    except Exception as exc:
        logger.error("review regeneration failed for %s: %s", session_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to regenerate resume artifacts.") from exc
    session.update({"review_data": full_data, "resume_data": artifacts["resume_data"], "files": artifacts["files"]})
    _persist_resume(session_id, full_data, session.get("filename", ""))
    return {"session_id": session_id, "resume_data": artifacts["resume_data"], "preview_html": artifacts["preview_html"]}


@app.put("/api/resumes/{session_id}/template")
async def update_selected_template(session_id: str, request: SelectedTemplateRequest):
    session = _get_review_session(session_id)
    try:
        template = TEMPLATE_REGISTRY.get(request.template_id)
    except TemplateNotFoundError as exc:
        raise HTTPException(status_code=400, detail="Selected template is unavailable. Please choose another template.") from exc
    full_data = dict(session["review_data"])
    full_data["selected_template_id"] = template.id
    session["review_data"] = full_data
    _persist_resume(session_id, full_data, session.get("filename", ""))
    return {"session_id": session_id, "template_id": template.id}


@app.post("/api/resumes/{session_id}/render")
async def render_reviewed_resume(session_id: str, request: RenderRequest):
    """Resolve a selected template through the registry and return its preview/download reference."""
    session = _get_review_session(session_id)
    try:
        template = TEMPLATE_REGISTRY.get(request.template_id)
    except TemplateNotFoundError as exc:
        raise HTTPException(status_code=400, detail="Invalid template ID.") from exc
    if not template.enabled or request.output_format not in template.supported_outputs:
        raise HTTPException(status_code=400, detail="Requested template output is unavailable.")
    alias = template.aliases[0] if template.aliases else template.id
    if request.output_format == "html":
        html_generator = RENDERER_FACTORY.get(template.id).render_html
        preview = html_generator(ResumeAdapter.from_legacy(session["resume_data"])).content or ""
        return {"session_id": session_id, "template_id": template.id, "output_format": "html", "preview_html": preview}
    return {"session_id": session_id, "template_id": template.id, "output_format": request.output_format, "download_url": f"/api/download/{session_id}/{alias}/{request.output_format}"}


@app.delete("/api/resumes/{resume_id}")
async def delete_saved_resume(resume_id: str):
    """Delete a stored resume and any generated session artifacts."""
    if not vector_store.get_resume(resume_id):
        raise HTTPException(status_code=404, detail="Resume not found.")

    vector_store.delete_resume(resume_id)
    session_dir = TEMP_DIR / resume_id
    shutil.rmtree(session_dir, ignore_errors=True)
    SESSIONS.pop(resume_id, None)
    return {"status": "deleted", "resume_id": resume_id}


@app.get("/api/download/{session_id}/{template_id}/{fmt}")
async def download_file(session_id: str, template_id: str, fmt: str):
    """
    Download a generated template.
    template_id: template1 | template2
    fmt: docx | pdf
    """
    if session_id not in SESSIONS:
        # Recover session artifacts from persisted resume so downloads continue
        # to work even after backend restarts.
        stored_resume = vector_store.get_resume(session_id)
        if stored_resume:
            try:
                _enrich_experience_with_company_sectors(stored_resume)
                template_resume_data = _anonymise_resume_for_template(stored_resume)
                artifacts = _generate_session_artifacts(session_id, template_resume_data)
                SESSIONS[session_id] = {
                    "resume_data": artifacts["resume_data"],
                    "files": artifacts["files"],
                    "filename": "",
                }
            except Exception as exc:
                logger.warning("download session regeneration failed for %s: %s", session_id, exc)
                raise HTTPException(status_code=404, detail="Session not found or expired.")
        else:
            raise HTTPException(status_code=404, detail="Session not found or expired.")

    try:
        template = TEMPLATE_REGISTRY.get(template_id)
    except TemplateNotFoundError as exc:
        raise HTTPException(status_code=400, detail="Invalid template ID.") from exc

    if fmt not in template.supported_outputs:
        raise HTTPException(status_code=400, detail=f"Template does not support '{fmt}' output.")

    # Generated artifacts retain legacy keys until renderer migration.
    template_id = template.aliases[0] if template.aliases else template.id

    session = SESSIONS[session_id]
    raw_candidate_name = str(session.get("resume_data", {}).get("contact", {}).get("name", "") or "").strip()
    candidate_name = _safe_filename_component(raw_candidate_name, "resume")
    template_name = _safe_filename_component(_template_download_name(template_id), "template")
    if not template.user_created:
        candidate_name = candidate_name.lower()
    download_stem = f"{candidate_name}_{template_name}" if template.user_created else f"{template_name}_{candidate_name}"

    if fmt == "html":
        try:
            content = RENDERER_FACTORY.get(template.id).render_html(ResumeAdapter.from_legacy(session["resume_data"])).content or ""
        except Exception as exc:
            logger.error("HTML download rendering failed for session=%s: %s", session_id, exc, exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to generate HTML.") from exc
        return HTMLResponse(content=content, headers={"Content-Disposition": f'attachment; filename="{download_stem}.html"'})

    docx_key = f"{template_id}_docx"
    docx_path = session["files"].get(docx_key)

    canonical_resume = ResumeAdapter.from_legacy(session["resume_data"])
    renderer = RENDERER_FACTORY.get(template.id)
    session_dir = TEMP_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    if fmt == "docx" and (not docx_path or not os.path.exists(docx_path)):
        docx_path = str(session_dir / ("kanini_classic.docx" if template_id == "template1" else "deloitte_format.docx" if template_id == "template2" else f"{template_id}.docx"))
        try:
            renderer.render_docx(canonical_resume, Path(docx_path))
        except Exception as exc:
            logger.error("DOCX generation failed for session=%s: %s", session_id, exc, exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to generate DOCX.") from exc
        session["files"][docx_key] = docx_path

    if fmt == "docx":
        return FileResponse(
            path=docx_path,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=f"{download_stem}.docx",
        )

    pdf_key = f"{template_id}_pdf"
    pdf_path = session["files"].get(pdf_key)

    if not pdf_path or not os.path.exists(pdf_path):
        try:
            pdf_path = str(session_dir / ("kanini_classic.pdf" if template_id == "template1" else "deloitte_format.pdf" if template_id == "template2" else f"{template_id}.pdf"))
            result = await asyncio.wait_for(run_in_threadpool(renderer.render_pdf, canonical_resume, Path(pdf_path).with_suffix(".tex")), timeout=90)
            pdf_path = str(result.path)
            session["files"][pdf_key] = pdf_path
            logger.info("PDF generated on demand for session=%s template=%s", session_id, template_id)
        except asyncio.TimeoutError:
            logger.warning("HTML-to-PDF timed out for session=%s template=%s", session_id, template_id)
            raise HTTPException(status_code=504, detail="PDF generation timed out. Please try again.")
        except Exception as e:
            logger.error("HTML-to-PDF failed for session=%s template=%s: %s", session_id, template_id, e, exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to generate PDF.")

    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=f"{download_stem}.pdf",
    )


@app.delete("/api/session/{session_id}")
async def delete_session(session_id: str):
    """Clean up session files."""
    if session_id in SESSIONS:
        session_dir = TEMP_DIR / session_id
        shutil.rmtree(session_dir, ignore_errors=True)
        del SESSIONS[session_id]
    try:
        vector_store.delete_resume(session_id)
    except Exception:
        pass
    return {"status": "deleted"}


# Serve Angular build when available. Keep mounted after API routes so /api/* stays intact.
_frontend_dir = _frontend_dist_dir()
if _frontend_dir is not None:
    app.mount("/", StaticFiles(directory=str(_frontend_dir), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=os.getenv("UVICORN_HOST", "127.0.0.1"),
        port=8000,
        reload=os.getenv("UVICORN_RELOAD", "0").strip().lower() in {"1", "true", "yes", "on"},
    )
