"""
AI-powered resume parser — uses Ollama to extract structured data.
Falls back gracefully so the caller can switch to the regex parser.
"""
import json
import os
import re
from typing import Any, Callable, Dict, List

try:
    from dotenv import load_dotenv
    load_dotenv(override=False)          # load .env only if not already in environ
except ImportError:
    pass


# ─── Provider configuration ───────────────────────────────────────────────────

_DEFAULT_OLLAMA_MODEL = "llama3.1"
_DEFAULT_PROVIDER_PRIORITY = ["ollama"]


class ProviderUnavailableError(RuntimeError):
    """Raised when a provider is not configured or cannot be used locally."""


def _default_model_for(provider: str) -> str:
    provider = str(provider or "").strip().lower()
    if provider == "ollama":
        return os.getenv("OLLAMA_MODEL", _DEFAULT_OLLAMA_MODEL).strip() or _DEFAULT_OLLAMA_MODEL
    return ""


def _get_provider_priority() -> List[str]:
    raw = os.getenv("AI_PROVIDER_PRIORITY", ",".join(_DEFAULT_PROVIDER_PRIORITY))
    ordered: List[str] = []
    for item in raw.split(","):
        provider = item.strip().lower()
        if provider and provider not in ordered and provider in _DEFAULT_PROVIDER_PRIORITY:
            ordered.append(provider)
    return ordered or list(_DEFAULT_PROVIDER_PRIORITY)


def _has_ollama_config() -> bool:
    return bool(os.getenv("OLLAMA_HOST") or os.getenv("OLLAMA_BASE_URL") or os.getenv("OLLAMA_MODEL"))


def get_configured_models() -> List[str]:
    configured: List[str] = []
    for provider in _get_provider_priority():
        if provider == "ollama" and _has_ollama_config():
            configured.append(f"ollama:{_default_model_for('ollama')}")
    return configured


def has_configured_provider() -> bool:
    return bool(get_configured_models())


def is_provider_configured(provider: str) -> bool:
    provider_key = str(provider or "").strip().lower()
    if provider_key == "ollama":
        return _has_ollama_config()
    return False


def get_model_dropdown_options() -> List[Dict[str, Any]]:
    """Return frontend-ready model options with availability status."""
    provider_labels = {
        "ollama": "Ollama",
    }

    options: List[Dict[str, Any]] = []
    options.append(
        {
            "label": "Auto (configured provider)",
            "value": "auto",
            "available": has_configured_provider(),
            "reason": "Configure at least one provider key" if not has_configured_provider() else "",
            "provider": "auto",
        }
    )

    candidates = [
        ("ollama", "qwen3:32b", "Qwen3 32B"),
        ("ollama", "qwen3:14b", "Qwen3 14B"),
        ("ollama", "llama3.3:70b", "Llama 3.3 70B"),
        ("ollama", "devstral", "Devstral"),
        ("ollama", "gemma3:27b", "Gemma 3 27B"),
        ("ollama", "mistral-small3.2", "Mistral Small 3.2"),
        ("ollama", _default_model_for("ollama"), "Ollama (local)"),
    ]

    for provider, model, label in candidates:
        available = is_provider_configured(provider)
        options.append(
            {
                "label": label,
                "value": f"{provider}:{model}",
                "available": available,
                "reason": "Provider is not configured" if not available else "",
                "provider": provider,
                "provider_label": provider_labels.get(provider, provider),
            }
        )

    return options


def is_model_configured(llm_model: str | None) -> bool:
    provider, model = _split_llm_model(llm_model)
    if provider == "auto":
        return has_configured_provider()
    return is_provider_configured(provider)


def _split_llm_model(llm_model: str | None) -> tuple[str, str]:
    raw = str(llm_model or "auto").strip().lower()
    if not raw or raw == "auto":
        auto_models = get_configured_models()
        if auto_models:
            provider, model = auto_models[0].split(":", 1)
            return provider, model
        return "auto", ""
    if ":" in raw:
        provider, model = raw.split(":", 1)
        provider = provider.strip()
        model = model.strip()
        if provider and model:
            return provider, model
    # Plain model names default to Ollama.
    return "ollama", raw


def normalise_selected_model(llm_model: str | None) -> str:
    if str(llm_model or "").strip().lower() == "auto":
        return "auto"
    provider, model = _split_llm_model(llm_model)
    return f"{provider}:{model}"

def is_available() -> bool:
    """Return True when any configured AI provider is available for auto-selection."""
    return has_configured_provider()


