from secure_knowledge_api.main import app


def test_health_route_is_registered() -> None:
    assert "/health" in app.openapi()["paths"]


def test_organization_routes_are_registered() -> None:
    assert "/organizations" in app.openapi()["paths"]
