import json
import time

import pytest

from python_model_service import app as flask_app


@pytest.fixture
def client():
    """Flask test client fixture."""
    flask_app.config.update({"TESTING": True})
    with flask_app.test_client() as client:
        yield client


def test_health_endpoint(client):
    """GET /health should return a JSON object with model information."""
    resp = client.get("/health")
    assert resp.status_code == 200, "Health endpoint did not return 200"
    data = resp.get_json()
    assert isinstance(data, dict), "Health response is not JSON object"
    # Basic keys we expect
    assert "status" in data, "Health JSON missing 'status' key"
    assert "model" in data, "Health JSON missing 'model' key"
    assert "timestamp" in data, "Health JSON missing 'timestamp' key"


def test_predict_single_returns_bundle(client):
    """POST /predict/single should accept feature dict and return a bundle prediction."""
    payload = {
        "data": {
            "Estimated_Annual_Income": 65000,
            "Adult_Dependents": 1,
            "Child_Dependents": 0,
            "Infant_Dependents": 0,
            "Previous_Claims_Filed": 0,
            "Vehicles_on_Policy": 1,
            # intentionally omit User_ID to exercise auto-assignment
        }
    }

    resp = client.post("/predict/single", json=payload)
    assert resp.status_code == 200, f"Predict endpoint returned {resp.status_code}"
    body = resp.get_json()
    # The service returns a wrapper with 'prediction'
    assert "prediction" in body, "Response missing 'prediction' key"
    prediction = body["prediction"]
    assert isinstance(prediction, dict), "prediction should be a dict"
    assert "Purchased_Coverage_Bundle" in prediction, "prediction missing Purchased_Coverage_Bundle"
    bundle = prediction["Purchased_Coverage_Bundle"]
    # Should be an integer in the expected range (0-9)
    assert isinstance(bundle, (int,)), f"bundle is not int: {bundle!r}"
    assert 0 <= bundle <= 9, f"bundle out of expected range: {bundle}"


def test_feedback_flow_and_metrics(client):
    """
    End-to-end feedback flow:
    - Call predict to get a suggested bundle
    - POST to /feedback with actual_bundle
    - GET /metrics and assert feedback count increases
    """
    # 1) Get a prediction
    p_payload = {
        "data": {
            "Estimated_Annual_Income": 48000,
            "Adult_Dependents": 2,
            "Child_Dependents": 1,
        }
    }
    p_resp = client.post("/predict/single", json=p_payload)
    assert p_resp.status_code == 200, "Initial predict call failed"
    p_body = p_resp.get_json()
    prediction = p_body.get("prediction") or {}
    predicted_bundle = prediction.get("Purchased_Coverage_Bundle")

    # Basic sanity checks
    assert predicted_bundle is not None, "Predicted bundle missing"
    assert isinstance(predicted_bundle, int), "Predicted bundle should be int"

    # 2) Submit feedback with actual choice (choose a different value to test mismatch)
    actual_bundle = (predicted_bundle + 1) % 10
    feedback_payload = {
        "historyId": p_body.get("history_id"),
        "User_ID": prediction.get("User_ID"),
        "predicted_bundle": int(predicted_bundle),
        "actual_bundle": int(actual_bundle),
        "clientData": p_payload["data"],
    }

    f_resp = client.post("/feedback", json=feedback_payload)
    # The implementation returns 201 on success
    assert f_resp.status_code in (200, 201), f"Feedback endpoint returned {f_resp.status_code}"
    f_body = f_resp.get_json()
    # Accept either {'status': 'ok'} or other success payloads — be permissive
    assert isinstance(f_body, dict), "Feedback response must be JSON"

    # 3) Check metrics — the total_feedback should be >= 1 (since feedback.csv is append-only across test runs)
    # The metrics endpoint reads the CSV; allow a small retry loop in case write is slightly delayed
    metrics = None
    for _ in range(5):
        m_resp = client.get("/metrics")
        assert m_resp.status_code == 200, "Metrics endpoint failed"
        metrics = m_resp.get_json()
        if metrics and metrics.get("total_feedback", 0) >= 1:
            break
        time.sleep(0.1)

    assert metrics is not None, "Metrics response was empty"
    assert "total_feedback" in metrics, "Metrics JSON missing total_feedback"
    assert isinstance(metrics["total_feedback"], int), "total_feedback should be int"
    assert metrics["total_feedback"] >= 1, "Expected at least 1 feedback row recorded"

    # distribution and accuracy keys exist
    assert "distribution" in metrics and isinstance(metrics["distribution"], dict)
    assert "accuracy" in metrics, "Metrics JSON missing 'accuracy' field"