def test_compare_multiple_models(client):
    response = client.post("/api/v1/compare", json={
        "models": ["gpt-4", "gpt-3.5-turbo", "r50k_base"],
        "text": "Hello world",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["text_length"] == 11
    assert len(data["results"]) == 3

    results_by_model = {r["model"]: r for r in data["results"]}

    # gpt-4 and gpt-3.5-turbo both use cl100k_base
    assert results_by_model["gpt-4"]["resolved_tokenizer"] == "cl100k_base"
    assert results_by_model["gpt-3.5-turbo"]["resolved_tokenizer"] == "cl100k_base"
    assert results_by_model["gpt-4"]["token_count"] == results_by_model["gpt-3.5-turbo"]["token_count"]

    # r50k_base uses itself
    assert results_by_model["r50k_base"]["resolved_tokenizer"] == "r50k_base"


def test_compare_too_many_models_returns_error(client):
    response = client.post("/api/v1/compare", json={
        "models": ["gpt-4"] * 11,
        "text": "Hello",
    })
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"


def test_compare_empty_models_returns_error(client):
    response = client.post("/api/v1/compare", json={
        "models": [],
        "text": "Hello",
    })
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"


def test_compare_includes_error_for_bad_model(client):
    response = client.post("/api/v1/compare", json={
        "models": ["gpt-4", "not-a-real-model-xyz"],
        "text": "Hello world",
    })
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 2
    results_by_model = {r["model"]: r for r in data["results"]}
    assert results_by_model["gpt-4"]["error"] is None
    assert results_by_model["not-a-real-model-xyz"]["error"] is not None


def test_compare_pricing_route(client):
    response = client.get("/api/v1/pricing")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["total"] > 0
