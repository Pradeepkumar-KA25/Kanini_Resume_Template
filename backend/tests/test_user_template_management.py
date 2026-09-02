import asyncio
import json

import pytest
from fastapi import HTTPException

import main
from tests.test_template_generation import VALID_SPEC


def _package(root, template_id='user-' + 'a' * 32, source=True):
    package = root / template_id
    package.mkdir(parents=True)
    manifest = {'id': template_id, 'display_name': 'Original', 'description': 'Original description.', 'version': '1.0', 'enabled': True, 'supported_outputs': ['html', 'docx', 'pdf'], 'page_size': 'A4', 'aliases': [], 'assets': {}, 'download_base_name': template_id, 'user_created': True}
    (package / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
    (package / 'template-spec.json').write_text(json.dumps(VALID_SPEC), encoding='utf-8')
    if source:
        (package / 'original.pdf').write_bytes(b'%PDF')
    return template_id, package


def test_get_update_and_delete_user_template(tmp_path, monkeypatch):
    template_id, package = _package(tmp_path)
    monkeypatch.setattr(main, 'USER_TEMPLATES_DIR', tmp_path)
    detail = asyncio.run(main.get_user_template(template_id))
    assert detail['display_name'] == 'Original'
    updated = asyncio.run(main.update_saved_user_template(template_id, main.UpdateUserTemplateRequest(template_name='Renamed', description='Updated description.', template_spec=VALID_SPEC)))
    assert updated['status'] == 'updated'
    assert json.loads((package / 'manifest.json').read_text())['display_name'] == 'Renamed'
    deleted = asyncio.run(main.delete_saved_user_template(template_id))
    assert deleted['status'] == 'deleted' and not package.exists()


def test_management_rejects_invalid_or_traversal_ids(tmp_path, monkeypatch):
    monkeypatch.setattr(main, 'USER_TEMPLATES_DIR', tmp_path)
    for template_id in ('../escape', 'kanini-format-1', 'user-invalid'):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(main.get_user_template(template_id))
        assert exc.value.status_code == 404


def test_update_rejects_invalid_spec(tmp_path, monkeypatch):
    template_id, _ = _package(tmp_path)
    monkeypatch.setattr(main, 'USER_TEMPLATES_DIR', tmp_path)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(main.update_saved_user_template(template_id, main.UpdateUserTemplateRequest(template_name='Valid', description='Valid description.', template_spec={'html': '<script>'})))
    assert exc.value.status_code == 422


def test_regeneration_is_staged_until_confirmed_and_can_cancel(tmp_path, monkeypatch):
    template_id, package = _package(tmp_path)
    monkeypatch.setattr(main, 'USER_TEMPLATES_DIR', tmp_path)
    monkeypatch.setattr(main, 'extract_text', lambda *_: 'Sample resume')
    monkeypatch.setattr(main, 'parse_resume', lambda *_: {'contact': {}, 'skills': {}, 'experience': [], 'education': [], 'projects': []})
    monkeypatch.setattr(main, 'generate_template_spec', lambda *_: VALID_SPEC)
    response = asyncio.run(main.regenerate_user_template(template_id))
    assert response['status'] == 'regenerated' and (package / 'regeneration_spec.json').exists()
    assert json.loads((package / 'template-spec.json').read_text()) == VALID_SPEC
    cancelled = asyncio.run(main.cancel_user_template_regeneration(template_id))
    assert cancelled['status'] == 'cancelled' and not (package / 'regeneration_spec.json').exists()


def test_regeneration_confirm_replaces_only_candidate(tmp_path, monkeypatch):
    template_id, package = _package(tmp_path)
    candidate = {**VALID_SPEC, 'page': {**VALID_SPEC['page'], 'size': 'LETTER'}}
    (package / 'regeneration_spec.json').write_text(json.dumps(candidate), encoding='utf-8')
    monkeypatch.setattr(main, 'USER_TEMPLATES_DIR', tmp_path)
    response = asyncio.run(main.confirm_user_template_regeneration(template_id))
    assert response['status'] == 'updated'
    assert json.loads((package / 'template-spec.json').read_text())['page']['size'] == 'LETTER'
