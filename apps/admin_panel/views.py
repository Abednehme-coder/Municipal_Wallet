from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.core.exceptions import ValidationError
from .models import ApproverAssignment, ApprovalConfiguration
from apps.accounts.models import User


def is_admin(user):
    """Check if user is an admin"""
    return user.is_superuser or user.is_staff


@login_required
@user_passes_test(is_admin)
def approver_management_view(request):
    """Main view for managing approvers"""
    deposit_assignments = ApproverAssignment.get_approvers_for_transaction_type('DEPOSIT', active_only=False)
    withdrawal_assignments = ApproverAssignment.get_approvers_for_transaction_type('WITHDRAWAL', active_only=False)
    
    # Get available approvers (users with approver roles)
    all_approvers = User.objects.filter(
        role__in=['APPROVER_1', 'APPROVER_2', 'APPROVER_3', 'APPROVER_4', 'APPROVER_5'],
        is_active=True
    ).order_by('role')
    
    # Filter out already assigned approvers for each transaction type (only active ones)
    assigned_deposit_ids = [a.approver.id for a in deposit_assignments.filter(is_active=True)]
    assigned_withdrawal_ids = [a.approver.id for a in withdrawal_assignments.filter(is_active=True)]
    
    available_deposit_approvers = all_approvers.exclude(id__in=assigned_deposit_ids)
    available_withdrawal_approvers = all_approvers.exclude(id__in=assigned_withdrawal_ids)
    
    # Get approval configurations
    deposit_config = ApprovalConfiguration.objects.filter(transaction_type='DEPOSIT').first()
    withdrawal_config = ApprovalConfiguration.objects.filter(transaction_type='WITHDRAWAL').first()
    
    # Calculate active counts for display
    active_deposit_count = deposit_assignments.filter(is_active=True).count()
    active_withdrawal_count = withdrawal_assignments.filter(is_active=True).count()
    
    context = {
        'deposit_assignments': deposit_assignments,
        'withdrawal_assignments': withdrawal_assignments,
        'available_approvers': all_approvers,  # Keep for backward compatibility
        'available_deposit_approvers': available_deposit_approvers,
        'available_withdrawal_approvers': available_withdrawal_approvers,
        'deposit_config': deposit_config,
        'withdrawal_config': withdrawal_config,
        'active_deposit_count': active_deposit_count,
        'active_withdrawal_count': active_withdrawal_count,
    }
    
    return render(request, 'admin_panel/approver_management.html', context)


@login_required
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def assign_approver_view(request):
    """Assign an approver to a transaction type (no levels)"""
    try:
        transaction_type = request.POST.get('transaction_type')
        approver_id = request.POST.get('approver_id')
        
        if not all([transaction_type, approver_id]):
            return JsonResponse({
                'success': False,
                'message': 'All fields are required'
            }, status=400)
        
        approver = get_object_or_404(User, id=approver_id)
        
        # Check if this approver is already assigned to this transaction type
        existing_assignment = ApproverAssignment.objects.filter(
            transaction_type=transaction_type,
            approver=approver
        ).first()
        
        if existing_assignment:
            # Update existing assignment
            existing_assignment.is_active = True
            existing_assignment.save()
        else:
            # Create new assignment
            ApproverAssignment.objects.create(
                transaction_type=transaction_type,
                approver=approver,
                is_active=True
            )
        
        # Auto-update required count based on active approvers
        active_count = ApproverAssignment.objects.filter(
            transaction_type=transaction_type,
            is_active=True
        ).count()
        
        config, created = ApprovalConfiguration.objects.get_or_create(
            transaction_type=transaction_type,
            defaults={'required_approvals': active_count}
        )
        if not created:
            config.required_approvals = active_count
            config.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Approver {approver.full_name} assigned to {transaction_type}. Required count updated to {active_count}.'
        })
        
    except ValidationError as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error assigning approver: {str(e)}'
        }, status=500)


