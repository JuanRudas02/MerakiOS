from __future__ import annotations

import uuid

import pytest

from oneheavy.modules.marketing.application.use_cases import default_plan, parse_steps
from oneheavy.modules.marketing.domain.html import html_to_text, sanitize_html
from oneheavy.modules.marketing.domain.model import (
    AudienceMember,
    Campaign,
    CampaignStatus,
    CampaignStep,
    Channel,
    EmailDraft,
    SegmentFilters,
)
from oneheavy.shared.domain import integration_events as ie
from oneheavy.shared.domain.errors import BusinessRuleViolation

TENANT = uuid.uuid4()


class TestSanitizer:
    def test_strips_scripts_handlers_and_js_urls(self) -> None:
        dirty = (
            '<p onclick="steal()">Hola <strong>Ana</strong></p>'
            "<script>alert(1)</script><style>p{}</style>"
            '<a href="javascript:alert(1)">x</a><a href="https://1heavy.co" target="_blank">ok</a>'
            '<img src="data:image/png;base64,AAA" onerror="x()"><iframe src="https://evil"></iframe>'
        )
        clean = sanitize_html(dirty)
        assert "script" not in clean and "alert" not in clean and "onclick" not in clean
        assert "onerror" not in clean and "iframe" not in clean and "data:" not in clean
        assert '<a href="https://1heavy.co" rel="noopener noreferrer" target="_blank">ok</a>' in clean
        assert "<strong>Ana</strong>" in clean

    def test_keeps_mautic_tokens_and_escapes_text(self) -> None:
        clean = sanitize_html('<p>1 < 2 & 3</p><a href="{unsubscribe_url}">baja</a>')
        assert "1 &lt; 2 &amp; 3" in clean
        assert 'href="{unsubscribe_url}"' in clean

    def test_html_to_text(self) -> None:
        assert html_to_text("<p>Hola</p><p>Mundo &amp; más</p>") == "Hola\nMundo & más"


class TestSegments:
    def member(self, **kw: object) -> AudienceMember:
        base: dict[str, object] = {"tenant_id": TENANT, "contact_id": uuid.uuid4()}
        base.update(kw)
        return AudienceMember(**base)  # type: ignore[arg-type]

    def test_filters_combine_with_and(self) -> None:
        f = SegmentFilters(stages=("mql",), tags=("source:meta_lead_ads",), min_score=5)
        assert f.matches(self.member(stage="mql", tags=["source:meta_lead_ads"], engagement_points=5))
        assert not f.matches(self.member(stage="lead", tags=["source:meta_lead_ads"], engagement_points=9))
        assert not f.matches(self.member(stage="mql", tags=["source:manual"], engagement_points=9))
        assert not f.matches(self.member(stage="mql", tags=["source:meta_lead_ads"], engagement_points=1))

    def test_empty_filters_match_everyone(self) -> None:
        assert SegmentFilters().matches(self.member())


class TestEmailAndCampaign:
    def test_compose_sanitizes_and_derives_text(self) -> None:
        draft = EmailDraft.compose(
            tenant_id=TENANT,
            subject="  Hola   mundo ",
            preheader="pre",
            body_html="<p>Hola<script>x</script></p>",
            body_text=None,
            goal="g",
        )
        assert draft.subject == "Hola mundo"
        assert draft.body_html == "<p>Hola</p>"
        assert draft.body_text == "Hola"

    def test_compose_rejects_empty(self) -> None:
        with pytest.raises(BusinessRuleViolation):
            EmailDraft.compose(
                tenant_id=TENANT,
                subject="x",
                preheader="",
                body_html="<script>x</script>",
                body_text=None,
                goal="g",
            )

    def test_launch_emits_event_once(self) -> None:
        c = Campaign(
            tenant_id=TENANT,
            name="N",
            objective="O",
            steps=[CampaignStep(3, Channel.WHATSAPP, "b", "i"), CampaignStep(0, Channel.WHATSAPP, "a", "i")],
        )
        assert c.steps[0].day == 0
        c.launch(actor_id=None)
        (event,) = c.pull_events()
        assert isinstance(event, ie.CampaignLaunched) and event.channel == "whatsapp"
        assert c.status is CampaignStatus.ACTIVE
        with pytest.raises(BusinessRuleViolation):
            c.launch(actor_id=None)

    def test_parse_steps_discards_invalid(self) -> None:
        raw = [
            {"day": 0, "channel": "email", "subject": "s", "intent": "i"},
            {"day": 99, "channel": "email", "subject": "s", "intent": "i"},
            {"day": 1, "channel": "fax", "subject": "s", "intent": "i"},
            {"day": "x"},
            "basura",
        ]
        assert len(parse_steps(raw, 14)) == 1
        assert parse_steps("nope", 14) == []

    def test_default_plan_within_duration(self) -> None:
        steps = default_plan("Vender", 10)
        assert steps[0].day == 0 and steps[-1].day == 10 and len(steps) == 5
