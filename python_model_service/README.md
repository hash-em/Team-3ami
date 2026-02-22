# Python Model Service (simple Flask demo)

This small Flask service serves a trained model (if present) or a deterministic mock predictor, accepts user feedback, and exposes simple endpoints that the frontend can call. It is intentionally lightweight so you can run it locally for development and collect feedback for later retraining.

Location in repository
- Service entry: `python_model_service/app.py`
- Feedback CSV (created by the service): `python_model_service/feedback.csv`
- Model file (optional): place a serialised model at `model.pkl` in the repo root (i.e. `test/model.pkl`)
- Service requirements: `python_model_service/requirements.txt`

What it provides
- POST `/predict/single` — accepts JSON client features and returns a suggested prediction.
- POST `/feedback` — accepts actual user choice + optional client snapshot; appends a row to `feedback.csv`.
- GET `/health` — service & model health summary.
- GET `/history` and `/history/<id>` — in-memory recent predictions (for quick UI testing).
- GET `/metrics` — lightweight metrics computed from `feedback.csv` (distribution, naive accuracy).
- GET `/ci-pipeline` — returns an example CI GitHub Actions workflow YAML.
- GET `/explainability` — a placeholder manifest for future explainability endpoints.

High-level behavior
- The service tries to load a model using `joblib` from `../model.pkl`. If that succeeds, predictions use the model.
- If no model is present or loading fails, a deterministic mock predictor is used (based on a simple heuristic) to keep the UX consistent.
- Feedback is appended to `python_model_service/feedback.csv` as CSV rows with a JSON payload column for the feature snapshot.
- Predictions are stored in an in-memory history buffer (no DB required).

Quick start — local (recommended for dev)
1. Create and activate a virtualenv (Python 3.9+ recommended)
```sh
python -m venv .venv
. .venv/bin/activate
```

2. Install requirements
```sh
pip install -r python_model_service/requirements.txt
```

3. Run the service
```sh
# from repo root
python python_model_service/app.py
```
By default it listens on `0.0.0.0:5000`. You should see startup logs indicating whether a model was loaded.

Using the endpoints (examples)

- Suggested prediction (frontend -> model service)
```sh
curl -sS -X POST http://localhost:5000/predict/single \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "User_ID": "USR_123",
      "Estimated_Annual_Income": 60000,
      "Adult_Dependents": 1,
      "Child_Dependents": 0,
      "Previous_Claims_Filed": 0,
      "Vehicles_on_Policy": 1
    }
  }' | jq
```

- Submit user feedback (after the user selects the actual bundle)
```sh
curl -sS -X POST http://localhost:5000/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "historyId": "optional-history-id",
    "User_ID": "USR_123",
    "predicted_bundle": 3,
    "actual_bundle": 4,
    "clientData": {
      "Estimated_Annual_Income": 60000,
      "Adult_Dependents": 1
    }
  }' | jq
```

- Health & metrics
```sh
curl http://localhost:5000/health | jq
curl http://localhost:5000/metrics | jq
```

Integrating with the existing frontend / Django API
- The repository's Django service already checks `PYTHON_API_URL` to forward predictions to an external model service. To connect:
  - Run this Flask service on `http://localhost:5000`.
  - Set environment variable for Django: `PYTHON_API_URL=http://localhost:5000`
  - The Django `recommender.services.prediction_service` will then post to `/predict/single` of this service.

Where the feedback goes
- Feedback rows are appended to `python_model_service/feedback.csv`.
- Each row includes:
  - `timestamp`, `user_id`, `predicted_bundle`, `actual_bundle`, `payload_json` (feature snapshot).
- You can use this CSV later for retraining.

Docker (optional)
- Example Dockerfile (simple):
```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY . /app
RUN pip install -r python_model_service/requirements.txt
EXPOSE 5000
CMD ["python", "python_model_service/app.py"]
```
- Example build & run:
```sh
docker build -t model-service .
docker run -p 5000:5000 -v "$(pwd)/python_model_service:/app/python_model_service" model-service
```
Mounting the service folder allows the container to write `feedback.csv` to your host during dev.

CI/CD pipeline
- The service exposes an example GitHub Actions YAML via `/ci-pipeline` to help you get started. In production you should:
  - Run tests (pytest) and linting.
  - Build a container and push to a registry.
  - Deploy to your environment (Kubernetes, ECS, or any host).
- For a minimal pipeline, copy the YAML from `/ci-pipeline` into `.github/workflows/ci.yml` and adapt.

Testing
- Unit/integration tests should be placed under `python_model_service/tests`.
- Basic run:
```sh
# with virtualenv activated
pip install -r python_model_service/requirements.txt
pytest -q python_model_service/tests
```

Notes, limitations & next steps
- This service is intentionally simple:
  - It uses an in-memory history and a CSV for feedback; you may want to migrate feedback storage to a DB for production.
  - The mock predictor is deterministic and intended only for UX/testing.
- Production recommendations:
  - Run behind a production WSGI server (`gunicorn`) and a reverse proxy.
  - Secure endpoints (authentication/authorization) and validate payloads.
  - Add input validation and schema checks (e.g. `pydantic`).
  - Add per-prediction explainability outputs (SHAP) and a retraining pipeline that consumes `feedback.csv`.
  - Consider atomic writes to feedback storage if you move to a shared filesystem or network storage.
- Model reloading:
  - Currently the model is loaded at startup. For smoother model deployments, add an API to reload the model or use a model server pattern.

Troubleshooting
- "Model not loaded" — ensure `joblib` is installed and `model.pkl` exists at the repo root (`test/model.pkl`). The app logs the reason when load fails and falls back to the mock.
- "Feedback file not created" — check service has write permissions in `python_model_service/` directory.
- If you change requirements, recreate the virtualenv and reinstall to avoid inconsistent states.

If you'd like, I can:
- Add a Docker Compose file that orchestrates Django + frontend + this model service for local dev.
- Add a simple web dashboard page (beyond the placeholder) to visualize metrics and feedback.
- Add an endpoint to trigger model reloads or to expose SHAP explanations if a supported model is available.

Happy to implement any of the above next — tell me which piece you want prioritized.