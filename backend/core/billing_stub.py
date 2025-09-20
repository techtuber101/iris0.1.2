"""
Stub billing router for when billing is disabled.

This module provides harmless stub responses for all billing endpoints
when BILLING_ENABLED is False, ensuring the application doesn't crash
due to missing Stripe configuration.
"""

from fastapi import APIRouter, Depends
from typing import Dict, Any
from core.utils.auth_utils import verify_and_get_user_id_from_jwt
from core.utils.logger import logger

router = APIRouter(prefix="/billing", tags=["billing"])

@router.get("/check")
async def check_billing_status(
    account_id: str = Depends(verify_and_get_user_id_from_jwt)
) -> Dict[str, Any]:
    """Stub endpoint for billing status check."""
    logger.debug(f"Billing disabled - returning stub response for user {account_id}")
    return {
        'can_run': True, 
        'message': 'Billing disabled - unlimited usage', 
        'balance': 10000,
        'tier': 'unlimited'
    }

@router.get("/check-status")
async def check_status(
    account_id: str = Depends(verify_and_get_user_id_from_jwt)
) -> Dict[str, Any]:
    """Stub endpoint for billing status check."""
    logger.debug(f"Billing disabled - returning stub status for user {account_id}")
    return {
        "can_run": True,
        "message": "Billing disabled - unlimited usage",
        "subscription": {
            "price_id": "disabled",
            "plan_name": "Billing Disabled"
        },
        "credit_balance": 999999,
        "can_purchase_credits": False
    }

@router.get("/project-limits")
async def get_project_limits(
    account_id: str = Depends(verify_and_get_user_id_from_jwt)
) -> Dict[str, Any]:
    """Stub endpoint for project limits."""
    logger.debug(f"Billing disabled - returning unlimited project limits for user {account_id}")
    return {
        'tier': 'unlimited',
        'tier_display_name': 'Unlimited',
        'current_count': 0,
        'limit': 999999,
        'can_create': True,
        'percent_used': 0
    }

@router.post("/deduct")
async def deduct_token_usage(
    account_id: str = Depends(verify_and_get_user_id_from_jwt)
) -> Dict[str, Any]:
    """Stub endpoint for token usage deduction."""
    logger.debug(f"Billing disabled - skipping token deduction for user {account_id}")
    return {
        'success': True, 
        'cost': 0, 
        'new_balance': 999999
    }

@router.get("/balance")
async def get_credit_balance(
    account_id: str = Depends(verify_and_get_user_id_from_jwt)
) -> Dict[str, Any]:
    """Stub endpoint for credit balance."""
    logger.debug(f"Billing disabled - returning unlimited balance for user {account_id}")
    return {
        'balance': 999999.0,
        'expiring_credits': 0.0,
        'non_expiring_credits': 999999.0,
        'tier': 'unlimited',
        'tier_display_name': 'Unlimited',
        'is_trial': False,
        'trial_status': None,
        'trial_ends_at': None,
        'can_purchase_credits': False,
        'next_credit_grant': None,
        'breakdown': {
            'expiring': 0.0,
            'non_expiring': 999999.0,
            'total': 999999.0
        }
    }

@router.get("/subscription")
async def get_subscription(
    account_id: str = Depends(verify_and_get_user_id_from_jwt)
) -> Dict[str, Any]:
    """Stub endpoint for subscription info."""
    logger.debug(f"Billing disabled - returning stub subscription for user {account_id}")
    return {
        'status': 'disabled',
        'plan_name': 'unlimited',
        'display_plan_name': 'Billing Disabled',
        'price_id': None,
        'subscription': None,
        'subscription_id': None,
        'current_usage': 0,
        'cost_limit': 999999,
        'credit_balance': 999999,
        'can_purchase_credits': False,
        'tier': {
            'name': 'unlimited',
            'credits': 999999.0,
            'display_name': 'Unlimited'
        },
        'is_trial': False,
        'trial_status': None,
        'trial_ends_at': None,
        'credits': {
            'balance': 999999,
            'tier_credits': 999999,
            'lifetime_granted': 999999,
            'lifetime_purchased': 0,
            'lifetime_used': 0,
            'can_purchase_credits': False
        }
    }

