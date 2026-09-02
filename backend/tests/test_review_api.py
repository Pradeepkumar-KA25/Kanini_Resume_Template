import asyncio

import pytest
from fastapi import HTTPException

from main import SESSIONS, RenderRequest, download_file, get_review_data, render_reviewed_resume, update_review_data, update_selected_template, SelectedTemplateRequest
from models.resume import ResumeData


@pytest.fixture
def review_session():
    session_id = "review-test-session"
    data = {"contact": {"name": "Riya", "email": "riya@example.com", "phone": "1234567890"}, "summary": "Original summary", "skills": {}, "experience": [], "education": [], "certifications": [], "projects": [], "achievements": []}
    SESSIONS[session_id] = {"review_data": data.copy(), "resume_data": {"contact": {"name": "Riya"}}, "files": {}, "filename": "resume.docx"}
    yield session_id
    SESSIONS.pop(session_id, None)


def test_review_get_returns_canonical_editable_data(review_session):
    response = asyncio.run(get_review_data(review_session))
    assert response["resume_data"]["contact"]["email"] == "riya@example.com"


def test_review_update_persists_edits_and_regenerates(review_session):
    resume = ResumeData(contact={"name": "Riya", "email": "riya@example.com", "phone": "1234567890"}, summary="Reviewed summary")
    response = asyncio.run(update_review_data(review_session, resume))
    assert SESSIONS[review_session]["review_data"]["summary"] == "Reviewed summary"
    assert "template1" in response["preview_html"] and SESSIONS[review_session]["files"]
    assert not any(SESSIONS[review_session]["files"].values())


def test_docx_is_generated_lazily_for_current_session(review_session):
    response = asyncio.run(download_file(review_session, "kanini-format-1", "docx"))
    assert response.media_type.endswith("wordprocessingml.document")
    assert SESSIONS[review_session]["files"]["template1_docx"]


def test_pdf_is_generated_lazily_for_current_session(review_session):
    response = asyncio.run(download_file(review_session, "kanini-format-2", "pdf"))
    assert response.media_type == "application/pdf"
    assert SESSIONS[review_session]["files"]["template2_pdf"]


def test_review_render_uses_registry_and_isolates_sessions(review_session):
    response = asyncio.run(render_reviewed_resume(review_session, RenderRequest(template_id="kanini-format-1")))
    assert response["template_id"] == "kanini-format-1"
    with pytest.raises(HTTPException) as exc:
        asyncio.run(render_reviewed_resume(review_session, RenderRequest(template_id="unknown")))
    assert exc.value.status_code == 400
    with pytest.raises(HTTPException) as missing:
        asyncio.run(get_review_data("other-session"))
    assert missing.value.status_code == 404


def test_selected_template_persists_on_the_existing_resume_id(review_session, monkeypatch):
    persisted = []
    monkeypatch.setattr("main._persist_resume", lambda resume_id, data, filename: persisted.append((resume_id, data, filename)))
    response = asyncio.run(update_selected_template(review_session, SelectedTemplateRequest(template_id="kanini-format-1")))
    assert response["session_id"] == review_session
    assert SESSIONS[review_session]["review_data"]["selected_template_id"] == "kanini-format-1"
    assert persisted[0][0] == review_session


def test_html_download_uses_selected_registry_template(review_session):
    response = asyncio.run(download_file(review_session, "kanini-format-2", "html"))
    assert response.media_type == "text/html"
    assert "attachment" in response.headers["content-disposition"]