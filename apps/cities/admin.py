from django.contrib import admin
from .models import City, Account


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ('name', 'country', 'state', 'is_active', 'created_at')
    list_filter = ('country', 'is_active', 'created_at')
    search_fields = ('name', 'country', 'state')
    ordering = ('name',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('account_name', 'city', 'balance', 'currency', 'is_active', 'created_at')
    list_filter = ('city', 'currency', 'is_active', 'created_at')
    search_fields = ('account_name', 'city__name')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('city')
