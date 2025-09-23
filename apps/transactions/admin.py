from django.contrib import admin
from .models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = [
        'reference', 'type', 'amount', 'status', 'created_by', 
        'city', 'created_at', 'executed_at'
    ]
    list_filter = ['type', 'status', 'city', 'created_at']
    search_fields = ['reference', 'description', 'created_by__username', 'created_by__email']
    readonly_fields = ['id', 'reference', 'created_at', 'updated_at', 'executed_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Transaction Details', {
            'fields': ('id', 'reference', 'type', 'amount', 'description', 'status')
        }),
        ('Account & Location', {
            'fields': ('account', 'city')
        }),
        ('User Information', {
            'fields': ('created_by',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'executed_at'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('account', 'city', 'created_by')
