from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from apps.transactions.models import Transaction
from apps.cities.models import City, Account
from apps.transactions.utils import create_request_approvals
from decimal import Decimal, InvalidOperation


def home_view(request):
    """Home view - redirect authenticated users to dashboard, show landing page for others"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    else:
        return render(request, 'home.html')


@login_required
def dashboard_view(request):
    """Dashboard view with real-time statistics"""
    from apps.transactions.models import Transaction
    from apps.cities.models import Account
    from apps.approvals.models import RequestApproval
    from django.db.models import Sum, Count, Q
    from django.utils import timezone
    from datetime import datetime, timedelta
    
    # Get user's city for filtering
    user_city = request.user.city if hasattr(request.user, 'city') else None
    
    # Base querysets
    transactions_qs = Transaction.objects.all()
    if user_city:
        transactions_qs = transactions_qs.filter(city=user_city)
    
    # Calculate statistics
    total_balance = Account.objects.filter(city=user_city).aggregate(
        total=Sum('balance')
    )['total'] or Decimal('0.00')
    
    # Pending approvals for current user
    pending_approvals = []
    if request.user.can_approve_requests():
        pending_approvals = RequestApproval.objects.filter(
            approver=request.user,
            status='PENDING'
        ).select_related('transaction', 'transaction__account', 'transaction__city', 'transaction__created_by')
    
    # This month transactions
    this_month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    this_month_transactions = transactions_qs.filter(created_at__gte=this_month_start).count()
    
    # Recent transactions
    recent_transactions = transactions_qs.order_by('-created_at')[:5]
    
    # Role-specific data
    role_data = {
        'can_create_requests': request.user.can_create_requests(),
        'can_approve_requests': request.user.can_approve_requests(),
    }
    
    if role_data['can_approve_requests']:
        role_data['approval_level'] = request.user.get_approval_level()
        role_data['my_approvals'] = RequestApproval.objects.filter(approver=request.user).count()
        role_data['my_approved_count'] = RequestApproval.objects.filter(approver=request.user, status='APPROVED').count()
    
    if role_data['can_create_requests']:
        role_data['my_transactions'] = transactions_qs.filter(created_by=request.user).count()
        role_data['pending_my_transactions'] = transactions_qs.filter(created_by=request.user, status='PENDING').count()
    
    context = {
        'user_name': request.user.full_name,
        'user_role': request.user.role,
        'stats': {
            'total_balance': total_balance,
            'pending_approvals': len(pending_approvals),
            'this_month_transactions': this_month_transactions,
            'active_users': 1,  # For now, just show 1
        },
        'recent_transactions': recent_transactions,
        'pending_approvals': pending_approvals,
        'role_data': role_data,
    }
    
    return render(request, 'index.html', context)


@login_required
def create_transaction_view(request):
    """View for creating new transactions (deposits/withdrawals)"""
    
    # Check if user can create requests
    if not request.user.can_create_requests():
        messages.error(request, 'Only users with INITIATOR role can create requests.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        transaction_type = request.POST.get('type')
        amount = request.POST.get('amount')
        description = request.POST.get('description')
        
        # Validate required fields
        if not all([transaction_type, amount, description]):
            messages.error(request, 'All fields are required.')
            return redirect('create_transaction')
        
        try:
            amount = Decimal(amount)
            if amount <= 0:
                raise ValueError('Amount must be positive')
        except (InvalidOperation, ValueError) as e:
            messages.error(request, f'Invalid amount: {str(e)}')
            return redirect('create_transaction')
        
        # Get user's city and account
        user_city = request.user.city
        if not user_city:
            messages.error(request, 'No city assigned to your account.')
            return redirect('create_transaction')
        
        account = Account.objects.filter(city=user_city).first()
        if not account:
            messages.error(request, 'No account found for your city.')
            return redirect('create_transaction')
        
        # For withdrawals, check balance
        if transaction_type == 'WITHDRAWAL' and not account.can_withdraw(amount):
            messages.error(request, 'Insufficient account balance.')
            return redirect('create_transaction')
        
        # Create transaction
        try:
            transaction = Transaction.objects.create(
                type=transaction_type,
                amount=amount,
                description=description,
                account=account,
                city=user_city,
                created_by=request.user
            )
            
            # Create approval records
            create_request_approvals(transaction)
            
            messages.success(request, f'{transaction_type.title()} request created successfully! Reference: {transaction.reference}')
            return redirect('dashboard')
            
        except Exception as e:
            messages.error(request, f'Error creating transaction: {str(e)}')
            return redirect('create_transaction')
    
    # GET request - show form
    user_city = request.user.city
    account = Account.objects.filter(city=user_city).first() if user_city else None
    pre_selected_type = request.GET.get('type', '')
    
    context = {
        'user_city': user_city,
        'account': account,
        'account_balance': account.balance if account else Decimal('0.00'),
        'pre_selected_type': pre_selected_type,
    }
    
    return render(request, 'transactions/create_transaction.html', context)


@login_required
def transaction_detail_view(request, transaction_id):
    """View for displaying transaction details"""
    try:
        transaction = Transaction.objects.get(id=transaction_id)
        
        # Check if user can view this transaction
        if not request.user.can_create_requests() and transaction.created_by != request.user:
            if not request.user.can_approve_requests():
                messages.error(request, 'You do not have permission to view this transaction.')
                return redirect('dashboard')
        
        context = {
            'transaction': transaction,
            'can_approve': request.user.can_approve_requests(),
        }
        
        return render(request, 'transactions/transaction_detail.html', context)
        
    except Transaction.DoesNotExist:
        messages.error(request, 'Transaction not found.')
        return redirect('dashboard')


@login_required
def transactions_list_view(request):
    """View for listing all transactions"""
    transactions = Transaction.objects.select_related('account', 'city', 'created_by').order_by('-created_at')
    
    # Filter by city if not admin
    if request.user.city:
        transactions = transactions.filter(city=request.user.city)
    
    context = {
        'transactions': transactions,
        'user_role': request.user.role,
    }
    
    return render(request, 'transactions/transactions_list.html', context)


@login_required
def approvals_list_view(request):
    """View for listing pending approvals"""
    if not request.user.can_approve_requests():
        messages.error(request, 'You do not have permission to view approvals.')
        return redirect('dashboard')
    
    from apps.approvals.models import RequestApproval
    
    # Get pending approvals for this user
    pending_approvals = RequestApproval.objects.filter(
        approver=request.user,
        status='PENDING'
    ).select_related(
        'transaction', 'transaction__account', 'transaction__city', 'transaction__created_by'
    ).order_by('approval_level', 'created_at')
    
    context = {
        'pending_approvals': pending_approvals,
        'user_role': request.user.role,
    }
    
    return render(request, 'approvals/approvals_list.html', context)


@login_required
def process_approval_view(request, transaction_id):
    """Process approval or rejection of a transaction"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)
    
    if not request.user.can_approve_requests():
        return JsonResponse({'success': False, 'message': 'You do not have permission to approve requests'}, status=403)
    
    from apps.approvals.models import RequestApproval
    from apps.transactions.models import Transaction
    # from apps.audit.models import AuditLog  # Temporarily disabled
    
    try:
        transaction = Transaction.objects.get(id=transaction_id)
        approval = RequestApproval.objects.get(
            transaction=transaction,
            approver=request.user,
            status='PENDING'
        )
    except (Transaction.DoesNotExist, RequestApproval.DoesNotExist):
        return JsonResponse({'success': False, 'message': 'Transaction or approval not found'}, status=404)
    
    action = request.POST.get('action')
    comments = request.POST.get('comments', '')
    
    if action == 'approve':
        # Check if this approval can be processed (sequential approval)
        if not approval.can_be_processed():
            return JsonResponse({
                'success': False, 
                'message': 'Cannot process approval. Previous approval levels must be completed first.'
            }, status=400)
        
        # For withdrawals, check if account has sufficient balance
        if transaction.type == 'WITHDRAWAL':
            if not transaction.account.can_withdraw(transaction.amount):
                return JsonResponse({
                    'success': False,
                    'message': 'Insufficient account balance'
                }, status=400)
        
        success = approval.approve(comments)
        action_name = 'APPROVED'
    elif action == 'reject':
        success = approval.reject(comments)
        action_name = 'REJECTED'
    else:
        return JsonResponse({
            'success': False,
            'message': 'Invalid action. Must be "approve" or "reject"'
        }, status=400)
    
    if success:
        # Log the action (temporarily disabled due to SQLite integer overflow)
        # AuditLog.log_action(
        #     user=request.user,
        #     action=f'REQUEST_{action_name}',
        #     description=f'Request {action_name.lower()} by {request.user.full_name} (Level {approval.approval_level})',
        #     content_object=transaction,
        #     request=request
        # )
        
        return JsonResponse({
            'success': True,
            'message': f'Transaction {action_name.lower()} successfully',
            'data': {
                'approval_id': approval.id,
                'transaction_id': transaction.id,
                'approval_level': approval.approval_level,
                'status': approval.status,
                'transaction_status': transaction.status
            }
        })
    
    return JsonResponse({
        'success': False,
        'message': 'Failed to process approval'
    }, status=400)


