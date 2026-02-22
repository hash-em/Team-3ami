from rest_framework.views    import APIView
from rest_framework.response import Response
from rest_framework          import status

from recommender.services.history_store import get_all, get_by_id


class HistoryListView(APIView):
    """
    GET /api/history?page=1&limit=20
    Returns paginated prediction history + overall bundle distribution summary.
    """

    def get(self, request):
        try:
            page  = max(1, int(request.query_params.get('page',  1)))
            limit = min(100, max(1, int(request.query_params.get('limit', 20))))
        except (TypeError, ValueError):
            page, limit = 1, 20

        return Response(get_all(page=page, limit=limit))


class HistoryDetailView(APIView):
    """
    GET /api/history/<id>
    Returns a single history entry including the full client data snapshot.
    """

    def get(self, request, pk):
        entry = get_by_id(pk)
        if not entry:
            return Response(
                {'error': 'History entry not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(entry)
