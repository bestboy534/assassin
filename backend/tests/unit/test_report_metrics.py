from app.domains.reports.metrics import metric_registry


def test_verified_savings_metric_uses_only_verified_results() -> None:
    definition = metric_registry.get("verified_savings")

    assert "status = 'verified'" in definition.sql_expression
    assert "realized" not in definition.allowed_statuses
    assert definition.value_type == "money"


def test_reporting_metric_registry_contains_first_batch() -> None:
    expected = {
        "monthly_spend",
        "budget_allocated",
        "application_count",
        "vendor_concentration",
        "renewal_amount",
        "seat_utilization",
        "procurement_cycle_days",
        "estimated_savings",
        "realized_savings",
        "verified_savings",
        "high_risk_findings",
    }

    assert expected <= {item.key for item in metric_registry.list()}
