from django.conf import settings


def get_approval_progress(transaction):
    """
    Get approval progress for a transaction using the new 5-role system
    Now allows any approver to approve regardless of level
    """
    from apps.approvals.models import RequestApproval, DepositApproval, WithdrawalApproval
    
    # Use new RequestApproval system if available
    if hasattr(transaction, 'requestapproval_set'):
        approvals = RequestApproval.objects.filter(transaction=transaction)
        
        # Determine required approval count based on transaction type
        if transaction.type == 'DEPOSIT':
            required_count = 3  # Deposits need 3 approvals (any level)
        else:  # WITHDRAWAL
            required_count = 5  # Withdrawals need 5 approvals (any level)
        
        # Count approvals regardless of level
        approved_count = approvals.filter(status='APPROVED').count()
        rejected_count = approvals.filter(status='REJECTED').count()
        pending_count = approvals.filter(status='PENDING').count()
        
        # Transaction is complete when we have enough approvals
        is_complete = approved_count >= required_count
        is_rejected = rejected_count > 0
        
        return {
            'approved': approved_count,
            'rejected': rejected_count,
            'pending': pending_count,
            'required': required_count,
            'total': approvals.count(),
            'is_complete': is_complete,
            'is_rejected': is_rejected,
            'approved_levels': [a.approval_level for a in approvals.filter(status='APPROVED')],
            'rejected_levels': [a.approval_level for a in approvals.filter(status='REJECTED')],
            'pending_levels': [a.approval_level for a in approvals.filter(status='PENDING')],
            'required_levels': list(range(1, required_count + 1))
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
    Get any pending approver for a transaction (no longer sequential)
    """
    from apps.approvals.models import RequestApproval
    
    # Find any pending approval
    next_approval = RequestApproval.objects.filter(
        transaction=transaction,
        status='PENDING'
    ).first()
    
    return next_approval.approver if next_approval else None


def can_user_process_transaction(user, transaction):
    """
    Check if a user can process a specific transaction
    Now allows any approver to process any transaction
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
    
    # Any approver can now process their approval
    return approval.can_be_processed()
