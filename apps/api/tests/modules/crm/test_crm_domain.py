from __future__ import annotations

import uuid
from datetime import timedelta
from decimal import Decimal

import pytest

from oneheavy.modules.crm.domain.model import (
    ALLOWED_TRANSITIONS,
    Contact,
    ContactSource,
    Deal,
    DealStage,
    LifecycleStage,
)
from oneheavy.modules.crm.domain.scoring import RuleBasedScoringPolicy
from oneheavy.shared.domain import integration_events as ie
from oneheavy.shared.domain.errors import BusinessRuleViolation
from oneheavy.shared.domain.time import utc_now
from oneheavy.shared.domain.value_objects import Email, PhoneNumber

TENANT = uuid.uuid4()


def make_contact(**kw: object) -> Contact:
    defaults: dict[str, object] = {"tenant_id": TENANT, "first_name": "Ana", "email": Email("ana@acme.co")}
    defaults.update(kw)
    return Contact.create(**defaults)  # type: ignore[arg-type]


class TestContactLifecycle:
    def test_create_records_contact_created(self) -> None:
        c = make_contact(phone=PhoneNumber("3001112222"), source=ContactSource.META_LEAD_ADS)
        events = c.pull_events()
        assert isinstance(events[0], ie.ContactCreated)
        assert events[0].phone == "+573001112222"
        assert c.stage is LifecycleStage.LEAD

    def test_mautic_contacts_start_as_subscribers(self) -> None:
        assert make_contact(source=ContactSource.MAUTIC).stage is LifecycleStage.SUBSCRIBER

    def test_contact_requires_email_or_phone(self) -> None:
        with pytest.raises(BusinessRuleViolation):
            Contact.create(tenant_id=TENANT, first_name="X")

    def test_valid_transition_emits_event(self) -> None:
        c = make_contact()
        c.pull_events()
        c.move_to(LifecycleStage.SQL)
        (event,) = c.pull_events()
        assert isinstance(event, ie.ContactLifecycleChanged)
        assert (event.from_stage, event.to_stage) == ("lead", "sql")

    @pytest.mark.parametrize(
        ("start", "target"),
        [
            (LifecycleStage.LEAD, LifecycleStage.CUSTOMER),
            (LifecycleStage.LOST, LifecycleStage.CUSTOMER),
            (LifecycleStage.EVANGELIST, LifecycleStage.LEAD),
        ],
    )
    def test_invalid_transitions_rejected(self, start: LifecycleStage, target: LifecycleStage) -> None:
        c = make_contact()
        c.stage = start
        with pytest.raises(BusinessRuleViolation):
            c.move_to(target)

    def test_every_stage_has_a_way_out(self) -> None:
        assert all(ALLOWED_TRANSITIONS[s] for s in LifecycleStage)

    def test_lead_auto_advances_to_mql_at_threshold(self) -> None:
        c = make_contact()
        c.pull_events()
        c.apply_score(49)
        assert c.stage is LifecycleStage.LEAD
        c.apply_score(50)
        assert c.stage is LifecycleStage.MQL
        assert [e.event_name for e in c.pull_events()] == ["ContactLifecycleChanged"]

    def test_merge_missing_never_overwrites(self) -> None:
        c = make_contact(company="Acme")
        c.merge_missing(company="Otra", phone=PhoneNumber("3001112222"), tags=["VIP", "vip"])
        assert c.company == "Acme"
        assert c.phone is not None
        assert c.tags == ["vip"]


class TestScoring:
    policy = RuleBasedScoringPolicy()

    def test_profile_and_source_weights(self) -> None:
        c = make_contact(
            last_name="Pérez",
            phone=PhoneNumber("3001112222"),
            company="Acme",
            job_title="CEO",
            source=ContactSource.META_LEAD_ADS,
        )
        result = self.policy.score(c)
        assert result.breakdown == {"perfil": 35, "fuente": 15, "engagement": 0}
        assert result.score == 50

    def test_engagement_is_capped_and_decays(self) -> None:
        c = make_contact()
        c.engagement_points = 500
        c.last_activity_at = utc_now()
        assert self.policy.score(c).breakdown["engagement"] == 50
        c.last_activity_at = utc_now() - timedelta(days=45)
        assert self.policy.score(c).breakdown["engagement"] == 25
        c.last_activity_at = utc_now() - timedelta(days=120)
        assert self.policy.score(c).breakdown["engagement"] == 10

    def test_score_never_exceeds_100(self) -> None:
        c = make_contact(phone=PhoneNumber("3001112222"), last_name="X", company="Y", job_title="Z")
        c.engagement_points = 999
        assert self.policy.score(c).score <= 100


class TestDeal:
    def test_won_emits_event_and_closes(self) -> None:
        d = Deal.open(tenant_id=TENANT, title="Plan anual", amount=Decimal("1200000"))
        d.move(DealStage.PROPOSAL)
        d.move(DealStage.WON)
        (event,) = d.pull_events()
        assert isinstance(event, ie.DealWon)
        assert event.amount == Decimal("1200000")
        assert d.closed_at is not None

    def test_closed_deal_cannot_move_or_edit(self) -> None:
        d = Deal.open(tenant_id=TENANT, title="X", amount=Decimal(1))
        d.move(DealStage.LOST)
        assert isinstance(d.pull_events()[0], ie.DealLost)
        with pytest.raises(BusinessRuleViolation):
            d.move(DealStage.NEW)
        with pytest.raises(BusinessRuleViolation):
            d.edit(title="Y")

    def test_invalid_amount_and_currency(self) -> None:
        with pytest.raises(BusinessRuleViolation):
            Deal.open(tenant_id=TENANT, title="X", amount=Decimal(-1))
        with pytest.raises(BusinessRuleViolation):
            Deal.open(tenant_id=TENANT, title="X", amount=Decimal(1), currency="PESOS")
