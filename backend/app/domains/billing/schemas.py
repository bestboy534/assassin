from pydantic import BaseModel


class BillingWebhookResponse(BaseModel):
    accepted: bool
    duplicate: bool
    stale: bool
    event_id: str
