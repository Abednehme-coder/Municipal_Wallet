from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('transactions/create/', views.create_transaction_view, name='create_transaction'),
    path('transactions/<uuid:transaction_id>/', views.transaction_detail_view, name='transaction_detail'),
    path('transactions/', views.transactions_list_view, name='transactions_list'),
    path('approvals/', views.approvals_list_view, name='approvals_list'),
    path('approvals/<uuid:transaction_id>/process/', views.process_approval_view, name='process_approval'),
    path('reports/', views.reports_view, name='reports'),
    path('reports/export/', views.export_transactions_view, name='export_transactions'),
]