@login_required
def reports_view(request):
    """View for displaying reports and analytics"""
    from django.db.models import Sum, Count, Q
    from django.utils import timezone
    from datetime import datetime, timedelta
    
    # Get user's city for filtering
    user_city = request.user.city if request.user.role != 'ADMIN' else None
    
    # Base querysets
    transactions_qs = Transaction.objects.all()
    if user_city:
        transactions_qs = transactions_qs.filter(city=user_city)
    
    # Calculate various statistics
    this_month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_month_start = (this_month_start - timedelta(days=1)).replace(day=1)
    
    # Monthly statistics
    this_month_stats = transactions_qs.filter(created_at__gte=this_month_start).aggregate(
        total_transactions=Count('id'),
        total_amount=Sum('amount'),
        deposits=Count('id', filter=Q(type='DEPOSIT')),
        withdrawals=Count('id', filter=Q(type='WITHDRAWAL')),
        executed=Count('id', filter=Q(status='EXECUTED')),
    )
    
    last_month_stats = transactions_qs.filter(
        created_at__gte=last_month_start,
        created_at__lt=this_month_start
    ).aggregate(
        total_transactions=Count('id'),
        total_amount=Sum('amount'),
        deposits=Count('id', filter=Q(type='DEPOSIT')),
        withdrawals=Count('id', filter=Q(type='WITHDRAWAL')),
        executed=Count('id', filter=Q(status='EXECUTED')),
    )
    
    # Recent transactions
    recent_transactions = transactions_qs.order_by('-created_at')[:10]
    
    # Status breakdown
    status_breakdown = transactions_qs.values('status').annotate(count=Count('id'))
    
    context = {
        'this_month_stats': this_month_stats,
        'last_month_stats': last_month_stats,
        'recent_transactions': recent_transactions,
        'status_breakdown': status_breakdown,
        'user_city': user_city,
    }
    
    return render(request, 'reports/reports.html', context)