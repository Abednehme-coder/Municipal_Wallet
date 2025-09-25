from django.urls import path
from . import views

app_name = 'admin_panel'

urlpatterns = [
    path('approvers/', views.approver_management_view, name='approver_management'),
    path('approvers/assign/', views.assign_approver_view, name='assign_approver'),
    path('approvers/remove/', views.remove_approver_view, name='remove_approver'),
    path('approvers/toggle/', views.toggle_approver_status_view, name='toggle_approver_status'),
    # path('approvers/config/', views.update_approval_config_view, name='update_approval_config'),  # No longer needed - auto-updated
    path('approvers/statistics/', views.approver_statistics_view, name='approver_statistics'),
]
