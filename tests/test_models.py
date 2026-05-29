def test_list_models_returns_items(client):
    response = client.get("/api/v1/models")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["total"] > 0
    assert len(data["items"]) == data["total"]


def test_list_models_filter_by_group(client):
    response = client.get("/api/v1/models?group=OpenAI+Encodings")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] > 0
    for item in data["items"]:
        assert item["group"] == "OpenAI Encodings"


def test_list_models_filter_by_provider(client):
    response = client.get("/api/v1/models?provider=openai")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] > 0
    for item in data["items"]:
        assert item["provider"] == "openai"


def test_get_model_by_id(client):
    response = client.get("/api/v1/models/gpt-4")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "gpt-4"
    assert data["provider"] == "openai"


def test_get_unknown_model_returns_error(client):
    response = client.get("/api/v1/models/nonexistent-xyz-model")
    assert response.status_code == 404
    data = response.json()
    assert data["error"]["code"] == "MODEL_NOT_SUPPORTED"


def test_gpt4_alias_resolves_to_cl100k(client):
    """Core behavior: gpt-4 model alias must resolve to cl100k_base encoding."""
    response = client.get("/api/v1/models/gpt-4")
    assert response.status_code == 200
    data = response.json()
    assert data["tokenizer_ref"] == "cl100k_base"


def test_gpt35_turbo_alias_resolves_to_cl100k(client):
    """Core behavior: gpt-3.5-turbo must resolve to cl100k_base encoding."""
    response = client.get("/api/v1/models/gpt-3.5-turbo")
    assert response.status_code == 200
    data = response.json()
    assert data["tokenizer_ref"] == "cl100k_base"


def test_gpt4o_alias_resolves_to_o200k(client):
    """Core behavior: gpt-4o model alias must resolve to o200k_base encoding."""
    response = client.get("/api/v1/models/gpt-4o")
    assert response.status_code == 200
    data = response.json()
    assert data["tokenizer_ref"] == "o200k_base"
