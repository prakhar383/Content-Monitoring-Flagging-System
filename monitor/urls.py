from django.urls import path
from . import views

urlpatterns = [
    path('keywords/',       views.KeywordListView.as_view()),
    path('scan/',           views.ScanView.as_view()),
    path('flags/',          views.FlagListView.as_view()),
    path('flags/<int:pk>/', views.FlagDetailView.as_view()),
]