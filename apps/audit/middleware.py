from django.utils.deprecation import MiddlewareMixin
from .models import AuditLog


class AuditMiddleware(MiddlewareMixin):
    """
    Middleware to automatically log certain actions
    """
    
    def process_request(self, request):
        """Process the request and log login attempts"""
        if request.user.is_authenticated and request.path == '/api/auth/login/':
            # Log login attempts
            AuditLog.log_action(
                user=request.user,
                action='LOGIN',
                description=f'User {request.user.email} logged in',
                request=request
            )
    
    def process_response(self, request, response):
        """Process the response and log logout attempts"""
        if request.user.is_authenticated and request.path == '/api/auth/logout/':
            # Log logout
            AuditLog.log_action(
                user=request.user,
                action='LOGOUT',
                description=f'User {request.user.email} logged out',
                request=request
            )
        
        return response