# ─── Prompt ──────────────────────────────────────────────────────────────────

_SYSTEM = """\
You are an expert resume parser. Read the entire resume carefully and extract
every piece of information into the JSON structure below.

=== STRICT FIELD RULES ===

contact.name
  - The candidate's FULL NAME — usually the very FIRST non-empty line of the resume.
  - It is a person's name (e.g. "Indira Eswaran", "John Smith").
  - NEVER leave this empty. NEVER put it in the summary field.

contact.email / contact.phone / contact.location / contact.linkedin / contact.github
  - Contact details found near the top of the resume (header area).
  - email: text containing @
  - phone: digits, spaces, +, -, ()
  - location: city, state, country
  - linkedin / github: URLs or profile handles

summary
  - ONLY the career summary / professional profile / objective paragraph(s).
  - Must NOT contain the candidate's name, phone, email, or any heading label.
  - Must NOT contain skills lists or bullet points — only prose narrative text.

skills
  - A dictionary of { "Category": ["skill1", "skill2", ...] }
  - Group logically: "Programming Languages", "Frameworks & Libraries",
    "Databases", "Cloud & DevOps", "Tools", "Soft Skills", etc.
  - If no clear grouping exists in the resume, use a single key "Technical Skills".
    - NEVER include company names, job titles/designations, project names, durations,
        locations, or sentence fragments from Work Experience.
    - NEVER include section labels as skills (e.g., "Company Name", "Designation",
        "Duration", "Responsibilities", "Project-I", "Project-II").
    - Skills must be atomic terms only (examples: "C#", "ASP.NET Web API", "ReactJS",
        "SQL Server", "MS Visual Studio", "Windows XP").

experience
  - Array of jobs, each with:
      title      : job title / designation
      company    : employer / organisation name
      location   : city or country (empty string if absent)
      dates      : duration exactly as written (e.g. "Jan 2022 – Present")
      responsibilities : array of bullet point strings, verbatim
    - IMPORTANT: Keep title and company in the correct fields. Do NOT swap them.
    - Do NOT output labels as values. Wrong examples:
            title="Company Name", company="Designation"
            title="Duration", company="Company Name"
    - If the resume uses table-like rows where labels and values are split across lines,
        pair them correctly:
            Company Name -> actual employer value
            Designation/Role/Position -> actual job title value
            Duration -> actual date range value
    - If one field is unknown, keep it "". Never copy another field's label as fallback.

education
  - Array of qualifications, each with:
      degree      : qualification name
      institution : university / college / school name
      year        : year of completion (e.g. "2020")
      gpa         : GPA or percentage (empty string if absent)

certifications  — flat list of certification strings
projects        — array of { name, description, technologies: [] }
achievements    — flat list of achievement strings

=== OUTPUT FORMAT ===
Return ONLY this JSON (no markdown, no extra text):
{
  "contact":        {"name":"","email":"","phone":"","location":"","linkedin":"","github":""},
  "summary":        "",
  "skills":         {"Category": ["skill1","skill2"]},
  "experience":     [{"title":"","company":"","location":"","dates":"","responsibilities":[]}],
  "education":      [{"degree":"","institution":"","year":"","gpa":""}],
  "certifications": [],
  "projects":       [{"name":"","description":"","technologies":[]}],
  "achievements":   []
}

=== FINAL SELF-CHECK (MANDATORY BEFORE RETURNING JSON) ===
1) In every experience item:
     - title must look like a role/designation, not a company.
     - company must look like an employer, not a role label.
     - title/company cannot be any of these labels: Company Name, Designation,
         Role, Position, Duration, Responsibilities.
2) skills must NOT contain:
     - company names, job titles, duration strings, or project labels.
     - long sentence fragments from experience/project descriptions.
3) If a value is uncertain, return "" instead of copying a label.
"""


# ─── Public entry point ───────────────────────────────────────────────────────

def _build_user_prompt(raw_text: str) -> str:
    return f"Parse this resume completely:\n\n{raw_text[:14000]}"


def _parse_with_openai(raw_text: str, model: str) -> Dict:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise ProviderUnavailableError("openai package not installed") from exc

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ProviderUnavailableError("OPENAI_API_KEY is not configured")

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": _build_user_prompt(raw_text)},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    raw = json.loads(response.choices[0].message.content)
    return _normalise(raw, raw_text)


