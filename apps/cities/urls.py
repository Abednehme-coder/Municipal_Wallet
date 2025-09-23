from django.urls import path
from . import views

urlpatterns = [
    path('', views.CityListView.as_view(), name='city-list'),
    path('<int:pk>/', views.CityDetailView.as_view(), name='city-detail'),
]
