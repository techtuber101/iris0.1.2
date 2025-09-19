from decimal import Decimal
from typing import Optional, Dict, Tuple
from billing.api import calculate_token_cost
from billing.credit_manager import credit_manager
from core.utils.config import config, EnvMode
from core.utils.logger import logger
from core.services.supabase import DBConnection

class BillingIntegration:
    @staticmethod
    async def check_and_reserve_credits(account_id: str, estimated_tokens: int = 10000) -> Tuple[bool, str, Optional[str]]:
        # Billing completely disabled - always allow usage
        return True, "Billing disabled - unlimited usage", None
    
    @staticmethod
    async def deduct_usage(
        account_id: str,
        prompt_tokens: int,
        completion_tokens: int,
        model: str,
        message_id: Optional[str] = None,
        cache_read_tokens: int = 0,
        cache_creation_tokens: int = 0
    ) -> Dict:
        # Billing completely disabled - no cost deduction
        return {'success': True, 'cost': 0, 'new_balance': 10000}

billing_integration = BillingIntegration() 