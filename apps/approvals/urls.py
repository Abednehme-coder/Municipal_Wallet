from django.urls import path
from . import views

urlpatterns = [
    # Legacy approval views (for backward compatibility)
    path('pending/', views.PendingApprovalsView.as_view(), name='pending-approvals'),
    path('deposit/<uuid:transaction_id>/', views.DepositApprovalView.as_view(), name='deposit-approval'),
    path('withdrawal/<uuid:transaction_id>/', views.WithdrawalApprovalView.as_view(), name='withdrawal-approval'),
    
    # New 5-role system views
    path('requests/pending/', views.PendingRequestApprovalsView.as_view(), name='pending-request-approvals'),
    path('requests/<uuid:transaction_id>/', views.RequestApprovalView.as_view(), name='request-approval'),
]
