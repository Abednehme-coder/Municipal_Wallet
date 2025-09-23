from django.conf import settings


def get_approval_progress(transaction):
    """
    Get approval progress for a transaction using the new 5-role system
    Enforces sequential approval: deposits need approvers 1,2,3; withdrawals need approvers 1,2,3,4,5
    """
    from apps.approvals.models import RequestApproval, DepositApproval, WithdrawalApproval
    
    # Use new RequestApproval system if available
    if hasattr(transaction, 'requestapproval_set'):
        approvals = RequestApproval.objects.filter(transaction=transaction).order_by('approval_level')
        
        # Determine required approval levels based on transaction type
        if transaction.type == 'DEPOSIT':
            required_levels = [1, 2, 3]  # Deposits need approvers 1, 2, 3
        else:  # WITHDRAWAL
            required_levels = [1, 2, 3, 4, 5]  # Withdrawals need approvers 1, 2, 3, 4, 5
        
        # Check if all required levels are approved
        approved_levels = []
        rejected_levels = []
        pending_levels = []
        
        for approval in approvals:
            if approval.approval_level in required_levels:
                if approval.status == 'APPROVED':
                    approved_levels.append(approval.approval_level)
                elif approval.status == 'REJECTED':
                    rejected_levels.append(approval.approval_level)
                else:  # PENDING
                    pending_levels.append(approval.approval_level)
        
        # Transaction is complete only if ALL required levels are approved
        is_complete = len(approved_levels) == len(required_levels)
        is_rejected = len(rejected_levels) > 0
        
        return {
            'approved': len(approved_levels),
            'rejected': len(rejected_levels),
            'pending': len(pending_levels),
            'required': len(required_levels),
            'total': len(required_levels),
            'is_complete': is_complete,
            'is_rejected': is_rejected,
            'approved_levels': approved_levels,
            'rejected_levels': rejected_levels,
            'pending_levels': pending_levels,
            'required_levels': required_levels
        }
    else:
        # Fallback to legacy system
        if transaction.type == 'DEPOSIT':
            approvals = DepositApproval.objects.filter(transaction=transaction)
            required = getattr(settings, 'DEPOSIT_APPROVALS_REQUIRED', 3)
        else:
            approvals = WithdrawalApproval.objects.filter(transaction=transaction)
            required = getattr(settings, 'WITHDRAWAL_APPROVALS_REQUIRED', 5)
        
        approved_count = approvals.filter(status='APPROVED').count()
        rejected_count = approvals.filter(status='REJECTED').count()
        
        return {
            'approved': approved_count,
            'rejected': rejected_count,
            'pending': approvals.filter(status='PENDING').count(),
            'required': required,
            'total': approvals.count(),
            'is_complete': approved_count >= required,
            'is_rejected': rejected_count > 0
        }


def check_transaction_status(transaction):
    """
    Check and update transaction status based on approvals
    """
    progress = get_approval_progress(transaction)
    
    if progress['is_rejected']:
        transaction.status = 'REJECTED'
    elif progress['is_complete']:
        transaction.status = 'APPROVED'
        # Automatically execute approved transactions
        if transaction.can_be_executed():
            execution_result = transaction.execute()
            if execution_result:
                transaction.status = 'EXECUTED'
    else:
        transaction.status = 'PENDING'
    
    transaction.save(update_fields=['status'])
    return transaction.status


def create_request_approvals(transaction):
    """
    Create approval records for a transaction based on transaction type
    - Deposits: 3 approvers required
    - Withdrawals: 5 approvers required
    """
    from apps.approvals.models import RequestApproval
    from apps.accounts.models import User
    from django.conf import settings
    
    # Determine number of approvals required based on transaction type
    if transaction.type == 'DEPOSIT':
        required_approvers = getattr(settings, 'DEPOSIT_APPROVALS_REQUIRED', 3)
    else:  # WITHDRAWAL
        required_approvers = getattr(settings, 'WITHDRAWAL_APPROVALS_REQUIRED', 5)
    
    # Get approvers based on required count
    approvers = []
    for i in range(1, required_approvers + 1):
        approver = User.get_user_by_role(f'APPROVER_{i}')
        if not approver:
            raise ValueError(f"APPROVER_{i} must be configured in the system")
        approvers.append(approver)
    
    # Create approval records
    approvals = []
    for i, approver in enumerate(approvers, 1):
        approvals.append(
            RequestApproval(transaction=transaction, approver=approver, approval_level=i)
        )
    
    RequestApproval.objects.bulk_create(approvals)
    return approvals


def get_next_approver_for_transaction(transaction):
    """
    Get the next approver who should process a transaction
    """
    from apps.approvals.models import RequestApproval
    
    # Find the first pending approval
    next_approval = RequestApproval.objects.filter(
        transaction=transaction,
        status='PENDING'
    ).order_by('approval_level').first()
    
    return next_approval.approver if next_approval else None


def can_user_process_transaction(user, transaction):
    """
    Check if a user can process a specific transaction
    """
    from apps.approvals.models import RequestApproval
    
    if not user.can_approve_requests():
        return False
    
    # Check if user has a pending approval for this transaction
    approval = RequestApproval.objects.filter(
        transaction=transaction,
        approver=user,
        status='PENDING'
    ).first()
    
    if not approval:
        return False
    
    # Check if this approval can be processed (sequential approval)
    return approval.can_be_processed()
