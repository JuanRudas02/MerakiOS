from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from oneheavy.modules.gamification.domain.model import (
    Challenge,
    ChallengeStatus,
    PlayerProfile,
    PointTransaction,
    Team,
    level_for,
    team_for_role,
)
from oneheavy.modules.gamification.domain.rules import RuleEngine, RuleSetting
from oneheavy.shared.domain import integration_events as ie
from oneheavy.shared.domain.errors import BusinessRuleViolation

T = uuid.uuid4()
STAFF = uuid.uuid4()


def completed(on_time: bool = True, photos: int = 3) -> ie.CleaningTaskCompleted:
    return ie.CleaningTaskCompleted(
        tenant_id=T,
        task_id=uuid.uuid4(),
        property_id=uuid.uuid4(),
        staff_id=STAFF,
        duration_minutes=90,
        photos_count=photos,
        on_time=on_time,
    )


class TestRuleEngine:
    def test_cleaning_on_time_awards_base_plus_photos(self) -> None:
        awards = RuleEngine().evaluate(completed(on_time=True, photos=3), {})
        assert {(a.rule_key, a.points) for a in awards} == {
            ("cleaning_completed_on_time", 50),
            ("cleaning_photos", 15),
        }
        assert all(a.user_id == STAFF for a in awards)

    def test_late_cleaning_and_photo_cap(self) -> None:
        awards = {
            a.rule_key: a.points for a in RuleEngine().evaluate(completed(on_time=False, photos=20), {})
        }
        assert awards == {"cleaning_completed_late": 20, "cleaning_photos": 30}

    def test_override_disables_and_changes_points(self) -> None:
        overrides = {
            "cleaning_completed_on_time": RuleSetting(80),
            "cleaning_photos": RuleSetting(5, active=False),
        }
        awards = RuleEngine().evaluate(completed(photos=4), overrides)
        assert [(a.rule_key, a.points) for a in awards] == [("cleaning_completed_on_time", 80)]

    def test_deal_won_bonus_per_million_capped(self) -> None:
        owner = uuid.uuid4()

        def deal(amount: str, currency: str = "COP") -> ie.DealWon:
            return ie.DealWon(
                tenant_id=T, deal_id=uuid.uuid4(), contact_id=None, owner_id=owner,
                amount=Decimal(amount), currency=currency,
            )  # fmt: skip

        engine = RuleEngine()
        assert engine.evaluate(deal("12500000"), {})[0].points == 112
        assert engine.evaluate(deal("900000000"), {})[0].points == 200
        assert engine.evaluate(deal("5000", "USD"), {})[0].points == 100
        assert engine.evaluate(deal("1"), {})[0].user_id == owner

    def test_rules_without_beneficiary_are_skipped(self) -> None:
        event = ie.CampaignLaunched(
            tenant_id=T, actor_id=None, campaign_id=uuid.uuid4(), name="x", channel="email"
        )
        assert RuleEngine().evaluate(event, {}) == []

    def test_lifecycle_only_customer_scores(self) -> None:
        actor = uuid.uuid4()

        def change(to: str) -> ie.ContactLifecycleChanged:
            return ie.ContactLifecycleChanged(
                tenant_id=T, actor_id=actor, contact_id=uuid.uuid4(), from_stage="sql", to_stage=to
            )

        assert RuleEngine().evaluate(change("opportunity"), {}) == []
        assert RuleEngine().evaluate(change("customer"), {})[0].points == 40


class TestLevelsBadgesStreaks:
    @pytest.mark.parametrize(
        ("points", "number", "name"),
        [(0, 1, "Rookie"), (249, 1, "Rookie"), (250, 2, "Pro"), (3000, 4, "Master"), (20000, 6, "Heavy")],
    )
    def test_levels(self, points: int, number: int, name: str) -> None:
        lv = level_for(points)
        assert (lv.number, lv.name) == (number, name)

    def test_level_progress(self) -> None:
        lv = level_for(625)  # Pro: 250 → 1000
        assert lv.next_level_points == 1000
        assert lv.progress == 0.5
        assert level_for(15000).next_level_points is None

    def test_team_mapping(self) -> None:
        assert team_for_role("staff") is Team.OPERATIONS
        assert team_for_role("sales") is Team.SALES
        assert team_for_role("marketer") is Team.MARKETING
        assert team_for_role("owner") is Team.ALL

    def test_streak_and_badges(self) -> None:
        player = PlayerProfile.enroll(T, STAFF, "Luz", "staff")
        start = datetime(2026, 11, 1, 15, tzinfo=UTC)
        for i in range(7):
            player.apply(
                PointTransaction(
                    tenant_id=T, user_id=STAFF, points=10, rule_key="x", reason="r",
                    source_ref=str(i), occurred_at=start + timedelta(days=i),
                )
            )  # fmt: skip
        assert player.streak_days == 7
        earned = player.evaluate_badges({"cleaning_completed_on_time": 1}, start)
        assert set(earned) == {"first_clean", "streak_7"}
        assert player.evaluate_badges({"cleaning_completed_on_time": 1}, start) == []  # no se repiten

    def test_streak_resets_after_gap(self) -> None:
        player = PlayerProfile.enroll(T, STAFF, "Luz", "staff")
        day = datetime(2026, 11, 1, tzinfo=UTC)
        for offset in (0, 1, 5):
            player.apply(
                PointTransaction(
                    tenant_id=T, user_id=STAFF, points=1, rule_key="x", reason="r",
                    source_ref=str(offset), occurred_at=day + timedelta(days=offset),
                )
            )  # fmt: skip
        assert player.streak_days == 1
        assert player.points == 3

    def test_challenge_validation_and_status(self) -> None:
        now = datetime(2026, 11, 22, tzinfo=UTC)
        with pytest.raises(BusinessRuleViolation):
            Challenge(
                tenant_id=T, title="x", description="", metric="points", target=0,
                starts_at=now, ends_at=now + timedelta(days=1), reward_points=10,
            )  # fmt: skip
        ch = Challenge(
            tenant_id=T, title="x", description="", metric="points", target=5,
            starts_at=now, ends_at=now + timedelta(days=1), reward_points=10, team=Team.SALES,
        )  # fmt: skip
        assert ch.status(now - timedelta(hours=1)) is ChallengeStatus.UPCOMING
        assert ch.status(now + timedelta(hours=1)) is ChallengeStatus.ACTIVE
        assert ch.status(now + timedelta(days=2)) is ChallengeStatus.FINISHED
        assert ch.applies_to(Team.SALES) and not ch.applies_to(Team.OPERATIONS)
