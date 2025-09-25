from rest_framework import generics, status, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from django.utils import timezone
from .models import Transaction
from .serializers import (
    TransactionSerializer, TransactionCreateSerializer, 
    TransactionUpdateSerializer, TransactionCancelSerializer
)
from .utils import get_approval_progress, check_transaction_status, create_request_approvals, can_user_process_transaction, can_user_view_transaction, can_user_cancel_transaction, get_user_visible_transactions
from apps.audit.models import AuditLog
# from apps.notifications.models import Notification
from apps.approvals.models import DepositApproval, WithdrawalApproval, RequestApproval
from django.conf import settings


class TransactionListView(generics.ListCreateAPIView):
    """List and create transactions"""
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['type', 'status', 'account', 'city']
    search_fields = ['description', 'reference']
    ordering_fields = ['created_at', 'amount']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return TransactionCreateSerializer
        return TransactionSerializer
    
    def get_queryset(self):
        return get_user_visible_transactions(self.request.user)
    
    def create(self, request, *args, **kwargs):
        # Check if user can create requests
        if not request.user.can_create_requests():
            return Response({
                'success': False,
                'message': 'Only users with INITIATOR role can create requests'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        transaction = serializer.save()
        
        # Create approval records using new role system
        try:
            create_request_approvals(transaction)
        except ValueError as e:
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Log transaction creation
        AuditLog.log_action(
            user=request.user,
            action='TRANSACTION_CREATED',
            description=f'Transaction {transaction.reference} created',
            content_object=transaction,
            request=request
        )
        
        # Send notifications to approvers (commented out for basic setup)
        # self._send_approval_notifications(transaction)
        
        return Response({
            'success': True,
            'message': 'Transaction created successfully',
            'data': TransactionSerializer(transaction).data
        }, status=status.HTTP_201_CREATED)
    
    def _create_approval_records(self, transaction):
        """Create approval records for the transaction"""
        # Get eligible approvers
        approvers = self._get_eligible_approvers(transaction.city)
        
        # Determine required approvals
        required_approvals = (
            settings.DEPOSIT_APPROVALS_REQUIRED if transaction.type == 'DEPOSIT'
            else settings.WITHDRAWAL_APPROVALS_REQUIRED
        )
        
        if len(approvers) < required_approvals:
            raise ValueError(f"Insufficient approvers. Required: {required_approvals}, Available: {len(approvers)}")
        
        # Create approval records
        approvers_to_approve = approvers[:required_approvals]
        
        if transaction.type == 'DEPOSIT':
            DepositApproval.objects.bulk_create([
                DepositApproval(transaction=transaction, approver=approver)
                for approver in approvers_to_approve
            ])
        else:
            WithdrawalApproval.objects.bulk_create([
                WithdrawalApproval(transaction=transaction, approver=approver)
                for approver in approvers_to_approve
            ])
    
    def _get_eligible_approvers(self, city):
        """Get eligible approvers for a city"""
        return User.objects.filter(
            city=city,
            is_active=True,
            role__in=['ADMIN', 'MAYOR', 'TREASURER', 'COUNCIL_MEMBER']
        ).exclude(id=self.request.user.id)
    
    # def _send_approval_notifications(self, transaction):
    #     """Send notifications to approvers"""
    #     # Get approvers for this transaction
    #     if transaction.type == 'DEPOSIT':
    #         approvers = DepositApproval.objects.filter(transaction=transaction).select_related('approver')
    #     else:
    #         approvers = WithdrawalApproval.objects.filter(transaction=transaction).select_related('approver')
    #     
    #     for approval in approvers:
    #         Notification.create_approval_notification(
    #             user=approval.approver,
    #             transaction=transaction,
    #             approver_name=transaction.created_by.full_name
    #         )


class TransactionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a transaction"""
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return TransactionUpdateSerializer
        return TransactionSerializer
    
    def get_queryset(self):
        return get_user_visible_transactions(self.request.user)
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        transaction = serializer.save()
        
        # Log transaction update
        AuditLog.log_action(
            user=request.user,
            action='TRANSACTION_UPDATED',
            description=f'Transaction {transaction.reference} updated',
            content_object=transaction,
            request=request
        )
        
        return Response({
            'success': True,
            'message': 'Transaction updated successfully',
            'data': TransactionSerializer(transaction).data
        })
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Only allow deletion of pending transactions
        if instance.status != 'PENDING':
            return Response({
                'success': False,
                'message': 'Only pending transactions can be deleted'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Log transaction deletion
        AuditLog.log_action(
            user=request.user,
            action='TRANSACTION_CANCELLED',
            description=f'Transaction {instance.reference} deleted',
            content_object=instance,
            request=request
        )
        
        instance.delete()
        return Response({
            'success': True,
            'message': 'Transaction deleted successfully'
        })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_transaction(request, pk):
    """Cancel a transaction"""
    try:
        transaction = Transaction.objects.get(pk=pk)
    except Transaction.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Transaction not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Check permissions - user must be able to cancel this transaction
    if not can_user_cancel_transaction(request.user, transaction):
        return Response({
            'success': False,
            'message': 'Not authorized to cancel this transaction'
        }, status=status.HTTP_403_FORBIDDEN)
    
    serializer = TransactionCancelSerializer(data=request.data, instance=transaction)
    if serializer.is_valid():
        reason = serializer.validated_data.get('reason', 'No reason provided')
        transaction.cancel(reason)
        
        # Log cancellation
        AuditLog.log_action(
            user=request.user,
            action='TRANSACTION_CANCELLED',
            description=f'Transaction {transaction.reference} cancelled',
            content_object=transaction,
            request=request
        )
        
        return Response({
            'success': True,
            'message': 'Transaction cancelled successfully',
            'data': TransactionSerializer(transaction).data
        })
    
    return Response({
        'success': False,
        'message': 'Cancellation failed',
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def transaction_approval_progress(request, pk):
    """Get approval progress for a transaction"""
    try:
        transaction = Transaction.objects.get(pk=pk)
    except Transaction.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Transaction not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Check permissions - user must be able to view this transaction
    if not can_user_view_transaction(request.user, transaction):
        return Response({
            'success': False,
            'message': 'Not authorized to view this transaction'
        }, status=status.HTTP_403_FORBIDDEN)
    
    progress = get_approval_progress(transaction)
    
    return Response({
        'success': True,
        'data': progress
    })
