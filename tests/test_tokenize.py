def test_tokenize_hello_world_gpt4(client):
    response = client.post("/api/v1/tokenize", json={
        "model": "gpt-4",
        "text": "Hello world",
        "include_tokens": True,
        "include_token_ids": True,
    })
    assert response.status_code == 200
    data = response.json()
    assert data["model"] == "gpt-4"
    assert data["resolved_tokenizer"] == "cl100k_base"
    assert data["token_count"] == 2
    assert data["tokens"] == ["Hello", " world"]
    assert len(data["token_ids"]) == 2


def test_tokenize_returns_token_ids(client):
    response = client.post("/api/v1/tokenize", json={
        "model": "cl100k_base",
        "text": "Hello",
        "include_tokens": False,
        "include_token_ids": True,
    })
    assert response.status_code == 200
    data = response.json()
    assert data["token_ids"] is not None
    assert len(data["token_ids"]) > 0


def test_tokenize_omit_tokens_when_false(client):
    response = client.post("/api/v1/tokenize", json={
        "model": "gpt-4",
        "text": "Hello world",
        "include_tokens": False,
        "include_token_ids": True,
    })
    assert response.status_code == 200
    data = response.json()
    assert data["tokens"] is None


def test_tokenize_empty_text_returns_validation_error(client):
    response = client.post("/api/v1/tokenize", json={
        "model": "gpt-4",
        "text": "",
    })
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"


def test_tokenize_unsupported_model_returns_error(client):
    response = client.post("/api/v1/tokenize", json={
        "model": "definitely-not-a-real-model-xyz",
        "text": "Hello",
    })
    assert response.status_code == 404
    data = response.json()
    assert data["error"]["code"] == "MODEL_NOT_SUPPORTED"


def test_tokenize_raw_encoding(client):
    response = client.post("/api/v1/tokenize", json={
        "model": "r50k_base",
        "text": "Hello world",
        "include_tokens": True,
        "include_token_ids": True,
    })
    assert response.status_code == 200
    data = response.json()
    assert data["resolved_tokenizer"] == "r50k_base"
    assert data["token_count"] > 0
