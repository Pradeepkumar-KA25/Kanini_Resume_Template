import asyncio
import io

import pytest
from fastapi import HTTPException, UploadFile

import main


def _upload(filename: str, content: bytes = b'%PDF-1.4 sample') -> UploadFile:
    return UploadFile(filename=filename, file=io.BytesIO(content))


def test_template_draft_rejects_non_pdf():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(main.create_template_draft(_upload('sample.docx')))
    assert exc.value.status_code == 400


def test_template_draft_stores_uploaded_pdf_and_extracted_data(tmp_path, monkeypatch, normal_resume):
    monkeypatch.setattr(main, 'TEMPLATE_DRAFT_DIR', tmp_path)
    monkeypatch.setattr(main, 'extract_text', lambda *_: 'Riya Raman\nriya@example.com\n9000000000')
    monkeypatch.setattr(main, 'parse_resume', lambda *_: normal_resume)

    response = asyncio.run(main.create_template_draft(_upload('sample.pdf')))

    draft_dir = tmp_path / response['draft_id']
    assert response['status'] == 'uploaded'
    assert response['filename'] == 'sample.pdf'
    assert response['extracted_data']['contact']['email'] == 'riya@example.com'
    assert (draft_dir / 'original.pdf').exists()
    assert (draft_dir / 'extracted_data.json').exists()


def test_template_draft_rejects_unreadable_pdf(tmp_path, monkeypatch):
    monkeypatch.setattr(main, 'TEMPLATE_DRAFT_DIR', tmp_path)
    monkeypatch.setattr(main, 'extract_text', lambda *_: '')

    with pytest.raises(HTTPException) as exc:
        asyncio.run(main.create_template_draft(_upload('sample.pdf')))

    assert exc.value.status_code == 422
    assert not list(tmp_path.iterdir())