@login_required
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def remove_approver_view(request):
    """Remove an approver assignment"""
    try:
        assignment_id = request.POST.get('assignment_id')
        
        if not assignment_id:
            return JsonResponse({
                'success': False,
                'message': 'Assignment ID is required'
            }, status=400)
        
        assignment = get_object_or_404(ApproverAssignment, id=assignment_id)
        approver_name = assignment.approver.full_name
        transaction_type = assignment.get_transaction_type_display()
        transaction_type_code = assignment.transaction_type
        
        assignment.delete()
        
        # Auto-update required count based on remaining active approvers
        active_count = ApproverAssignment.objects.filter(
            transaction_type=transaction_type_code,
            is_active=True
        ).count()
        
        config, created = ApprovalConfiguration.objects.get_or_create(
            transaction_type=transaction_type_code,
            defaults={'required_approvals': active_count}
        )
        if not created:
            config.required_approvals = active_count
            config.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Approver {approver_name} removed from {transaction_type}. Required count updated to {active_count}.'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error removing approver: {str(e)}'
        }, status=500)


@login_required
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def toggle_approver_status_view(request):
    """Toggle active status of an approver assignment"""
    try:
        assignment_id = request.POST.get('assignment_id')
        
        if not assignment_id:
            return JsonResponse({
                'success': False,
                'message': 'Assignment ID is required'
            }, status=400)
        
        assignment = get_object_or_404(ApproverAssignment, id=assignment_id)
        assignment.is_active = not assignment.is_active
        assignment.save()
        
        status_text = "activated" if assignment.is_active else "deactivated"
        
        # Auto-update required count based on active approvers
        active_count = ApproverAssignment.objects.filter(
            transaction_type=assignment.transaction_type,
            is_active=True
        ).count()
        
        config, created = ApprovalConfiguration.objects.get_or_create(
            transaction_type=assignment.transaction_type,
            defaults={'required_approvals': active_count}
        )
        if not created:
            config.required_approvals = active_count
            config.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Approver {assignment.approver.full_name} {status_text} for {assignment.get_transaction_type_display()}. Required count updated to {active_count}.'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error updating approver status: {str(e)}'
        }, status=500)


@login_required
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def update_approval_config_view(request):
    """Update approval configuration for transaction types"""
    try:
        transaction_type = request.POST.get('transaction_type')
        required_approvals = int(request.POST.get('required_approvals'))
        
        if not all([transaction_type, required_approvals]):
            return JsonResponse({
                'success': False,
                'message': 'All fields are required'
            }, status=400)
        
        if required_approvals < 1 or required_approvals > 5:
            return JsonResponse({
                'success': False,
                'message': 'Required approvals must be between 1 and 5'
            }, status=400)
        
        config, created = ApprovalConfiguration.objects.get_or_create(
            transaction_type=transaction_type,
            defaults={'required_approvals': required_approvals}
        )
        
        if not created:
            config.required_approvals = required_approvals
            config.save()
        
        return JsonResponse({
            'success': True,
            'message': f'{transaction_type} approval configuration updated to require {required_approvals} approvals'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error updating configuration: {str(e)}'
        }, status=500)


@login_required
@user_passes_test(is_admin)
def approver_statistics_view(request):
    """View statistics about approver assignments"""
    deposit_assignments = ApproverAssignment.objects.filter(transaction_type='DEPOSIT')
    withdrawal_assignments = ApproverAssignment.objects.filter(transaction_type='WITHDRAWAL')
    
    # Count active assignments
    active_deposit_count = deposit_assignments.filter(is_active=True).count()
    active_withdrawal_count = withdrawal_assignments.filter(is_active=True).count()
    
    # Get approval configurations
    deposit_config = ApprovalConfiguration.objects.filter(transaction_type='DEPOSIT').first()
    withdrawal_config = ApprovalConfiguration.objects.filter(transaction_type='WITHDRAWAL').first()
    
    context = {
        'deposit_stats': {
            'total_assignments': deposit_assignments.count(),
            'active_assignments': active_deposit_count,
            'required_approvals': active_deposit_count,  # Use active count instead of config
            'assignments': deposit_assignments.order_by('approver__username')
        },
        'withdrawal_stats': {
            'total_assignments': withdrawal_assignments.count(),
            'active_assignments': active_withdrawal_count,
            'required_approvals': active_withdrawal_count,  # Use active count instead of config
            'assignments': withdrawal_assignments.order_by('approver__username')
        }
    }
    
    return render(request, 'admin_panel/approver_statistics.html', context)