def _parse_with_azure_openai(raw_text: str, model: str) -> Dict:
    try:
        from openai import AzureOpenAI
    except ImportError as exc:
        raise ProviderUnavailableError("openai package with Azure support is not installed") from exc

    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    azure_ad_token = os.getenv("AZURE_OPENAI_AD_TOKEN")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")

    if not endpoint:
        raise ProviderUnavailableError("AZURE_OPENAI_ENDPOINT is not configured")
    if not (api_key or azure_ad_token):
        raise ProviderUnavailableError("AZURE_OPENAI_API_KEY or AZURE_OPENAI_AD_TOKEN is required")

    kwargs: Dict[str, Any] = {
        "api_version": api_version,
        "azure_endpoint": endpoint,
    }
    if api_key:
        kwargs["api_key"] = api_key
    else:
        kwargs["azure_ad_token"] = azure_ad_token

    client = AzureOpenAI(**kwargs)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": _build_user_prompt(raw_text)},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    raw = json.loads(response.choices[0].message.content)
    return _normalise(raw, raw_text)


def _parse_with_anthropic(raw_text: str, model: str) -> Dict:
    try:
        import importlib
        anthropic_mod = importlib.import_module("anthropic")
        Anthropic = getattr(anthropic_mod, "Anthropic")
    except ImportError as exc:
        raise ProviderUnavailableError("anthropic package not installed") from exc

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ProviderUnavailableError("ANTHROPIC_API_KEY is not configured")

    client = Anthropic(api_key=api_key)
    response = client.messages.create(
        model=model,
        system=_SYSTEM,
        messages=[
            {"role": "user", "content": _build_user_prompt(raw_text)},
        ],
        max_tokens=4096,
        temperature=0,
    )

    text_content = ""
    for block in response.content:
        if getattr(block, "type", "") == "text":
            text_content += getattr(block, "text", "")

    if not text_content.strip():
        raise RuntimeError("Anthropic response was empty")

    raw = json.loads(text_content)
    return _normalise(raw, raw_text)


def _parse_with_gemini(raw_text: str, model: str) -> Dict:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ProviderUnavailableError("GEMINI_API_KEY is not configured")

    try:
        import importlib
        genai = importlib.import_module("google.genai")
    except ImportError as exc:
        raise ProviderUnavailableError("google-genai package not installed") from exc

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents=[_SYSTEM, _build_user_prompt(raw_text)],
        config={"response_mime_type": "application/json", "temperature": 0},
    )
    text_content = getattr(response, "text", "") or ""
    if not text_content.strip():
        raise RuntimeError("Gemini response was empty")
    raw = json.loads(text_content)
    return _normalise(raw, raw_text)


def _parse_with_ollama(raw_text: str, model: str) -> Dict:
    import urllib.error
    import urllib.request

    base_url = (os.getenv("OLLAMA_BASE_URL") or os.getenv("OLLAMA_HOST") or "").strip().rstrip("/")
    if not base_url:
        raise ProviderUnavailableError("OLLAMA_BASE_URL or OLLAMA_HOST is not configured")

    payload = json.dumps({
        "model": model,
        "prompt": f"{_SYSTEM}\n\n{_build_user_prompt(raw_text)}",
        "stream": False,
        "format": "json",
        "options": {"temperature": 0},
    }).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise ProviderUnavailableError(f"Ollama request failed: {exc}") from exc

    text_content = str(body.get("response") or "").strip()
    if not text_content:
        raise RuntimeError("Ollama response was empty")
    raw = json.loads(text_content)
    return _normalise(raw, raw_text)


_PROVIDER_HANDLERS: Dict[str, Callable[[str, str], Dict]] = {
    "ollama": _parse_with_ollama,
}


def parse_resume_with_ai(raw_text: str, llm_model: str = "auto") -> tuple[Dict, str]:
    """
    Parse *raw_text* (extracted from a PDF/DOCX) with the selected model.
    Returns (parsed_resume, provider:model_used).
    Raises RuntimeError when no configured provider can serve the request.
    """
    requested = str(llm_model or "auto").strip().lower()
    if requested in {"", "auto"}:
        candidates = get_configured_models()
        if not candidates:
            raise RuntimeError(
                "No AI service is available. Configure Ollama via OLLAMA_BASE_URL or OLLAMA_HOST."
            )
    else:
        candidates = [normalise_selected_model(llm_model)]

    errors: List[str] = []
    for candidate in candidates:
        provider, model = _split_llm_model(candidate)
        handler = _PROVIDER_HANDLERS.get(provider)
        if handler is None:
            errors.append(f"{candidate}: unsupported provider")
            if requested not in {"", "auto"}:
                break
            continue
        try:
            return handler(raw_text, model), f"{provider}:{model}"
        except ProviderUnavailableError as exc:
            errors.append(f"{candidate}: {exc}")
            if requested not in {"", "auto"}:
                raise RuntimeError(str(exc)) from exc
        except Exception as exc:
            errors.append(f"{candidate}: {exc}")
            if requested not in {"", "auto"}:
                raise RuntimeError(str(exc)) from exc

    if requested in {"", "auto"} and not candidates:
        raise RuntimeError(
            "No AI service is available. Configure Ollama via OLLAMA_BASE_URL or OLLAMA_HOST."
        )

    if requested in {"", "auto"}:
        raise RuntimeError("All configured AI providers failed: " + " | ".join(errors[:5]))
    raise RuntimeError(errors[0] if errors else "Selected AI provider failed")


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _s(v, default: str = "") -> str:
    return str(v).strip() if v else default


