from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import DepositApproval, WithdrawalApproval, RequestApproval
from .serializers import DepositApprovalSerializer, WithdrawalApprovalSerializer, RequestApprovalSerializer
from apps.transactions.utils import can_user_process_transaction
from apps.transactions.models import Transaction
from apps.audit.models import AuditLog
# from apps.notifications.models import Notification


class PendingApprovalsView(generics.ListAPIView):
    """List pending approvals for the current user"""
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        deposit_approvals = DepositApproval.objects.filter(
            approver=user,
            status='PENDING'
        ).select_related('transaction', 'transaction__account', 'transaction__city', 'transaction__created_by')
        
        withdrawal_approvals = WithdrawalApproval.objects.filter(
            approver=user,
            status='PENDING'
        ).select_related('transaction', 'transaction__account', 'transaction__city', 'transaction__created_by')
        
        # Combine and return both types
        return list(deposit_approvals) + list(withdrawal_approvals)


class DepositApprovalView(generics.UpdateAPIView):
    """Handle deposit approval/rejection"""
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return DepositApproval.objects.filter(
            approver=self.request.user,
            status='PENDING'
        )
    
    def update(self, request, *args, **kwargs):
        approval = self.get_object()
        action = request.data.get('action')
        comments = request.data.get('comments', '')
        
        if action == 'approve':
            success = approval.approve(comments)
            action_name = 'APPROVED'
        elif action == 'reject':
            success = approval.reject(comments)
            action_name = 'REJECTED'
        else:
            return Response({
                'success': False,
                'message': 'Invalid action. Must be "approve" or "reject"'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if success:
            # Log the action
            AuditLog.log_action(
                user=request.user,
                action=f'DEPOSIT_{action_name}',
                description=f'Deposit {action_name.lower()} by {request.user.full_name}',
                content_object=approval.transaction,
                request=request
            )
            
            # Send notification to transaction creator (commented out for basic setup)
            # Notification.create_transaction_status_notification(
            #     user=approval.transaction.created_by,
            #     transaction=approval.transaction,
            #     status=approval.transaction.status
            # )
            
            return Response({
                'success': True,
                'message': f'Deposit {action_name.lower()} successfully',
                'data': {
                    'approval_id': approval.id,
                    'transaction_id': approval.transaction.id,
                    'status': approval.status,
                    'transaction_status': approval.transaction.status
                }
            })
        
        return Response({
            'success': False,
            'message': 'Failed to process approval'
        }, status=status.HTTP_400_BAD_REQUEST)


class WithdrawalApprovalView(generics.UpdateAPIView):
    """Handle withdrawal approval/rejection"""
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return WithdrawalApproval.objects.filter(
            approver=self.request.user,
            status='PENDING'
        )
    
    def update(self, request, *args, **kwargs):
        approval = self.get_object()
        action = request.data.get('action')
        comments = request.data.get('comments', '')
        
        if action == 'approve':
            # Check if account has sufficient balance
            if not approval.transaction.account.can_withdraw(approval.transaction.amount):
                return Response({
                    'success': False,
                    'message': 'Insufficient account balance'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            success = approval.approve(comments)
            action_name = 'APPROVED'
        elif action == 'reject':
            success = approval.reject(comments)
            action_name = 'REJECTED'
        else:
            return Response({
                'success': False,
                'message': 'Invalid action. Must be "approve" or "reject"'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if success:
            # Log the action
            AuditLog.log_action(
                user=request.user,
                action=f'WITHDRAWAL_{action_name}',
                description=f'Withdrawal {action_name.lower()} by {request.user.full_name}',
                content_object=approval.transaction,
                request=request
            )
            
            # Send notification to transaction creator (commented out for basic setup)
            # Notification.create_transaction_status_notification(
            #     user=approval.transaction.created_by,
            #     transaction=approval.transaction,
            #     status=approval.transaction.status
            # )
            
            return Response({
                'success': True,
                'message': f'Withdrawal {action_name.lower()} successfully',
                'data': {
                    'approval_id': approval.id,
                    'transaction_id': approval.transaction.id,
                    'status': approval.status,
                    'transaction_status': approval.transaction.status
                }
            })
        
        return Response({
            'success': False,
            'message': 'Failed to process approval'
        }, status=status.HTTP_400_BAD_REQUEST)


# New 5-role system views
class PendingRequestApprovalsView(generics.ListAPIView):
    """List pending RequestApproval records for the current user"""
    permission_classes = [IsAuthenticated]
    serializer_class = RequestApprovalSerializer
    
    def get_queryset(self):
        user = self.request.user
        return RequestApproval.objects.filter(
            approver=user,
            status='PENDING'
        ).select_related('transaction', 'transaction__account', 'transaction__city', 'transaction__created_by')


class RequestApprovalView(generics.UpdateAPIView):
    """Handle RequestApproval approval/rejection for the 5-role system"""
    permission_classes = [IsAuthenticated]
    serializer_class = RequestApprovalSerializer
    
    def get_queryset(self):
        return RequestApproval.objects.filter(
            approver=self.request.user,
            status='PENDING'
        )
    
    def update(self, request, *args, **kwargs):
        approval = self.get_object()
        action = request.data.get('action')
        comments = request.data.get('comments', '')
        
        # Additional validation: Check if user has already approved this transaction
        existing_approval = RequestApproval.objects.filter(
            transaction=approval.transaction,
            approver=request.user,
            status__in=['APPROVED', 'REJECTED']
        ).first()
        
        if existing_approval:
            return Response({
                'success': False,
                'message': f'You have already {existing_approval.status.lower()} this transaction'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if this approval can be processed (now allows any approver)
        if not approval.can_be_processed():
            return Response({
                'success': False,
                'message': 'Cannot process approval. This approval is not pending.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if action == 'approve':
            # For withdrawals, check if account has sufficient balance
            if approval.transaction.type == 'WITHDRAWAL':
                if not approval.transaction.account.can_withdraw(approval.transaction.amount):
                    return Response({
                        'success': False,
                        'message': 'Insufficient account balance'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            success = approval.approve(comments)
            action_name = 'APPROVED'
        elif action == 'reject':
            success = approval.reject(comments)
            action_name = 'REJECTED'
        else:
            return Response({
                'success': False,
                'message': 'Invalid action. Must be "approve" or "reject"'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if success:
            # Log the action
            AuditLog.log_action(
                user=request.user,
                action=f'REQUEST_{action_name}',
                description=f'Request {action_name.lower()} by {request.user.full_name} (Level {approval.approval_level})',
                content_object=approval.transaction,
                request=request
            )
            
            # Send notification to transaction creator (commented out for basic setup)
            # Notification.create_transaction_status_notification(
            #     user=approval.transaction.created_by,
            #     transaction=approval.transaction,
            #     status=approval.transaction.status
            # )
            
            return Response({
                'success': True,
                'message': f'Request {action_name.lower()} successfully',
                'data': {
                    'approval_id': approval.id,
                    'transaction_id': approval.transaction.id,
                    'approval_level': approval.approval_level,
                    'status': approval.status,
                    'transaction_status': approval.transaction.status
                }
            })
        
        return Response({
            'success': False,
            'message': 'Failed to process approval'
        }, status=status.HTTP_400_BAD_REQUEST)
