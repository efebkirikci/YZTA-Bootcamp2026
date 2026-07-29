"""Funding slot mekaniği testleri — 8 saatlik sabit UTC slotları."""

from datetime import datetime, timezone

from bot.trading.paper_engine import funding_slots_between


def dt(iso: str) -> datetime:
    return datetime.fromisoformat(iso).replace(tzinfo=timezone.utc)


def test_no_slot_crossed_short_hold():
    start = dt("2026-07-01T12:08:00+00:00")
    end = dt("2026-07-01T12:30:00+00:00")
    assert funding_slots_between(start, end) == []


def test_first_payment_at_next_slot():
    """12:08 açılış → ilk ödeme 16:00 slotunda (20:08 DEĞİL)."""
    start = dt("2026-07-01T12:08:00+00:00")
    end = dt("2026-07-01T16:00:01+00:00")
    slots = funding_slots_between(start, end)
    assert len(slots) == 1
    assert slots[0].hour == 16


def test_slot_inclusive_boundary():
    start = dt("2026-07-01T16:00:00+00:00")
    end = dt("2026-07-01T16:00:30+00:00")
    assert funding_slots_between(start, end) == []


def test_multiple_slots_over_days():
    start = dt("2026-07-01T00:00:00+00:00")
    end = dt("2026-07-02T00:00:01+00:00")
    slots = funding_slots_between(start, end)
    assert [s.hour for s in slots] == [8, 16, 0]


def test_sorted_dedup():
    start = dt("2026-07-01T00:00:01+00:00")
    end = dt("2026-07-01T08:00:00+00:00")
    slots = funding_slots_between(start, end)
    assert slots == sorted(set(slots))
    assert len(slots) == 1


def test_weekend_slots_exist():
    start = dt("2026-07-04T05:00:00+00:00")
    end = dt("2026-07-05T05:00:00+00:00")
    assert len(funding_slots_between(start, end)) == 3
