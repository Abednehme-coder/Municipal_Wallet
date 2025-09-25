from django.contrib import admin
from .models import DepositApproval, WithdrawalApproval, RequestApproval


@admin.register(DepositApproval)
class DepositApprovalAdmin(admin.ModelAdmin):
    list_display = ('transaction', 'approver', 'status', 'approved_at', 'created_at')
    list_filter = ('status', 'created_at', 'approved_at')
    search_fields = ('transaction__reference', 'approver__email', 'approver__first_name', 'approver__last_name')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at', 'approved_at')
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('transaction', 'approver')


@admin.register(WithdrawalApproval)
class WithdrawalApprovalAdmin(admin.ModelAdmin):
    list_display = ('transaction', 'approver', 'status', 'approved_at', 'created_at')
    list_filter = ('status', 'created_at', 'approved_at')
    search_fields = ('transaction__reference', 'approver__email', 'approver__first_name', 'approver__last_name')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at', 'approved_at')
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('transaction', 'approver')


@admin.register(RequestApproval)
class RequestApprovalAdmin(admin.ModelAdmin):
    list_display = [
        'transaction', 'approver', 'status', 
        'approved_at', 'created_at'
    ]
    list_filter = ['status', 'created_at', 'approved_at']
    search_fields = [
        'transaction__reference', 'approver__username', 
        'approver__email', 'approver__first_name', 'approver__last_name'
    ]
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at', 'approved_at']
    
    fieldsets = (
        ('Approval Details', {
            'fields': ('transaction', 'approver', 'status')
        }),
        ('Comments', {
            'fields': ('comments',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'approved_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('transaction', 'approver')
