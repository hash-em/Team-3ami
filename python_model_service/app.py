#!/usr/bin/env python3
"""
Simple Flask model service to serve predictions for the frontend, record user feedback,
and expose basic dashboard / metrics endpoints.

Features:
- Loads a serialized model (if available) from ../model.pkl
- POST /predict/single  -> returns a suggested prediction (mock if no model)
- POST /feedback       -> records actual user choice (appends to feedback.csv)
- GET  /history        -> returns in-memory recent predictions
- GET  /metrics        -> computes simple metrics from feedback.csv
- GET  /ci-pipeline    -> returns a suggested CI pipeline YAML (for copy/paste)
- GET  /explainability -> placeholder endpoint for future explainability features

Persistence:
- feedback entries are appended to python_model_service/feedback.csv
- predictions are kept in an in-memory ring-buffer (no DB required)

Notes:
- This is a simple, dependency-light service: it uses the standard library csv module
  for feedback persistence and will optionally use joblib and pandas if available to
  load and run a real model. If those aren't present, a deterministic mock predictor is used.
"""

from __future__ import annotations

import csv
import json
import os
import time
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from flask import Flask, jsonify, request, render_template, render_template_string, send_from_directory
from flask_cors import CORS

# Optional dependencies for real model loading
try:
    import joblib  # type: ignore
except Exception:
    joblib = None  # type: ignore

try:
    import pandas as pd  # type: ignore
except Exception:
    pd = None  # type: ignore

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent  # points to `test` directory
MODEL_PATH = Path(__file__).resolve().parent.parent / "model.pkl"
FEEDBACK_CSV = Path(__file__).resolve().parent / "feedback.csv"
MAX_HISTORY_ITEMS = 1000

# ---------------------------------------------------------------------------
# App and state
# ---------------------------------------------------------------------------

app = Flask(
    __name__,
    template_folder=str(Path(__file__).resolve().parent / "templates"),
    static_folder=str(Path(__file__).resolve().parent / "static"),
)
CORS(app)  # allow cross-origin requests from frontend dev server

# Serve the vanilla frontend index.html at the root path
@app.route("/", methods=["GET"])
def index():
    # Render the static vanilla frontend located at python_model_service/templates/index.html
    return render_template("index.html")

_lock = threading.Lock()
_history: List[Dict[str, Any]] = []  # newest first (appendleft semantics implemented)
_model = None
_model_info: Dict[str, Any] = {"loaded": False, "source": "none"}


# ---------------------------------------------------------------------------
# Model loading & mock predictor
# ---------------------------------------------------------------------------

def try_load_model(path: Path) -> Optional[Any]:
    """
    Attempt to load a model with joblib (commonly used for scikit-learn models).
    Returns the model object on success or None on failure.
    """
    if joblib is None:
        app.logger.info("joblib not available; skipping model load.")
        return None

    if not path.exists():
        app.logger.info("Model file %s not found. Using mock predictor.", path)
        return None

    try:
        model = joblib.load(path)
        app.logger.info("Loaded model from %s", path)
        return model
    except Exception as exc:  # noqa: BLE001 - we want to log the exception
        app.logger.exception("Failed to load model at %s: %s", path, exc)
        return None


