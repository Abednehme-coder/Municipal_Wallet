from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogListView(generics.ListAPIView):
    """List audit logs (admin and auditor only)"""
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Only allow admin and auditor roles to view audit logs
        if self.request.user.role not in ['ADMIN', 'AUDITOR']:
            return AuditLog.objects.none()
        
        return AuditLog.objects.all().order_by('-created_at')
