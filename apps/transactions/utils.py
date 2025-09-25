from django.conf import settings


def get_approval_progress(transaction):
    """
    Get approval progress for a transaction using any-order approval system
    """
    from apps.approvals.models import RequestApproval, DepositApproval, WithdrawalApproval
    
    # Use new RequestApproval system if available
    if hasattr(transaction, 'requestapproval_set'):
        approvals = RequestApproval.objects.filter(transaction=transaction)
        
        # Get required approval count from dynamic configuration
        try:
            from apps.admin_panel.models import ApprovalConfiguration
            required_count = ApprovalConfiguration.get_required_approvals(transaction.type)
        except:
            # Fallback to default values
            required_count = 3 if transaction.type == 'DEPOSIT' else 5
        
        # Count approvals (any order)
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
            'approved_approvers': [a.approver.full_name for a in approvals.filter(status='APPROVED')],
            'rejected_approvers': [a.approver.full_name for a in approvals.filter(status='REJECTED')],
            'pending_approvers': [a.approver.full_name for a in approvals.filter(status='PENDING')]
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
    Create approval records for a transaction using any-order approval system
    """
    from apps.approvals.models import RequestApproval
    from apps.accounts.models import User
    from django.conf import settings
    
    # Get required approvers from dynamic configuration
    try:
        from apps.admin_panel.models import ApproverAssignment, ApprovalConfiguration
        required_count = ApprovalConfiguration.get_required_approvals(transaction.type)
        assignments = ApproverAssignment.get_approvers_for_transaction_type(transaction.type)
        
        # Get approvers from assignments
        approvers = [a.approver for a in assignments]
        
        # If not enough assignments exist, fall back to role-based users
        if len(approvers) < required_count:
            existing_approver_ids = [a.id for a in approvers]
            fallback_approvers = User.objects.filter(
                role__in=['APPROVER_1', 'APPROVER_2', 'APPROVER_3', 'APPROVER_4', 'APPROVER_5'],
                is_active=True
            ).exclude(id__in=existing_approver_ids)
            
            # Add fallback approvers until we have enough
            for approver in fallback_approvers:
                if len(approvers) >= required_count:
                    break
                approvers.append(approver)
        
        if len(approvers) < required_count:
            raise ValueError(f"Not enough active approvers assigned for {transaction.type} transactions. Required: {required_count}, Found: {len(approvers)}")
            
    except Exception:
        # Fallback to settings-based fixed roles
        if transaction.type == 'DEPOSIT':
            required_count = getattr(settings, 'DEPOSIT_APPROVALS_REQUIRED', 3)
        else:  # WITHDRAWAL
            required_count = getattr(settings, 'WITHDRAWAL_APPROVALS_REQUIRED', 5)
        
        approvers = []
        for i in range(1, required_count + 1):
            approver = User.get_user_by_role(f'APPROVER_{i}')
            if not approver:
                raise ValueError(f"APPROVER_{i} must be configured in the system")
            approvers.append(approver)
    
    # Create approval records (no approval_level needed)
    approvals = []
    for approver in approvers:
        approvals.append(
            RequestApproval(transaction=transaction, approver=approver)
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


def can_user_view_transaction(user, transaction):
    """
    Check if a user can view a specific transaction based on their privileges
    """
    # Admins can view all transactions
    if user.is_superuser or user.is_staff:
        return True
    
    # Initiators can view their own transactions
    if user.can_create_requests() and transaction.created_by == user:
        return True
    
    # Approvers can view transactions they're assigned to approve
    if user.can_approve_requests():
        from apps.approvals.models import RequestApproval
        return RequestApproval.objects.filter(
            transaction=transaction,
            approver=user
        ).exists()
    
    return False


def can_user_cancel_transaction(user, transaction):
    """
    Check if a user can cancel a specific transaction
    """
    # Admins can cancel any transaction
    if user.is_superuser or user.is_staff:
        return True
    
    # Initiators can cancel their own transactions
    if user.can_create_requests() and transaction.created_by == user:
        return True
    
    return False


def get_user_visible_transactions(user, base_queryset=None):
    """
    Get transactions that a user is allowed to see based on their privileges
    """
    from .models import Transaction
    
    if base_queryset is None:
        base_queryset = Transaction.objects.all()
    
    # Filter by city if not admin
    if not (user.is_superuser or user.is_staff) and hasattr(user, 'city') and user.city:
        base_queryset = base_queryset.filter(city=user.city)
    
    # Apply privilege-based filtering
    if user.can_create_requests():
        # Initiators can see their own transactions
        return base_queryset.filter(created_by=user)
    elif user.can_approve_requests():
        # Approvers can only see transactions they're assigned to approve
        from apps.approvals.models import RequestApproval
        assigned_transaction_ids = RequestApproval.objects.filter(
            approver=user
        ).values_list('transaction_id', flat=True)
        return base_queryset.filter(id__in=assigned_transaction_ids)
    elif user.is_superuser or user.is_staff:
        # Admins can see all transactions
        return base_queryset
    else:
        # Non-privileged users see no transactions
        return base_queryset.none()


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
