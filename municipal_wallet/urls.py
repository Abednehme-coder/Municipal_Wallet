"""
URL configuration for municipal_wallet project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
urlpatterns = [
    path('admin/', admin.site.urls),
    path('admin-panel/', include('apps.admin_panel.urls', namespace='admin_panel')),
    path('api/auth/', include('apps.accounts.urls')),
    path('api/cities/', include('apps.cities.urls')),
    path('api/transactions/', include('apps.transactions.urls')),
    path('api/approvals/', include('apps.approvals.urls')),
    # path('api/notifications/', include('apps.notifications.urls')),
    path('api/audit/', include('apps.audit.urls')),
    # Django built-in authentication URLs
    path('accounts/', include('django.contrib.auth.urls')),
    path('', include('apps.dashboard.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    
    # Django Debug Toolbar
    if 'debug_toolbar' in settings.INSTALLED_APPS:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns
