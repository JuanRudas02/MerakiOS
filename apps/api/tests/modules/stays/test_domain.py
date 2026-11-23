from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta

import pytest

from oneheavy.modules.stays.domain.model import (
    DEFAULT_CHECKLIST,
    BillingCutoffs,
    ChecklistItem,
    CleaningTask,
    IssueKind,
    Property,
    Receipt,
    ReceiptStatus,
    TaskStatus,
)
from oneheavy.shared.domain import integration_events as ie
from oneheavy.shared.domain.errors import BusinessRuleViolation

T0 = datetime(2026, 5, 4, 15, 0, tzinfo=UTC)
TENANT = uuid.uuid4()


def _prop(**kw: object) -> Property:
    return Property(tenant_id=TENANT, code="SKY-05", name="Sky 05", **kw)  # type: ignore[arg-type]


def _task(prop: Property | None = None) -> CleaningTask:
    return CleaningTask.schedule(
        tenant_id=TENANT, prop=prop or _prop(), staff_id=uuid.uuid4(), scheduled_at=T0
    )


def test_schedule_uses_default_checklist_and_records_event() -> None:
    task = _task()
    assert [c.item for c in task.checklist] == DEFAULT_CHECKLIST
    events = task.pull_events()
    assert isinstance(events[0], ie.CleaningTaskScheduled)


def test_full_lifecycle_emits_events() -> None:
    task = _task(_prop(checklist_template=["Cama"]))
    task.pull_events()
    task.confirm_arrival(["a.png"], T0 + timedelta(minutes=4))
    assert task.status is TaskStatus.ARRIVED and task.minutes_late() == 4
    task.start(T0 + timedelta(minutes=5))
    task.update_checklist([ChecklistItem("Cama", True)])
    task.complete(["b.png"], T0 + timedelta(minutes=64), on_time_minutes=10)
    assert task.status is TaskStatus.COMPLETED
    arrival, done = task.pull_events()
    assert isinstance(arrival, ie.CleaningArrivalConfirmed) and arrival.minutes_late == 4
    assert isinstance(done, ie.CleaningTaskCompleted)
    assert done.on_time and done.duration_minutes == 60 and done.photos_count == 2


def test_arrival_requires_photos() -> None:
    with pytest.raises(BusinessRuleViolation) as err:
        _task().confirm_arrival([], T0)
    assert err.value.code == "photos_required"


def test_whatsapp_arrival_then_photos_before_start() -> None:
    task = _task()
    task.acknowledge_arrival(T0)
    with pytest.raises(BusinessRuleViolation):
        task.start(T0)
    task.confirm_arrival(["x.png"], T0)
    task.start(T0)
    assert task.status is TaskStatus.IN_PROGRESS


def test_cannot_complete_without_checklist_or_photos() -> None:
    task = _task()
    task.confirm_arrival(["a.png"], T0)
    task.start(T0)
    with pytest.raises(BusinessRuleViolation) as err:
        task.complete(["b.png"], T0, on_time_minutes=10)
    assert err.value.code == "checklist_incomplete"
    task.update_checklist([ChecklistItem(i, True) for i in DEFAULT_CHECKLIST])
    with pytest.raises(BusinessRuleViolation):
        task.complete([], T0, on_time_minutes=10)


def test_late_arrival_is_not_on_time() -> None:
    task = _task(_prop(checklist_template=["Cama"]))
    task.confirm_arrival(["a.png"], T0 + timedelta(minutes=30))
    task.start(T0 + timedelta(minutes=31))
    task.update_checklist([ChecklistItem("Cama", True)])
    task.complete(["b.png"], T0 + timedelta(minutes=90), on_time_minutes=10)
    done = task.pull_events()[-1]
    assert isinstance(done, ie.CleaningTaskCompleted) and not done.on_time


def test_edit_only_when_pending_and_cancel_rules() -> None:
    task = _task()
    task.edit(observations="Llevar toallas")
    assert task.observations == "Llevar toallas"
    task.confirm_arrival(["a.png"], T0)
    with pytest.raises(BusinessRuleViolation):
        task.edit(observations="x")
    task.cancel("Huésped extendió estadía")
    with pytest.raises(BusinessRuleViolation):
        task.cancel("otra vez")


def test_unknown_checklist_item_rejected() -> None:
    task = _task()
    task.confirm_arrival(["a.png"], T0)
    with pytest.raises(BusinessRuleViolation):
        task.update_checklist([ChecklistItem("Piscina", True)])


def test_issue_is_typed_and_emits_event() -> None:
    task = _task()
    task.pull_events()
    task.report_issue(IssueKind.MISSING_SUPPLIES, "Faltan toallas", T0)
    assert task.issues[0].kind is IssueKind.MISSING_SUPPLIES
    assert isinstance(task.pull_events()[0], ie.CleaningIssueReported)


def test_cutoffs_validation_and_due_date_clamped() -> None:
    with pytest.raises(BusinessRuleViolation):
        BillingCutoffs(water=32)
    assert BillingCutoffs.due_date(31, 2026, 2) == date(2026, 2, 28)


def test_receipt_review_once() -> None:
    receipt = Receipt.upload(
        tenant_id=TENANT, property_id=uuid.uuid4(), service="gas", period="2026-05", url="/x"
    )
    receipt.review(approved=True, reviewer_id=uuid.uuid4())
    assert receipt.status is ReceiptStatus.VERIFIED
    assert isinstance(receipt.pull_events()[0], ie.ReceiptVerified)
    with pytest.raises(BusinessRuleViolation):
        receipt.review(approved=False, reviewer_id=uuid.uuid4())


def test_receipt_rejects_bad_period_and_service() -> None:
    with pytest.raises(BusinessRuleViolation):
        Receipt.upload(tenant_id=TENANT, property_id=uuid.uuid4(), service="gas", period="05-2026", url="/x")
    with pytest.raises(BusinessRuleViolation):
        Receipt.upload(
            tenant_id=TENANT, property_id=uuid.uuid4(), service="netflix", period="2026-05", url="/x"
        )


def test_property_validation() -> None:
    with pytest.raises(BusinessRuleViolation):
        _prop(ical_url="ftp://nope")
    prop = _prop()
    prop.update({"name": "Sky 05 Deluxe", "checklist_template": [" Cama ", ""]})
    assert prop.checklist_template == ["Cama"]
    with pytest.raises(BusinessRuleViolation):
        prop.update({"tenant_id": uuid.uuid4()})