def _lst(v) -> List[str]:
    if isinstance(v, list):
        return [str(i).strip() for i in v if i and str(i).strip()]
    return []


def _unique_keep_order(items: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for item in items:
        key = item.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def _normalise_skills(skills_raw) -> Dict[str, List[str]]:
    """Merge duplicate categories, remove trailing colons, and dedupe skill entries."""
    merged: Dict[str, List[str]] = {}

    if isinstance(skills_raw, list):
        flat = _unique_keep_order(_lst(skills_raw))
        return {"Technical Skills": flat} if flat else {}

    if not isinstance(skills_raw, dict):
        return {}

    for raw_cat, raw_items in skills_raw.items():
        cat = str(raw_cat or "").strip().rstrip(":")
        if not cat:
            cat = "Technical Skills"

        items: List[str]
        if isinstance(raw_items, list):
            items = _lst(raw_items)
        elif isinstance(raw_items, str):
            items = [s.strip() for s in re.split(r",|\n|;", raw_items) if s.strip()]
        else:
            items = []

        if not items:
            continue

        # Merge categories case-insensitively while preserving first display form.
        canonical_key = None
        for existing in merged.keys():
            if existing.casefold() == cat.casefold():
                canonical_key = existing
                break
        if canonical_key is None:
            canonical_key = cat
            merged[canonical_key] = []

        merged[canonical_key].extend(items)

    for cat in list(merged.keys()):
        merged[cat] = _unique_keep_order([i.rstrip(":").strip() for i in merged[cat] if i.strip()])
        if not merged[cat]:
            del merged[cat]

    return merged


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


def _clean_exp_field(value) -> str:
    return _EXP_LABEL_PREFIX_RE.sub("", str(value or "").strip()).strip()


def _looks_like_role(text: str) -> bool:
    return bool(text and _ROLE_HINT_RE.search(text))


def _looks_like_company(text: str) -> bool:
    if not text:
        return False
    if _COMPANY_HINT_RE.search(text):
        return True
    words = [w for w in text.split() if w]
    return len(words) >= 2 and text[0].isupper() and not _looks_like_role(text)


def _split_title_company(text: str) -> tuple[str, str]:
    raw = str(text or "").strip()
    if not raw:
        return "", ""

    m = re.match(r"^(.+?)\s+(?:at|@)\s+(.+)$", raw, flags=re.IGNORECASE)
    if m:
        return m.group(1).strip(), m.group(2).strip()

    for sep in ("|", " - ", " – ", " — "):
        if sep in raw:
            parts = [p.strip() for p in raw.split(sep) if p.strip()]
            if len(parts) >= 2:
                return parts[0], parts[1]

    return raw, ""


def _normalise_experience_fields(title_raw, company_raw) -> tuple[str, str]:
    title = _clean_exp_field(title_raw)
    company = _clean_exp_field(company_raw)

    if title and not company:
        t, c = _split_title_company(title)
        if c:
            title, company = t, c
    elif company and not title:
        t, c = _split_title_company(company)
        if c:
            title, company = t, c

    if company and title:
        company_looks_role = _looks_like_role(company)
        title_looks_role = _looks_like_role(title)
        title_looks_company = _looks_like_company(title)
        company_looks_company = _looks_like_company(company)
        if company_looks_role and (not title_looks_role or (title_looks_company and not company_looks_company)):
            title, company = company, title

    return title, company


# Contact-info patterns used to scrub accidental leakage into summary
_CONTACT_RE = re.compile(
    r'(\b[\w.+-]+@[\w-]+\.[a-z]{2,}\b'          # email
    r'|\b(\+?\d[\d\s\-().]{6,15}\d)\b'          # phone
    r'|linkedin\.com/\S+'                        # linkedin url
    r'|github\.com/\S+)',                        # github url
    re.IGNORECASE,
)

# Looks like "John Smith" — 2-4 capitalised words, no digits/punct
_NAME_RE = re.compile(r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})$')


