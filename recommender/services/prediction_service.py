import os
import time
import requests

PYTHON_URL = os.getenv('PYTHON_API_URL', '')


def predict_single(row: dict) -> tuple[dict, int]:
    t0 = time.monotonic()

    if PYTHON_URL:
        resp = requests.post(
            f'{PYTHON_URL}/predict/single',
            json={'data': row},
            timeout=15,
        )
        resp.raise_for_status()
        prediction = resp.json().get('prediction', resp.json())
    else:
        prediction = _mock(row)

    duration_ms = round((time.monotonic() - t0) * 1000)
    return prediction, duration_ms


def _mock(row: dict) -> dict:
    income     = float(row.get('Estimated_Annual_Income') or 40_000)
    dependents = (
        int(row.get('Adult_Dependents')  or 0) +
        int(row.get('Child_Dependents')  or 0) +
        int(row.get('Infant_Dependents') or 0)
    )
    claims   = int(row.get('Previous_Claims_Filed')      or 0)
    vehicles = int(row.get('Vehicles_on_Policy')         or 1)
    riders   = int(row.get('Custom_Riders_Requested')    or 0)
    cancelled = int(row.get('Policy_Cancelled_Post_Purchase') or 0)

    score = 0
    score += min(int(income / 25_000), 5)
    score += min(dependents, 2)
    score += min(vehicles, 1)
    score += min(riders, 1)
    score -= min(claims, 3)
    score -= cancelled

    bundle = max(0, min(9, score))
    return {
        'User_ID':                   row.get('User_ID') or f'USR_{int(time.time())}',
        'Purchased_Coverage_Bundle': bundle,
    }