def _mock_predict(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simple deterministic heuristic predictor used as fallback. Mirrors the demo logic
    used in the frontend project so UX is reasonable even without a trained model.
    """
    # Safe conversions with fallbacks
    def to_float(x, default=40000.0):
        try:
            return float(x)
        except Exception:
            return default

    def to_int(x, default=0):
        try:
            return int(x)
        except Exception:
            return default

    income = to_float(row.get("Estimated_Annual_Income", None), 40000.0)
    dependents = (
        to_int(row.get("Adult_Dependents")) +
        to_int(row.get("Child_Dependents")) +
        to_int(row.get("Infant_Dependents"))
    )
    claims = to_int(row.get("Previous_Claims_Filed"), 0)
    vehicles = to_int(row.get("Vehicles_on_Policy"), 1)
    riders = to_int(row.get("Custom_Riders_Requested"), 0)
    cancelled = to_int(row.get("Policy_Cancelled_Post_Purchase"), 0)

    score = 0
    score += min(int(income / 25000), 5)
    score += min(dependents, 2)
    score += min(vehicles, 1)
    score += min(riders, 1)
    score -= min(claims, 3)
    score -= cancelled

    bundle = max(0, min(9, score))
    return {
        "User_ID": row.get("User_ID") or f"USR_{int(time.time())}",
        "Purchased_Coverage_Bundle": int(bundle),
    }


def predict_with_model(model: Any, row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Predict using the loaded model.
    If pandas is available and the model expects a DataFrame, we convert the row.
    This function tries to be forgiving about input formats.
    """
    # Common scikit-learn style: model.predict(X) where X is a 2D array or DataFrame.
    try:
        if pd is not None:
            df = pd.DataFrame([row])
            # If the model needs a specific set of features, it should handle missing keys.
            preds = model.predict(df)
            # Some models return numpy arrays; extract scalar
            bundle = int(preds[0]) if len(preds) > 0 else None
            return {
                "User_ID": row.get("User_ID") or f"USR_{int(time.time())}",
                "Purchased_Coverage_Bundle": bundle,
            }
        else:
            # Try passing raw mapping; some custom models accept dict inputs
            preds = model.predict([row])  # type: ignore
            bundle = int(preds[0]) if len(preds) > 0 else None
            return {
                "User_ID": row.get("User_ID") or f"USR_{int(time.time())}",
                "Purchased_Coverage_Bundle": bundle,
            }
    except Exception:
        # On any failure while using a real model, fallback to mock
        app.logger.exception("Model prediction failed; falling back to mock predictor.")
        return _mock_predict(row)


def load_model_at_startup() -> None:
    global _model, _model_info
    model = try_load_model(MODEL_PATH)
    if model is not None:
        _model = model
        _model_info = {
            "loaded": True,
            "source": str(MODEL_PATH),
            "type": type(model).__name__,
        }
    else:
        _model = None
        _model_info = {
            "loaded": False,
            "source": "mock",
            "type": "mock",
        }


# Load model eagerly on import/start
load_model_at_startup()

# ---------------------------------------------------------------------------
# Helpers: history & feedback persistence
# ---------------------------------------------------------------------------

def add_history_entry(client_data: Dict[str, Any], prediction: Dict[str, Any], duration_ms: int) -> Dict[str, Any]:
    """
    Add entry to in-memory history and return it.
    """
    entry = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "clientData": client_data,
        "prediction": prediction,
        "durationMs": duration_ms,
    }
    with _lock:
        _history.insert(0, entry)
        if len(_history) > MAX_HISTORY_ITEMS:
            _history.pop()
    return entry


