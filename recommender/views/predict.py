import time
from rest_framework.views    import APIView
from rest_framework.response import Response
from rest_framework          import status

from recommender.services.prediction_service import predict_single
from recommender.services.history_store      import add_entry


class PredictSingleView(APIView):
    """
    POST /api/predict-single

    Body (JSON): client feature fields.
    Returns the predicted Purchased_Coverage_Bundle (0–9).
    """

    def post(self, request):
        row = request.data

        if not row:
            return Response(
                {'error': 'Request body is empty. Send client feature data as JSON.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Auto-assign User_ID if missing
        if not row.get('User_ID'):
            row = dict(row)
            row['User_ID'] = f'USR_{int(time.time() * 1000)}'

        try:
            prediction, duration_ms = predict_single(row)
        except Exception as exc:
            return Response(
                {'error': f'Prediction failed: {str(exc)}'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        entry = add_entry(
            client_data=dict(row),
            prediction=prediction,
            duration_ms=duration_ms,
        )

        return Response({
            'status':     'success',
            'prediction': prediction,
            'durationMs': duration_ms,
            'historyId':  entry['id'],
        })
