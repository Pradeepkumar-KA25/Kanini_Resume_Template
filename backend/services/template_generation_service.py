from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any

import ai_parser


class TemplateGenerationError(RuntimeError):
    """Raised when Ollama cannot produce a usable template specification."""


_TEMPLATE_SPEC_PROMPT = """You design reusable professional resume templates.
Create a design inspired only by the sample's section organization and content structure.
Do not claim to copy its original visual layout: no font, color, spacing, or coordinate data was extracted.
Return only a valid JSON object matching this exact schema, with no markdown or explanation:

{
  "page": {
    "size": "A4",
    "orientation": "portrait",
    "margin_inches": 0.65
  },
  "typography": {
    "font_family": "Calibri",
    "base_size_pt": 10,
        "heading_size_pt": 12
  },
  "colors": {
    "text": "#1F2937",
    "accent": "#0072B4",
    "muted": "#64748B"
  },
  "header": {
    "layout": "centered",
    "contact_layout": "inline",
    "show_divider": true
  },
  "layout": {
    "columns": 1,
    "sidebar_position": "none",
    "section_alignment": "left"
  },
  "sections": [
    "summary",
    "skills",
    "experience",
    "projects",
    "education",
    "certifications",
    "achievements"
  ],
  "spacing": {
    "section_gap_pt": 12,
    "line_height": 1.35,
    "divider_style": "solid",
    "skill_style": "inline"
  }
}

Rules:
- Output JSON only.
- Do not include markdown.
- Do not include HTML.
- Do not include CSS.
- Do not include JavaScript.
- Do not include URLs.
- Do not include assets.
- Do not include executable code.
- Do not include resume content.
- sections must be an array of individual section names.
- Each section must be one of: summary, skills, experience, projects, education, certifications, achievements.
- Do not repeat sections.
- Include at least one section.
- margin_inches must be between 0.35 and 1.25.
- base_size_pt must be between 8 and 14.
- heading_size_pt must be between 12 and 24.
- heading_size_pt must be greater than base_size_pt.
- Colors must use exactly six-digit hexadecimal format such as #1F2937.
- font_family must be one of: Arial, Calibri, Georgia, Helvetica, Times New Roman.
- page size must be A4 or LETTER.
- orientation must be portrait.
- columns must be 1 or 2.
- If columns is 1, sidebar_position must be none.
- If columns is 2, sidebar_position must be left or right.
- section_alignment must be left or justified.
- section_gap_pt must be between 4 and 28.
- line_height must be between 1.0 and 1.8.
- divider_style must be none, solid, or accent.
- skill_style must be inline, bullets, or tags.
All headings must use the fixed 12pt, bold, black, uppercase style. Do not vary heading styling.

Sample resume structure:
"""


def generate_template_spec(extracted_data: dict[str, Any]) -> dict[str, Any]:
    """Ask the configured Ollama model for a non-executable TemplateSpec JSON object."""

    base_url = (
        os.getenv("OLLAMA_BASE_URL")
        or os.getenv("OLLAMA_HOST")
        or ""
    ).strip().rstrip("/")

    if not base_url:
        raise ai_parser.ProviderUnavailableError(
            "Ollama is not configured."
        )

    model = os.getenv("OLLAMA_MODEL", "llama3.1").strip() or "llama3.1"

    prompt = (
        _TEMPLATE_SPEC_PROMPT
        + json.dumps(
            extracted_data,
            ensure_ascii=False,
        )[:14000]
    )
    with open("template_debug_prompt.txt", "w", encoding="utf-8") as f:
      f.write(prompt)

    print("\n========== TEMPLATE GENERATION DEBUG ==========")
    print(f"Model: {model}")
    print(f"Prompt length: {len(prompt)} characters")
    print(f"Ollama URL: {base_url}/api/generate")
    print("Starting Ollama request...")

    payload = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0,
            },
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        f"{base_url}/api/generate",
        data=payload,
        headers={
            "Content-Type": "application/json",
        },
        method="POST",
    )

    start_time = time.time()

    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            elapsed = time.time() - start_time

            print(
                f"Ollama response received in: "
                f"{elapsed:.2f} seconds"
            )

            body = json.loads(
                response.read().decode("utf-8")
            )

    except urllib.error.URLError as exc:
        elapsed = time.time() - start_time

        print(
            f"Ollama request failed after: "
            f"{elapsed:.2f} seconds"
        )

        raise ai_parser.ProviderUnavailableError(
            "Ollama is unavailable. Check that the configured model is running."
        ) from exc

    except TimeoutError as exc:
        elapsed = time.time() - start_time

        print(
            f"Ollama TIMEOUT after: "
            f"{elapsed:.2f} seconds"
        )

        raise TemplateGenerationError(
            "Ollama timed out while generating the template."
        ) from exc

    response_text = str(
        body.get("response") or ""
    ).strip()

    print(
        f"Response length: "
        f"{len(response_text)} characters"
    )
    print("===============================================\n")

    if not response_text:
        raise TemplateGenerationError(
            "Ollama returned an empty template specification."
        )

    try:
        generated = json.loads(response_text)

    except json.JSONDecodeError as exc:
        raise TemplateGenerationError(
            "Ollama returned an invalid template specification."
        ) from exc

    if not isinstance(generated, dict):
        raise TemplateGenerationError(
            "Ollama returned an invalid template specification."
        )

    return generated