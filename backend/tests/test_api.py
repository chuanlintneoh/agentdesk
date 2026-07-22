from fastapi.testclient import TestClient

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "docs_url" in data

def test_mock_agent_validation(client):
    # Empty string should fail validation with 400 status
    response = client.post("/api/agent/mock", json={"prompt": ""})
    assert response.status_code == 400
    assert "detail" in response.json()

def test_mock_agent_success(client):
    response = client.post("/api/agent/mock", json={"prompt": "hello mock agent"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "steps" in data
    assert "output" in data

def test_agent_run_validation(client):
    # Empty string or whitespace-only prompt should fail validation with 400 status
    response = client.post("/api/agent/run", json={"prompt": "   "})
    assert response.status_code == 400
    assert "detail" in response.json()

def test_agent_stream_validation(client):
    # Empty prompt should fail validation with 400 status
    response = client.post("/api/agent/stream", json={"prompt": ""})
    assert response.status_code == 400
    assert "detail" in response.json()