@router.get("/available-models")
async def get_available_models(
    account_id: str = Depends(verify_and_get_user_id_from_jwt)
) -> Dict[str, Any]:
    """Stub endpoint for available models."""
    logger.debug(f"Billing disabled - returning all models for user {account_id}")
    return {
        "models": [],
        "subscription_tier": "unlimited",
        "total_models": 0,
        "allowed_models_count": 0
    }

@router.get("/transactions")
async def get_my_transactions(
    account_id: str = Depends(verify_and_get_user_id_from_jwt)
) -> Dict[str, Any]:
    """Stub endpoint for transactions."""
    logger.debug(f"Billing disabled - returning empty transactions for user {account_id}")
    return {
        'transactions': [],
        'pagination': {
            'total': 0,
            'limit': 50,
            'offset': 0,
            'has_more': False
        },
        'current_balance': {
            'total': 999999.0,
            'expiring': 0.0,
            'non_expiring': 999999.0
        }
    }

@router.get("/transactions/summary")
async def get_transactions_summary(
    account_id: str = Depends(verify_and_get_user_id_from_jwt)
) -> Dict[str, Any]:
    """Stub endpoint for transaction summary."""
    logger.debug(f"Billing disabled - returning empty transaction summary for user {account_id}")
    return {
        'period_days': 30,
        'since_date': '2024-01-01T00:00:00Z',
        'current_balance': {
            'total': 999999.0,
            'expiring': 0.0,
            'non_expiring': 999999.0
        },
        'summary': {
            'total_added': 0.0,
            'total_used': 0.0,
            'total_refunded': 0.0,
            'total_expired': 0.0,
            'net_change': 0.0
        },
        'transaction_counts': {},
        'total_transactions': 0
    }

@router.get("/credit-breakdown")
async def get_credit_breakdown(
    account_id: str = Depends(verify_and_get_user_id_from_jwt)
) -> Dict[str, Any]:
    """Stub endpoint for credit breakdown."""
    logger.debug(f"Billing disabled - returning unlimited credit breakdown for user {account_id}")
    return {
        'total_balance': 999999,
        'expiring_credits': 0,
        'non_expiring_credits': 999999,
        'tier': 'unlimited',
        'next_credit_grant': None,
        'recent_purchases': [],
        'message': 'Billing disabled - unlimited credits available'
    }

@router.get("/usage-history")
async def get_usage_history(
    account_id: str = Depends(verify_and_get_user_id_from_jwt)
) -> Dict[str, Any]:
    """Stub endpoint for usage history."""
    logger.debug(f"Billing disabled - returning empty usage history for user {account_id}")
    return {
        'daily_usage': {},
        'total_period_usage': 0,
        'total_period_credits': 0
    }

@router.get("/subscription-commitment/{subscription_id}")
async def get_subscription_commitment(
    subscription_id: str,
    account_id: str = Depends(verify_and_get_user_id_from_jwt)
) -> Dict[str, Any]:
    """Stub endpoint for subscription commitment."""
    logger.debug(f"Billing disabled - returning no commitment for user {account_id}")
    return {
        'has_commitment': False,
        'can_cancel': True,
        'commitment_type': None,
        'months_remaining': None,
        'commitment_end_date': None
    }

@router.get("/trial/status")
async def get_trial_status(
    account_id: str = Depends(verify_and_get_user_id_from_jwt)
) -> Dict[str, Any]:
    """Stub endpoint for trial status."""
    logger.debug(f"Billing disabled - returning no trial for user {account_id}")
    return {
        'has_trial': False,
        'trial_status': None,
        'trial_ends_at': None,
        'message': 'Billing disabled - no trial needed'
    }

