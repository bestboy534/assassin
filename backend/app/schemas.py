from typing import Literal
from pydantic import BaseModel, Field, ConfigDict

BillingCycle = Literal["monthly", "yearly", "weekly", "quarterly", "unknown"]
SourceType = Literal["csv", "apple_mail", "stripe_mail", "paypal_mail", "google_play", "unknown"]
RiskType = Literal["possible_idle", "possible_duplicate", "hidden_fee", "api_usage", "apple_unresolved", "none"]
SubscriptionStatus = Literal[
    "need_confirm", "apple_unresolved", "flagged", "cancel_in_progress", "cancelled",
    "verified_saved", "cancellation_failed", "active", "ignored"
]

class AnalyzeRequest(BaseModel):
    raw_text: str = Field(min_length=1)
    source_hint: SourceType = "unknown"

class ExtractedSubscription(BaseModel):
    model_config = ConfigDict(extra="forbid")
    software_name: str
    merchant_name: str | None = None
    amount: float
    currency: str
    billing_cycle: BillingCycle = "unknown"
    transaction_date: str | None = None
    source_type: SourceType = "unknown"
    risk_type: RiskType = "none"
    confidence: float = Field(ge=0, le=1)
    evidence: str
    needs_user_confirmation: bool = True

class ExtractedSubscriptionsPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[ExtractedSubscription]

class SubscriptionItem(BaseModel):
    id: str
    software_name: str
    merchant_name: str | None = None
    amount: float
    currency: str
    billing_cycle: BillingCycle
    transaction_date: str | None = None
    normalized_amount_usd: float
    monthly_cost_usd: float
    status: SubscriptionStatus
    risk_type: str
    confidence: float
    evidence: str
    needs_user_confirmation: bool
    cancel_url: str | None = None
    fallback_search_url: str | None = None
    support_email: str | None = None
    guide_steps: list[str] = []
    risk_note: str | None = None

class AnalyzeResponse(BaseModel):
    items: list[SubscriptionItem]

class HealthResponse(BaseModel):
    status: str = "ok"
