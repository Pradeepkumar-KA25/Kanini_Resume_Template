import asyncio
import json
import uuid

import pytest
from fastapi import HTTPException

import main
from services import user_template_store
from tests.test_template_generation import VALID_SPEC


def _draft(tmp_path, spec=VALID_SPEC):
    draft_id = str(uuid.uuid4())
    draft_dir = tmp_path / draft_id
    draft_dir.mkdir()
    (draft_dir / 'template_spec.json').write_text(json.dumps(spec), encoding='utf-8')
    return draft_id, draft_dir


def test_save_template_creates_manifest_and_package(tmp_path, monkeypatch):
    draft_root = tmp_path / 'drafts'
    user_root = tmp_path / 'user_templates'
    draft_root.mkdir()
    draft_id, _ = _draft(draft_root)
    monkeypatch.setattr(main, 'TEMPLATE_DRAFT_DIR', draft_root)
    monkeypatch.setattr(main, 'USER_TEMPLATES_DIR', user_root)

    response = asyncio.run(main.save_template_draft(draft_id, main.SaveTemplateDraftRequest(template_name='Modern Resume', description='Single-column modern resume template.')))

    package = user_root / response['template_id']
    manifest = json.loads((package / 'manifest.json').read_text(encoding='utf-8'))
    assert response['status'] == 'saved'
    assert manifest['id'] == response['template_id']
    assert manifest['display_name'] == 'Modern Resume'
    assert manifest['supported_outputs'] == ['html', 'docx', 'pdf']
    assert (package / 'template-spec.json').is_file()


def test_save_template_rejects_missing_draft(tmp_path, monkeypatch):
    monkeypatch.setattr(main, 'TEMPLATE_DRAFT_DIR', tmp_path)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(main.save_template_draft(str(uuid.uuid4()), main.SaveTemplateDraftRequest(template_name='Modern Resume', description='Valid description.')))
    assert exc.value.status_code == 404


def test_save_template_rejects_invalid_spec(tmp_path, monkeypatch):
    draft_id, _ = _draft(tmp_path, {'html': '<script>alert(1)</script>'})
    monkeypatch.setattr(main, 'TEMPLATE_DRAFT_DIR', tmp_path)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(main.save_template_draft(draft_id, main.SaveTemplateDraftRequest(template_name='Modern Resume', description='Valid description.')))
    assert exc.value.status_code == 422


@pytest.mark.parametrize('name', ['', '   ', '../escape', 'Name/Path'])
def test_save_template_rejects_invalid_name(tmp_path, monkeypatch, name):
    draft_id, _ = _draft(tmp_path)
    monkeypatch.setattr(main, 'TEMPLATE_DRAFT_DIR', tmp_path)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(main.save_template_draft(draft_id, main.SaveTemplateDraftRequest(template_name=name, description='Valid description.')))
    assert exc.value.status_code == 422


def test_save_template_uses_a_new_id_when_candidate_already_exists(tmp_path, monkeypatch):
    draft_root = tmp_path / 'drafts'
    user_root = tmp_path / 'user_templates'
    draft_root.mkdir()
    (user_root / 'user-collision').mkdir(parents=True)
    draft_id, _ = _draft(draft_root)
    monkeypatch.setattr(main, 'TEMPLATE_DRAFT_DIR', draft_root)
    monkeypatch.setattr(main, 'USER_TEMPLATES_DIR', user_root)

    class Identifier:
        def __init__(self, value): self.hex = value
    identifiers = iter([Identifier('collision'), Identifier('unique')])
    monkeypatch.setattr(user_template_store.uuid, 'uuid4', lambda: next(identifiers))

    response = asyncio.run(main.save_template_draft(draft_id, main.SaveTemplateDraftRequest(template_name='Modern Resume', description='Valid description.')))
    assert response['template_id'] == 'user-unique'
