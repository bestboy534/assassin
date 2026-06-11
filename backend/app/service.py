from .normalizer import default_status, monthly_cost, normalize_amount_to_usd
from .route_matcher import fallback_search_url, find_route
from .schemas import ExtractedSubscription, SubscriptionItem
from .utils import make_subscription_id


def to_subscription_item(extracted: ExtractedSubscription) -> SubscriptionItem:
    amount_usd = normalize_amount_to_usd(extracted.amount, extracted.currency)
    monthly_usd = monthly_cost(amount_usd, extracted.billing_cycle)
    route = find_route(extracted.software_name, extracted.merchant_name)
    return SubscriptionItem(
        id=make_subscription_id(extracted),
        software_name=extracted.software_name,
        merchant_name=extracted.merchant_name,
        amount=extracted.amount,
        currency=extracted.currency.upper(),
        billing_cycle=extracted.billing_cycle,
        transaction_date=extracted.transaction_date,
        normalized_amount_usd=amount_usd,
        monthly_cost_usd=monthly_usd,
        status=default_status(extracted),
        risk_type=extracted.risk_type,
        confidence=extracted.confidence,
        evidence=extracted.evidence,
        needs_user_confirmation=extracted.needs_user_confirmation,
        cancel_url=route.get("primary_cancel_url"),
        fallback_search_url=fallback_search_url(extracted.software_name),
        support_email=route.get("support_email"),
        guide_steps=route.get("guide_steps", []),
        risk_note=route.get("risk_note"),
    )
