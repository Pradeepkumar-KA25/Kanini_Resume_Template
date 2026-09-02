from main import app


def test_existing_api_routes_remain_registered():
    routes = {
        (method, route.path)
        for route in app.routes
        for method in getattr(route, "methods", set())
        if method not in {"HEAD", "OPTIONS"}
    }
    expected = {
        ("GET", "/api/health"),
        ("GET", "/api/llm-models"),
        ("GET", "/api/templates"),
        ("POST", "/api/upload"),
        ("GET", "/api/resumes/{session_id}/review"),
        ("PUT", "/api/resumes/{session_id}/review"),
        ("POST", "/api/resumes/{session_id}/render"),
        ("POST", "/api/skills-only"),
        ("GET", "/api/resumes"),
        ("GET", "/api/resumes/search"),
        ("GET", "/api/resumes/{resume_id}"),
        ("DELETE", "/api/resumes/{resume_id}"),
        ("GET", "/api/download/{session_id}/{template_id}/{fmt}"),
        ("DELETE", "/api/session/{session_id}"),
    }
    assert expected <= routes