def _guess_name_from_text(raw_text: str) -> str:
    """Try to extract candidate name from the first non-empty lines."""
    for line in raw_text.splitlines():
        line = line.strip()
        if not line:
            continue
        # Skip lines that look like headings or contact info
        if _CONTACT_RE.search(line):
            continue
        if len(line) > 60:         # too long to be a name
            continue
        if any(kw in line.upper() for kw in (
            "RESUME", "CURRICULUM", "VITAE", "CV", "SUMMARY",
            "PROFILE", "OBJECTIVE", "SKILLS", "EXPERIENCE",
        )):
            continue
        # Accept all-caps name (e.g. "INDIRA ESWARAN") or Title Case
        words = line.split()
        if 2 <= len(words) <= 5 and all(re.match(r"[A-Za-z'-]+$", w) for w in words):
            return line.title()
    return ""


def _clean_summary(summary: str, name: str) -> str:
    """Remove candidate name / contact noise accidentally placed in summary."""
    if not summary:
        return summary
    lines = summary.splitlines()
    cleaned = []
    for line in lines:
        stripped = line.strip()
        # Drop lines that are just the candidate name
        if name and stripped.upper() == name.upper():
            continue
        # Drop lines that consist entirely of contact info
        if stripped and not re.sub(_CONTACT_RE, "", stripped).strip():
            continue
        # Drop lines that are clearly section headings leaked into summary
        if re.match(r'^(PROFESSIONAL SUMMARY|SUMMARY|PROFILE|OBJECTIVE)[:\s]*$',
                    stripped, re.IGNORECASE):
            continue
        # Remove accidental leading bullet markers from summary lines.
        cleaned.append(re.sub(r"^[\s\u2022\u2023\u25E6\u2043\u2219\-*]+\s*", "", line))
    return "\n".join(cleaned).strip()


# ─── Normaliser ──────────────────────────────────────────────────────────────

def _normalise(raw: Dict, raw_text: str = "") -> Dict:
    """Coerce AI output to the strict schema expected by template_generator."""
    c = raw.get("contact") or {}

    # ── Contact ──────────────────────────────────────────────────────────────
    name  = _s(c.get("name"))
    email = _s(c.get("email"))
    phone = _s(c.get("phone"))

    # If AI missed the name, try to extract it ourselves
    if not name:
        name = _guess_name_from_text(raw_text)

    # ── Skills ───────────────────────────────────────────────────────────────
    skills = _normalise_skills(raw.get("skills") or {})

    # ── Experience ───────────────────────────────────────────────────────────
    experience = []
    for e in (raw.get("experience") or []):
        if not isinstance(e, dict):
            continue
        title, company = _normalise_experience_fields(e.get("title"), e.get("company"))
        experience.append(
            {
                "title":            title,
                "company":          company,
                "location":         _s(e.get("location")),
                "dates":            _s(e.get("dates")),
                "responsibilities": _lst(e.get("responsibilities")),
            }
        )

    # ── Education ────────────────────────────────────────────────────────────
    education = [
        {
            "degree":      _s(e.get("degree")),
            "institution": _s(e.get("institution")),
            "year":        _s(e.get("year")),
            "gpa":         _s(e.get("gpa")),
        }
        for e in (raw.get("education") or [])
        if isinstance(e, dict)
    ]

    # ── Projects ─────────────────────────────────────────────────────────────
    projects = [
        {
            "name":         _s(p.get("name")),
            "description":  _s(p.get("description")),
            "technologies": _lst(p.get("technologies")),
        }
        for p in (raw.get("projects") or [])
        if isinstance(p, dict)
    ]

    # ── Summary — clean any name/contact leakage ──────────────────────────────
    summary = _clean_summary(_s(raw.get("summary")), name)

    return {
        "contact": {
            "name":     name,
            "email":    email,
            "phone":    phone,
            "location": _s(c.get("location")),
            "linkedin": _s(c.get("linkedin")),
            "github":   _s(c.get("github")),
        },
        "summary":        summary,
        "skills":         skills,
        "experience":     experience,
        "education":      education,
        "certifications": _lst(raw.get("certifications")),
        "projects":       projects,
        "achievements":   _lst(raw.get("achievements")),
    }
