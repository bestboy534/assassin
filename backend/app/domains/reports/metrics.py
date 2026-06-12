from dataclasses import dataclass
from typing import Literal

MetricValueType = Literal["money", "number", "percentage", "duration"]


@dataclass(frozen=True)
class MetricDefinition:
    key: str
    label: str
    description: str
    value_type: MetricValueType
    required_permission: str
    dimensions: frozenset[str]
    sql_expression: str
    allowed_statuses: frozenset[str] = frozenset()


class MetricRegistry:
    def __init__(self, definitions: list[MetricDefinition]) -> None:
        self._definitions = {definition.key: definition for definition in definitions}

    def get(self, key: str) -> MetricDefinition:
        try:
            return self._definitions[key]
        except KeyError as exc:
            raise KeyError(f"Unknown metric: {key}") from exc

    def list(self) -> list[MetricDefinition]:
        return list(self._definitions.values())

    def keys(self) -> set[str]:
        return set(self._definitions)


SPEND_DIMENSIONS = frozenset({"department", "category", "merchant_name", "currency"})
ORG_DIMENSIONS = frozenset({"department", "category", "status", "risk_level", "currency"})


metric_registry = MetricRegistry(
    [
        MetricDefinition(
            key="monthly_spend",
            label="月度支出",
            description="按所选期间统计的软件支出总额。",
            value_type="money",
            required_permission="reports.spend.read",
            dimensions=SPEND_DIMENSIONS,
            sql_expression="SUM(spend_transactions.amount)",
        ),
        MetricDefinition(
            key="budget_allocated",
            label="已分配预算",
            description="所选财年内已启用的部门预算。",
            value_type="money",
            required_permission="reports.spend.read",
            dimensions=frozenset({"department", "currency"}),
            sql_expression="SUM(budgets.amount)",
        ),
        MetricDefinition(
            key="application_count",
            label="应用数量",
            description="当前组织内活跃应用数量。",
            value_type="number",
            required_permission="reports.applications.read",
            dimensions=frozenset({"category", "status", "risk_level"}),
            sql_expression="COUNT(applications.id)",
        ),
        MetricDefinition(
            key="vendor_concentration",
            label="供应商集中度",
            description="最大供应商支出占总支出的比例。",
            value_type="percentage",
            required_permission="reports.spend.read",
            dimensions=frozenset({"department", "currency"}),
            sql_expression="MAX(vendor_spend) / SUM(total_spend)",
        ),
        MetricDefinition(
            key="renewal_amount",
            label="续约金额",
            description="所选期间内待处理续约的当前合同金额。",
            value_type="money",
            required_permission="reports.contracts.read",
            dimensions=frozenset({"status", "currency"}),
            sql_expression="SUM(renewals.current_amount)",
        ),
        MetricDefinition(
            key="seat_utilization",
            label="席位利用率",
            description="已分配席位中的活跃使用比例。",
            value_type="percentage",
            required_permission="reports.applications.read",
            dimensions=ORG_DIMENSIONS,
            sql_expression="active_seats / allocated_seats",
        ),
        MetricDefinition(
            key="procurement_cycle_days",
            label="采购周期",
            description="采购申请从提交到决策的平均天数。",
            value_type="duration",
            required_permission="reports.procurement.read",
            dimensions=frozenset({"department", "status"}),
            sql_expression="AVG(purchase_requests.decided_at - purchase_requests.submitted_at)",
        ),
        MetricDefinition(
            key="estimated_savings",
            label="预计节省",
            description="仍在推进中的节省机会金额。",
            value_type="money",
            required_permission="reports.savings.read",
            dimensions=frozenset({"department", "category", "status", "currency"}),
            sql_expression="SUM(savings_opportunities.estimated_amount)",
        ),
        MetricDefinition(
            key="realized_savings",
            label="已实现节省",
            description="已经落地的节省结果金额。",
            value_type="money",
            required_permission="reports.savings.read",
            dimensions=frozenset({"status"}),
            sql_expression="SUM(savings_results.realized_amount)",
            allowed_statuses=frozenset({"realized", "verified"}),
        ),
        MetricDefinition(
            key="verified_savings",
            label="已验证节省",
            description="仅统计经过验证的节省结果。",
            value_type="money",
            required_permission="reports.savings.read",
            dimensions=frozenset({"status"}),
            sql_expression="SUM(savings_results.verified_amount) WHERE status = 'verified'",
            allowed_statuses=frozenset({"verified"}),
        ),
        MetricDefinition(
            key="high_risk_findings",
            label="高风险发现",
            description="仍未关闭的高风险供应商发现数量。",
            value_type="number",
            required_permission="reports.risk.read",
            dimensions=frozenset({"severity", "status"}),
            sql_expression="COUNT(risk_findings.id)",
            allowed_statuses=frozenset({"open", "accepted"}),
        ),
    ]
)
