from pathlib import Path


def test_security_workflow_blocks_high_risk_findings() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    workflow = (
        repository_root / ".github" / "workflows" / "security.yml"
    ).read_text(encoding="utf-8")

    assert "pypa/gh-action-pip-audit@" in workflow
    assert "npm audit --audit-level=high" in workflow
    assert "gitleaks/gitleaks-action@v3" in workflow
    assert "aquasecurity/trivy-action@" in workflow
    assert 'exit-code: "1"' in workflow
    assert "severity: HIGH,CRITICAL" in workflow
    assert "docker build" in workflow
