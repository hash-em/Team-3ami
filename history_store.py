"""
In-memory prediction history store.
Thread-safe for Django's development server (single process).
For production use a database (PostgreSQL) or cache (Redis).
"""
import uuid
import threading
from datetime import datetime

_lock  = threading.Lock()
_store = []          # newest first
MAX_ITEMS = 500

BUNDLE_LABELS = [
    'Basic Starter', 'Basic Plus', 'Essential', 'Standard', 'Standard Pro',
    'Premium', 'Premium Plus', 'Elite', 'Elite Max', 'Platinum',
]

def add_entry(client_data: dict, prediction: dict, duration_ms: int) -> dict:
    entry = {
        'id':           str(uuid.uuid4()),
        'timestamp':    datetime.utcnow().isoformat() + 'Z',
        'clientData':   client_data,
        'prediction':   prediction,
        'bundleLabel':  BUNDLE_LABELS[prediction.get('Purchased_Coverage_Bundle', 0)],
        'durationMs':   duration_ms,
    }
    with _lock:
        _store.insert(0, entry)
        if len(_store) > MAX_ITEMS:
            _store.pop()
    return entry


def get_all(page: int = 1, limit: int = 20) -> dict:
    with _lock:
        total = len(_store)
        start = (page - 1) * limit
        data  = _store[start:start + limit]

        # Summary across ALL stored entries
        dist = {}
        for e in _store:
            b = e['prediction'].get('Purchased_Coverage_Bundle')
            if b is not None:
                dist[b] = dist.get(b, 0) + 1

        most_common = max(dist, key=dist.get) if dist else None

    return {
        'data':  data,
        'total': total,
        'page':  page,
        'pages': max(1, -(-total // limit)),   # ceiling division
        'summary': {
            'total':              total,
            'bundleDistribution': dist,
            'mostCommon':         most_common,
        },
    }


def get_by_id(entry_id: str) -> dict | None:
    with _lock:
        return next((e for e in _store if e['id'] == entry_id), None)
