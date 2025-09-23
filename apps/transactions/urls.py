from django.urls import path
from . import views

urlpatterns = [
    path('', views.TransactionListView.as_view(), name='transaction-list'),
    path('<uuid:pk>/', views.TransactionDetailView.as_view(), name='transaction-detail'),
    path('<uuid:pk>/cancel/', views.cancel_transaction, name='transaction-cancel'),
    path('<uuid:pk>/approval-progress/', views.transaction_approval_progress, name='transaction-approval-progress'),
]