def append_feedback_row(row: Dict[str, Any]) -> None:
    """
    Append feedback to FEEDBACK_CSV. The file will be created with a header if missing.
    Uses a file lock to avoid concurrent writes clobbering the CSV.
    Expected columns:
      timestamp, user_id, predicted_bundle, actual_bundle, payload_json
    """
    header = ["timestamp", "user_id", "predicted_bundle", "actual_bundle", "payload_json"]
    FEEDBACK_CSV.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        exists = FEEDBACK_CSV.exists()
        with FEEDBACK_CSV.open("a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=header)
            if not exists:
                writer.writeheader()
            writer.writerow({
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "user_id": row.get("User_ID", ""),
                "predicted_bundle": row.get("predicted_bundle", ""),
                "actual_bundle": row.get("actual_bundle", ""),
                "payload_json": json.dumps(row.get("clientData", {})),
            })


def read_feedback_rows() -> List[Dict[str, Any]]:
    """
    Read all feedback rows and return them as dicts.
    """
    if not FEEDBACK_CSV.exists():
        return []
    with FEEDBACK_CSV.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def compute_simple_metrics() -> Dict[str, Any]:
    """
    Compute basic metrics from feedback.csv:
      - total_feedback
      - distribution of actual bundles
      - naive accuracy (where predicted == actual)
    """
    rows = read_feedback_rows()
    total = len(rows)
    dist = {}
    correct = 0
    for r in rows:
        actual = r.get("actual_bundle", "")
        predicted = r.get("predicted_bundle", "")
        if actual != "":
            dist[actual] = dist.get(actual, 0) + 1
        if actual != "" and predicted != "" and str(actual) == str(predicted):
            correct += 1
    accuracy = (correct / total) if total > 0 else None
    return {
        "total_feedback": total,
        "distribution": dist,
        "correct_matches": correct,
        "accuracy": accuracy,
    }


# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------

@app.route("/health", methods=["GET"])
def health():
    """Service health endpoint."""
    return jsonify({
        "status": "ok",
        "model": _model_info,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    })


@app.route("/predict/single", methods=["POST"])
def predict_single():
    """
    Accepts JSON body:
      { "data": { ...client feature dict... } }

    Returns:
      {
        "status": "success",
        "prediction": { "User_ID": "...", "Purchased_Coverage_Bundle": 3 },
        "duration_ms": 123,
        "model": { ...info... }
      }
    """
    payload = request.get_json(force=True, silent=True)
    if not payload:
        return jsonify({"error": "Request body should be JSON with a 'data' object."}), 400

    row = payload.get("data") or payload.get("client") or payload
    if not isinstance(row, dict):
        return jsonify({"error": "Expected 'data' to be a JSON object of client features."}), 400

    # Ensure User_ID exists
    if not row.get("User_ID"):
        row = dict(row)
        row["User_ID"] = f"USR_{int(time.time() * 1000)}"

    t0 = time.monotonic()
    try:
        if _model is not None:
            prediction = predict_with_model(_model, row)
            model_source = _model_info.get("source", "unknown")
        else:
            prediction = _mock_predict(row)
            model_source = "mock"
    except Exception:
        app.logger.exception("Prediction failed")
        return jsonify({"error": "Prediction failed"}), 502
    duration_ms = int((time.monotonic() - t0) * 1000)

    entry = add_history_entry(client_data=row, prediction=prediction, duration_ms=duration_ms)

    response = {
        "status": "success",
        "prediction": prediction,
        "duration_ms": duration_ms,
        "history_id": entry["id"],
        "model": {
            "source": model_source,
            "type": _model_info.get("type"),
        },
    }
    return jsonify(response)


@app.route("/feedback", methods=["POST"])
def feedback():
    """
    Record user feedback after they choose the actual bundle.
    Expected JSON:
      {
        "historyId": "<optional - id returned when suggested>",
        "User_ID": "USR_xxx",
        "predicted_bundle": 3,
        "actual_bundle": 4,
        "clientData": { ... optional snapshot ... }
      }

    The endpoint appends the feedback to feedback.csv for later retraining.
    """
    payload = request.get_json(force=True, silent=True)
    if not payload:
        return jsonify({"error": "Request body must be JSON."}), 400

    # Basic validation
    if "actual_bundle" not in payload:
        return jsonify({"error": "Missing required field 'actual_bundle'."}), 400

    try:
        append_feedback_row(payload)
    except Exception:
        app.logger.exception("Failed to append feedback")
        return jsonify({"error": "Failed to save feedback"}), 500

    return jsonify({"status": "ok"}), 201


@app.route("/history", methods=["GET"])
def get_history():
    """
    Return paginated history; query params: page (1-based), limit
    """
    try:
        page = max(1, int(request.args.get("page", 1)))
        limit = min(200, max(1, int(request.args.get("limit", 50))))
    except Exception:
        page, limit = 1, 50

    with _lock:
        total = len(_history)
        start = (page - 1) * limit
        data_slice = _history[start:start + limit]

    return jsonify({
        "data": data_slice,
        "total": total,
        "page": page,
        "pages": max(1, -(-total // limit)),
    })


@app.route("/history/<string:entry_id>", methods=["GET"])
def get_history_entry(entry_id: str):
    with _lock:
        entry = next((e for e in _history if e["id"] == entry_id), None)
    if not entry:
        return jsonify({"error": "Not found"}), 404
    return jsonify(entry)


@app.route("/metrics", methods=["GET"])
def metrics():
    """
    Compute simple metrics from feedback.csv and return them.
    """
    try:
        m = compute_simple_metrics()
    except Exception:
        app.logger.exception("Failed to compute metrics")
        return jsonify({"error": "Failed to compute metrics"}), 500
    return jsonify(m)


@app.route("/ci-pipeline", methods=["GET"])
def ci_pipeline_example():
    """
    Returns a small example GitHub Actions workflow YAML to run tests and build a Docker image.
    Copy/paste it into .github/workflows/ci.yml in your repo and adapt as needed.
    """
    yaml = r"""
name: CI

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install deps
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements2.txt
      - name: Run tests
        run: |
          # adapt your test command here
          pytest -q

  build:
    runs-on: ubuntu-latest
    needs: test
    steps:
      - uses: actions/checkout@v4
      - name: Build Docker image
        run: |
          docker build -t my-recommender:latest .
          # optionally push to registry
"""
    return app.response_class(yaml, mimetype="text/yaml")


@app.route("/explainability", methods=["GET"])
def explainability_placeholder():
    """
    Placeholder endpoint for future explainability / SHAP / LIME outputs.
    For now, returns a manifest of what will be implemented later.
    """
    return jsonify({
        "status": "planned",
        "features": [
            "per-prediction feature importance (SHAP)",
            "aggregate global feature importance",
            "counterfactual suggestions",
            "per-segment explanations"
        ],
        "note": "This endpoint will return explainability artifacts in future iterations."
    })


# ---------------------------------------------------------------------------
# MLOps: background retrain watcher, admin UI endpoints and model versioning
# ---------------------------------------------------------------------------

# Directories for saved models & simple admin reports
MODELS_DIR = Path(__file__).resolve().parent / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

_admin_reports: List[Dict[str, Any]] = []
_retrain_lock = threading.Lock()
_is_retraining = False
_LAST_RETRAIN_AT: Optional[float] = None

# Configuration
RETRAIN_BATCH_SIZE = int(os.getenv("RETRAIN_BATCH_SIZE", "50"))   # start retrain when feedback rows >= this
RETRAIN_MIN_INTERVAL = int(os.getenv("RETRAIN_MIN_INTERVAL", "3600"))  # seconds between retrains
ANOMALY_MAX_DOMINANCE = float(os.getenv("ANOMALY_MAX_DOMINANCE", "0.9"))  # if a class dominates, flag anomaly


def _save_model_and_update_symlink(trained_model: Any) -> str:
    """
    Save trained model to models/ with a timestamped version and update repo root model.pkl
    Returns the path to the saved model file.
    """
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    version = f"model_v{ts}.pkl"
    dest = MODELS_DIR / version
    try:
        if joblib is None:
            raise RuntimeError("joblib not available to save the model")
        joblib.dump(trained_model, str(dest))
        # also update the top-level model.pkl so Django / repo can pick it up if needed
        top_model = Path(__file__).resolve().parent.parent / "model.pkl"
        # copy the file (not symlink) for portability
        with open(dest, "rb") as r, open(top_model, "wb") as w:
            w.write(r.read())
        return str(dest)
    except Exception as exc:
        app.logger.exception("Failed to save model: %s", exc)
        raise


def _anomaly_check_from_feedback(rows: List[Dict[str, Any]]) -> Tuple[bool, Dict[str, Any]]:
    """
    Very small anomaly detector: checks if any single class dominates the labels,
    or if we have insufficient class diversity. Returns (is_anomaly, details).
    """
    counts = {}
    for r in rows:
        a = r.get("actual_bundle", "")
        if a == "":
            continue
        counts[a] = counts.get(a, 0) + 1
    total = sum(counts.values())
    if total == 0:
        return True, {"reason": "no labeled feedback rows"}
    most_common_count = max(counts.values())
    dominance = most_common_count / total if total > 0 else 0.0
    details = {"total": total, "counts": counts, "dominance": dominance}
    is_anomaly = dominance >= ANOMALY_MAX_DOMINANCE
    if is_anomaly:
        details["reason"] = "single class predominance"
    return is_anomaly, details


def _prepare_training_df(rows: List[Dict[str, Any]]):
    """
    Convert feedback rows into a pandas DataFrame suitable for training.
    Expect `payload_json` column contains the feature snapshot (dict).
    Returns (X, y) as DataFrame/Series if possible.
    """
    if pd is None:
        raise RuntimeError("pandas not installed; cannot prepare training data")
    records = []
    ys = []
    for r in rows:
        pj = r.get("payload_json", "{}")
        try:
            feat = json.loads(pj)
        except Exception:
            feat = {}
        records.append(feat)
        ys.append(int(r.get("actual_bundle", 0)) if r.get("actual_bundle", "") != "" else None)
    df = pd.DataFrame(records).fillna(0)
    y = pd.Series(ys)
    # remove rows without labels
    mask = y.notnull()
    if mask.sum() == 0:
        raise RuntimeError("No labeled rows in feedback for training")
    return df.loc[mask].reset_index(drop=True), y.loc[mask].reset_index(drop=True)


def retrain_pipeline(force: bool = False) -> Dict[str, Any]:
    """
    Orchestrates a retraining run:
      - Reads feedback rows
      - Runs anomaly checks, reports to admin if present
      - Trains a simple model (RandomForest if scikit-learn available) as a refit/fine-tune
      - Saves model version and updates _model in-memory
      - Records a report in _admin_reports
    Returns a report dict with status/details.
    """
    global _model, _model_info, _LAST_RETRAIN_AT, _is_retraining

    with _retrain_lock:
        if _is_retraining:
            return {"status": "skipped", "reason": "retrain already in progress"}
        _is_retraining = True

    try:
        rows = read_feedback_rows()
        total_feedback = len(rows)
        if total_feedback < RETRAIN_BATCH_SIZE and not force:
            return {"status": "skipped", "reason": f"not enough feedback rows ({total_feedback} < {RETRAIN_BATCH_SIZE})"}

        # anomaly checks
        is_anom, details = _anomaly_check_from_feedback(rows)
        report = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "action": "retrain_attempt",
            "total_feedback": total_feedback,
            "anomaly": is_anom,
            "anomaly_details": details,
        }
        if is_anom and not force:
            _admin_reports.append({**report, "status": "aborted", "note": "anomaly detected; admin notified"})
            return {**report, "status": "aborted", "note": "anomaly detected"}

        # prepare training data
        try:
            X, y = _prepare_training_df(rows)
        except Exception as exc:
            _admin_reports.append({**report, "status": "failed", "error": str(exc)})
            return {"status": "failed", "error": str(exc)}

        # Train a simple model if sklearn available
        try:
            from sklearn.ensemble import RandomForestClassifier  # type: ignore
        except Exception:
            _admin_reports.append({**report, "status": "failed", "error": "scikit-learn not available"})
            return {"status": "failed", "error": "scikit-learn not available"}

        try:
            clf = RandomForestClassifier(n_estimators=50, random_state=42)
            clf.fit(X, y)
        except Exception as exc:
            _admin_reports.append({**report, "status": "failed", "error": f"training error: {exc}"})
            return {"status": "failed", "error": f"training error: {exc}"}

        # Save model version
        try:
            saved_path = _save_model_and_update_symlink(clf)
            # reload model into memory
            _model = try_load_model(Path(saved_path))
            _model_info.update({"loaded": True, "source": saved_path, "type": type(_model).__name__})
            _LAST_RETRAIN_AT = time.time()
            _admin_reports.append({**report, "status": "completed", "model_path": saved_path})
            return {"status": "ok", "model_path": saved_path}
        except Exception as exc:
            _admin_reports.append({**report, "status": "failed", "error": str(exc)})
            return {"status": "failed", "error": str(exc)}
    finally:
        _is_retraining = False


def _retrain_watcher():
    """
    Background thread that periodically checks feedback size and triggers retraining
    if the threshold and timing conditions are met.
    """
    while True:
        try:
            rows = read_feedback_rows()
            ts = time.time()
            enough = len(rows) >= RETRAIN_BATCH_SIZE
            interval_ok = (_LAST_RETRAIN_AT is None) or (ts - _LAST_RETRAIN_AT >= RETRAIN_MIN_INTERVAL)
            if enough and interval_ok:
                app.logger.info("Retrain watcher: conditions met -> starting retrain")
                # run retrain in same thread to simplify concurrency model
                retrain_pipeline()
        except Exception:
            app.logger.exception("Retrain watcher error")
        time.sleep(30)  # check every 30 seconds


# Admin web UI: small vanilla HTML templates (no React)
_ADMIN_INDEX_HTML = """
<!doctype html>
<html>
  <head><meta charset="utf-8"><title>Model Admin</title></head>
  <body style="font-family:system-ui,Arial,sans-serif">
    <h1>Model Admin Dashboard</h1>
    <section>
      <h2>Model</h2>
      <pre id="modelinfo">{{ model_info }}</pre>
    </section>
    <section>
      <h2>Metrics</h2>
      <pre id="metrics">{{ metrics }}</pre>
    </section>
    <section>
      <h2>Reports</h2>
      <ul>
      {% for r in reports %}
        <li><strong>{{ r.timestamp }}</strong> - {{ r.action }} - {{ r.status }} - {{ r.get('note','') }}</li>
      {% else %}
        <li>No reports yet</li>
      {% endfor %}
      </ul>
    </section>
    <section>
      <h2>Models</h2>
      <ul>
      {% for m in models %}
        <li>{{ m }}</li>
      {% else %}
        <li>No model versions saved</li>
      {% endfor %}
      </ul>
    </section>
    <section>
      <form id="retrain" method="post" action="/admin/retrain" style="margin-top:16px">
        <button type="submit">Trigger Manual Retrain</button>
      </form>
    </section>
  </body>
</html>
"""


@app.route("/admin", methods=["GET"])
def admin_index():
    metrics = compute_simple_metrics()
    # list model files
    models = sorted([p.name for p in MODELS_DIR.glob("model_v*.pkl")], reverse=True)
    rendered = render_template('admin.html',
                                      model_info=_model_info,
                                      metrics=metrics,
                                      reports=list(reversed(_admin_reports))[:50],
                                      models=models)
    return rendered


@app.route("/admin/reports", methods=["GET"])
def admin_reports():
    return jsonify({"reports": _admin_reports})


@app.route("/admin/retrain", methods=["POST"])
def admin_retrain():
    # Fire retrain asynchronously so UI returns quickly
    def _run():
        app.logger.info("Admin triggered retrain starting...")
        r = retrain_pipeline(force=True)
        app.logger.info("Admin retrain completed: %s", r)

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"status": "retrain_started"}), 202


@app.route("/admin/models", methods=["GET"])
def admin_models():
    models = sorted([p.name for p in MODELS_DIR.glob("model_v*.pkl")], reverse=True)
    return jsonify({"models": models, "current_model": _model_info})


@app.route("/admin/model/<string:name>", methods=["GET"])
def admin_get_model(name: str):
    p = MODELS_DIR / name
    if not p.exists():
        return jsonify({"error": "not found"}), 404
    return send_from_directory(str(MODELS_DIR), name, as_attachment=True)


# start background retrain watcher thread at startup
try:
    t = threading.Thread(target=_retrain_watcher, daemon=True)
    t.start()
    app.logger.info("Started retrain watcher thread")
except Exception:
    app.logger.exception("Failed to start retrain watcher thread")

# ---------------------------------------------------------------------------
# Run app (for local development)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Helpful debug output when running directly
    print("Starting Flask model service (with MLOps watcher)")
    print("Model info:", _model_info)
    print("Feedback file:", str(FEEDBACK_CSV))
    print("Models directory:", str(MODELS_DIR))
    # Use 0.0.0.0 so it's reachable from other devices (dev containers, WSL, etc.)
    app.run(host="0.0.0.0", port=5000, debug=True)
