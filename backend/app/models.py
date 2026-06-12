"""Import all mapped models so SQLAlchemy and Alembic share one metadata registry."""

from .domains.applications.models import Application, ApplicationSource
from .domains.audit_ai.models import AnalysisItem, AnalysisRun
from .domains.contracts.models import Contract, ContractVersion, Renewal
from .domains.files.models import StoredFile
from .domains.identity.models import User, UserSession
from .domains.jobs.models import Job
from .domains.organizations.models import Organization, OrganizationMember
from .domains.outbox.models import InboxReceipt, OutboxEvent
from .domains.payments.models import (
    PaymentAction,
    PaymentEvent,
    PaymentInstrument,
    PaymentLimit,
    PaymentRequest,
)
from .domains.procurement.models import ApprovalDecision, ApprovalTask, PurchaseRequest
from .domains.savings.models import (
    OptimizationProject,
    OptimizationTask,
    SavingsBaseline,
    SavingsOpportunity,
    SavingsResult,
)
from .domains.spend.models import (
    AccountingPeriod,
    Budget,
    BudgetCommitment,
    SpendTransaction,
    TransactionAnomaly,
    TransactionSplit,
)
from .domains.vendors.models import RiskFinding, Vendor, VendorAlias, VendorRiskAssessment

__all__ = [
    "AnalysisItem",
    "AnalysisRun",
    "AccountingPeriod",
    "Application",
    "ApplicationSource",
    "ApprovalDecision",
    "ApprovalTask",
    "Budget",
    "BudgetCommitment",
    "Contract",
    "ContractVersion",
    "InboxReceipt",
    "Job",
    "Organization",
    "OrganizationMember",
    "OptimizationProject",
    "OptimizationTask",
    "OutboxEvent",
    "PaymentAction",
    "PaymentEvent",
    "PaymentInstrument",
    "PaymentLimit",
    "PaymentRequest",
    "PurchaseRequest",
    "RiskFinding",
    "Renewal",
    "SavingsBaseline",
    "SavingsOpportunity",
    "SavingsResult",
    "StoredFile",
    "SpendTransaction",
    "TransactionAnomaly",
    "TransactionSplit",
    "User",
    "UserSession",
    "Vendor",
    "VendorAlias",
    "VendorRiskAssessment",
]
