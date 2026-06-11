"""Import all mapped models so SQLAlchemy and Alembic share one metadata registry."""

from .domains.applications.models import Application, ApplicationSource
from .domains.audit_ai.models import AnalysisItem, AnalysisRun
from .domains.contracts.models import Contract, ContractVersion, Renewal
from .domains.files.models import StoredFile
from .domains.identity.models import User, UserSession
from .domains.jobs.models import Job
from .domains.organizations.models import Organization, OrganizationMember
from .domains.outbox.models import InboxReceipt, OutboxEvent
from .domains.procurement.models import ApprovalDecision, ApprovalTask, PurchaseRequest

__all__ = [
    "AnalysisItem",
    "AnalysisRun",
    "Application",
    "ApplicationSource",
    "ApprovalDecision",
    "ApprovalTask",
    "Contract",
    "ContractVersion",
    "InboxReceipt",
    "Job",
    "Organization",
    "OrganizationMember",
    "OutboxEvent",
    "PurchaseRequest",
    "Renewal",
    "StoredFile",
    "User",
    "UserSession",
]