@router.post("/trial/cancel")
async def cancel_trial(
    account_id: str = Depends(verify_and_get_user_id_from_jwt)
) -> Dict[str, Any]:
    """Stub endpoint for trial cancellation."""
    logger.debug(f"Billing disabled - trial cancellation not applicable for user {account_id}")
    return {
        'success': True,
        'message': 'Billing disabled - no trial to cancel'
    }

@router.post("/trial/start")
async def start_trial(
    account_id: str = Depends(verify_and_get_user_id_from_jwt)
) -> Dict[str, Any]:
    """Stub endpoint for trial start."""
    logger.debug(f"Billing disabled - trial start not applicable for user {account_id}")
    return {
        'success': True,
        'message': 'Billing disabled - no trial needed'
    }

@router.post("/trial/create-checkout")
async def create_trial_checkout(
    account_id: str = Depends(verify_and_get_user_id_from_jwt)
) -> Dict[str, Any]:
    """Stub endpoint for trial checkout creation."""
    logger.debug(f"Billing disabled - trial checkout not applicable for user {account_id}")
    return {
        'success': True,
        'message': 'Billing disabled - no trial checkout needed'
    }

# Additional stub endpoints for any other billing routes that might be called
@router.post("/purchase-credits")
async def purchase_credits_checkout(
    account_id: str = Depends(verify_and_get_user_id_from_jwt)
) -> Dict[str, Any]:
    """Stub endpoint for credit purchase."""
    logger.debug(f"Billing disabled - credit purchase not applicable for user {account_id}")
    return {
        'success': True,
        'message': 'Billing disabled - credits unlimited'
    }

@router.post("/webhook")
async def stripe_webhook() -> Dict[str, Any]:
    """Stub endpoint for Stripe webhook."""
    logger.debug("Billing disabled - Stripe webhook not applicable")
    return {
        'success': True,
        'message': 'Billing disabled - webhook ignored'
    }

@router.post("/create-checkout-session")
async def create_checkout_session(
    account_id: str = Depends(verify_and_get_user_id_from_jwt)
) -> Dict[str, Any]:
    """Stub endpoint for checkout session creation."""
    logger.debug(f"Billing disabled - checkout session not applicable for user {account_id}")
    return {
        'success': True,
        'message': 'Billing disabled - checkout not needed'
    }

@router.post("/create-portal-session")
async def create_portal_session(
    account_id: str = Depends(verify_and_get_user_id_from_jwt)
) -> Dict[str, Any]:
    """Stub endpoint for portal session creation."""
    logger.debug(f"Billing disabled - portal session not applicable for user {account_id}")
    return {
        'success': True,
        'message': 'Billing disabled - portal not needed'
    }

@router.post("/sync-subscription")
async def sync_subscription(
    account_id: str = Depends(verify_and_get_user_id_from_jwt)
) -> Dict[str, Any]:
    """Stub endpoint for subscription sync."""
    logger.debug(f"Billing disabled - subscription sync not applicable for user {account_id}")
    return {
        'success': True,
        'message': 'Billing disabled - no subscription to sync'
    }

@router.post("/cancel-subscription")
async def cancel_subscription(
    account_id: str = Depends(verify_and_get_user_id_from_jwt)
) -> Dict[str, Any]:
    """Stub endpoint for subscription cancellation."""
    logger.debug(f"Billing disabled - subscription cancellation not applicable for user {account_id}")
    return {
        'success': True,
        'message': 'Billing disabled - no subscription to cancel'
    }

@router.post("/reactivate-subscription")
async def reactivate_subscription(
    account_id: str = Depends(verify_and_get_user_id_from_jwt)
) -> Dict[str, Any]:
    """Stub endpoint for subscription reactivation."""
    logger.debug(f"Billing disabled - subscription reactivation not applicable for user {account_id}")
    return {
        'success': True,
        'message': 'Billing disabled - no subscription to reactivate'
    }
