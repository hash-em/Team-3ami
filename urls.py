from django.urls import path
from recommender.views.health  import HealthView
from recommender.views.predict import PredictSingleView
from recommender.views.history import HistoryListView, HistoryDetailView

urlpatterns = [
    path('api/health',            HealthView.as_view()),
    path('api/predict-single',    PredictSingleView.as_view()),
    path('api/history',           HistoryListView.as_view()),
    path('api/history/<str:pk>',  HistoryDetailView.as_view()),
]
