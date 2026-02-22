import os
import time
import platform
from rest_framework.views    import APIView
from rest_framework.response import Response

_start_time = time.time()


def _fmt(b: int) -> str:
    return f'{b / 1024 / 1024:.1f} MB'


def _uptime_human(seconds: float) -> str:
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f'{h}h {m}m {sec}s'


class HealthView(APIView):
    """
    GET /api/health
    Returns service status, uptime, memory usage, and model connection info.
    """
    def get(self, request):
        uptime = time.time() - _start_time

        # psutil may not be installed — graceful fallback
        try:
            import psutil
            proc   = psutil.Process()
            mem    = proc.memory_info()
            heap   = _fmt(mem.rss)
            vm     = psutil.virtual_memory()
            free   = _fmt(vm.available)
            cpus   = psutil.cpu_count(logical=True)
        except ImportError:
            heap = free = 'n/a (install psutil)'
            cpus = os.cpu_count()

        return Response({
            'status':    'ok',
            'service':   'BundleIQ Insurance Recommender API',
            'version':   '1.0.0',
            'framework': 'Django ' + self._django_version(),
            'timestamp': self._now(),
            'uptime': {
                'seconds': round(uptime),
                'human':   _uptime_human(uptime),
            },
            'memory': {
                'rss':  heap,
                'free': free,
            },
            'system': {
                'platform': platform.system(),
                'python':   platform.python_version(),
                'cpus':     cpus,
            },
            'model': {
                'status':   'connected' if os.getenv('PYTHON_API_URL') else 'demo_mode',
                'endpoint': os.getenv('PYTHON_API_URL') or 'mock (set PYTHON_API_URL to connect)',
            },
        })

    @staticmethod
    def _django_version():
        import django
        return django.__version__

    @staticmethod
    def _now():
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()
