from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest

from oneheavy.modules.meta.application.use_cases import lead_notifications_from_payload
from oneheavy.modules.meta.application.webhooks import (
    compute_signature,
    verify_signature,
    verify_subscription,
)
from oneheavy.modules.meta.domain.anomalies import (
    AnomalyDetector,
    CampaignSeries,
    CpcSpikeRule,
    HighCplRule,
    LowCtrRule,
    ZeroDeliveryRule,
)
from oneheavy.modules.meta.domain.model import (
    CampaignDailyMetric,
    MetaConnection,
    Performance,
    Severity,
    hash_email,
    hash_phone,
)
from oneheavy.modules.meta.infrastructure.graph import _sum_actions, parse_lead_fields
from oneheavy.shared.domain.errors import AuthenticationError, BusinessRuleViolation

TENANT = uuid.uuid4()


def metric(
    day: int, *, spend: int = 1000, impressions: int = 2000, clicks: int = 40, leads: int = 0
) -> CampaignDailyMetric:
    return CampaignDailyMetric(
        tenant_id=TENANT,
        external_id="c1",
        name="Campaña",
        status="ACTIVE",
        objective="OUTCOME_LEADS",
        day=date(2026, 11, 1) + timedelta(days=day),
        spend=Decimal(spend),
        impressions=impressions,
        clicks=clicks,
        leads=leads,
    )


def series(days: list[CampaignDailyMetric], status: str = "ACTIVE") -> CampaignSeries:
    return CampaignSeries("c1", "Campaña", status, days)


class TestPerformance:
    def test_derived_kpis(self) -> None:
        p = Performance.of([metric(0, spend=1000, impressions=2000, clicks=40, leads=4)])
        assert (p.ctr, p.cpc, p.cpm, p.cpl) == (2.0, 25.0, 500.0, 250.0)

    def test_zero_safe(self) -> None:
        p = Performance()
        assert (p.ctr, p.cpc, p.cpm, p.cpl, p.roas) == (0.0, 0.0, 0.0, 0.0, 0.0)


class TestAnomalyRules:
    def test_low_ctr_detects_creative_fatigue(self) -> None:
        anomaly = LowCtrRule().evaluate(series([metric(0, impressions=5000, clicks=10)]))
        assert anomaly is not None
        assert anomaly.metric == "ctr"
        assert anomaly.severity is Severity.CRITICAL  # 0.2% < 0.5%

    def test_low_ctr_ignores_low_volume(self) -> None:
        assert LowCtrRule().evaluate(series([metric(0, impressions=500, clicks=1)])) is None

    def test_cpc_spike(self) -> None:
        days = [metric(i, spend=1000, clicks=40) for i in range(7)] + [metric(7, spend=4000, clicks=40)]
        anomaly = CpcSpikeRule().evaluate(series(days))
        assert anomaly is not None and anomaly.value == 100.0 and anomaly.benchmark == 25.0

    def test_cpc_stable_no_alert(self) -> None:
        assert CpcSpikeRule().evaluate(series([metric(i) for i in range(8)])) is None

    def test_high_cpl(self) -> None:
        anomaly = HighCplRule(benchmark=100).evaluate(series([metric(0, spend=1000, leads=2)]))
        assert anomaly is not None and anomaly.severity is Severity.CRITICAL

    def test_zero_delivery_only_for_active(self) -> None:
        days = [metric(0), metric(1, impressions=0, clicks=0)]
        assert ZeroDeliveryRule().evaluate(series(days)) is not None
        assert ZeroDeliveryRule().evaluate(series(days, status="PAUSED")) is None

    def test_detector_runs_all_rules(self) -> None:
        days = [metric(0, impressions=5000, clicks=5), metric(1, impressions=0, clicks=0)]
        keys = {a.metric for a in AnomalyDetector().detect(series(days))}
        assert {"ctr", "delivery"} <= keys


class TestConnection:
    def test_normalizes_account_and_masks_token(self) -> None:
        conn = MetaConnection.connect(
            tenant_id=TENANT, ad_account_id="act_123456789", access_token="EAAB-secret-9876"
        )
        assert conn.ad_account_id == "123456789"
        assert conn.masked_token == "…9876"

    @pytest.mark.parametrize(("account", "token"), [("abc", "EAAB-secret-9876"), ("123456789", "short")])
    def test_rejects_invalid(self, account: str, token: str) -> None:
        with pytest.raises(BusinessRuleViolation):
            MetaConnection.connect(tenant_id=TENANT, ad_account_id=account, access_token=token)


class TestWebhookSecurity:
    def test_valid_signature(self) -> None:
        body = b'{"object":"page"}'
        verify_signature("s3cret", body, compute_signature("s3cret", body), env="production")

    def test_invalid_signature(self) -> None:
        with pytest.raises(AuthenticationError):
            verify_signature("s3cret", b"{}", "sha256=deadbeef", env="production")
        with pytest.raises(AuthenticationError):
            verify_signature("s3cret", b"{}", None, env="test")

    def test_missing_secret_only_allowed_locally(self) -> None:
        verify_signature(None, b"{}", None, env="test")
        with pytest.raises(AuthenticationError):
            verify_signature(None, b"{}", None, env="production")

    def test_subscription_verification(self) -> None:
        assert verify_subscription("subscribe", "tok", "tok")
        assert not verify_subscription("subscribe", "bad", "tok")
        assert not verify_subscription("subscribe", "tok", None)


def test_lead_payload_parsing() -> None:
    payload = {
        "object": "page",
        "entry": [
            {"id": "p1", "changes": [{"field": "leadgen", "value": {"leadgen_id": "L1", "page_id": "p1"}}]},
            {"id": "p2", "changes": [{"field": "feed", "value": {}}]},
        ],
    }
    notes = lead_notifications_from_payload(payload)
    assert [(n.page_id, n.leadgen_id) for n in notes] == [("p1", "L1")]
    assert lead_notifications_from_payload({"object": "user"}) == []


def test_hashing_is_normalized() -> None:
    assert hash_email(" Ana@Acme.CO ") == hash_email("ana@acme.co")
    assert hash_phone("+57 300-111") == hash_phone("57300111")
    assert hash_email(None) is None and hash_phone("") is None


def test_graph_parsers() -> None:
    actions = [{"action_type": "lead", "value": "3"}, {"action_type": "link_click", "value": "9"}]
    assert _sum_actions(actions, {"lead"}) == Decimal(3)
    fields = parse_lead_fields(
        [{"name": "email", "values": ["a@b.co"]}, {"name": "city", "values": ["Bogotá"]}]
    )
    assert fields == {"email": "a@b.co", "city": "Bogotá"}
