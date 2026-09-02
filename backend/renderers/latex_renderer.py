from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .base import LatexUnavailableError, RenderResult, RendererError

_ESCAPES = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def escape_latex(value: object) -> str:
    """Escape only candidate-controlled text before it enters LaTeX source."""
    return "".join(_ESCAPES.get(character, character) for character in str(value or ""))


class XeLatexCompiler:
    def compile(self, tex_path: Path) -> RenderResult:
        executable = shutil.which("xelatex")
        if not executable:
            raise LatexUnavailableError(
                "XeLaTeX is not available. Install MiKTeX/XeLaTeX or configure the executable path."
            )
        try:
            process = subprocess.run(
                [executable, "-interaction=nonstopmode", "-halt-on-error", tex_path.name],
                cwd=tex_path.parent,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=90,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise RendererError("XeLaTeX compilation timed out.") from exc
        pdf_path = tex_path.with_suffix(".pdf")
        if process.returncode or not pdf_path.exists() or pdf_path.stat().st_size == 0:
            diagnostic = (process.stderr or process.stdout or "XeLaTeX failed.")[-2000:]
            raise RendererError("Format 1 LaTeX rendering failed: " + diagnostic)
        return RenderResult("kanini-format-1", "pdf", path=pdf_path, diagnostics=process.stdout[-1000:])