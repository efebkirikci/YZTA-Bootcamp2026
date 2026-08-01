"""Funding slot mechanics tests — fixed 8h UTC slots (00/08/16)."""

from datetime import datetime, timezone

import pytest

from bot.trading.paper_engine import funding_slots_between


def dt(iso: str) -> datetime:
    return datetime.fromisoformat(iso).replace(tzinfo=timezone.utc)


def test_no_slot_crossed_short_hold():
    """12:08'de açılan pozisyon 16:00'dan önce ödeme almaz."""
    start = dt("2026-07-01T12:08:00+00:00")
    end = dt("2026-07-01T12:30:00+00:00")
    assert funding_slots_between(start, end) == []


def test_first_payment_at_next_slot():
    """12:08'de açılan pozisyon ilk ödemesini 16:00'da alır (20:08 DEĞİL)."""
    start = dt("2026-07-01T12:08:00+00:00")
    end = dt("2026-07-01T16:00:01+00:00")
    slots = funding_slots_between(start, end)
    assert len(slots) == 1
    assert slots[0].hour == 16


def test_slot_inclusive_boundary():
    """Slot anında açılış (16:00:00) o slotu almaz — start < slot şartı."""
    start = dt("2026-07-01T16:00:00+00:00")
    end = dt("2026-07-01T16:00:30+00:00")
    assert funding_slots_between(start, end) == []


def test_multiple_slots_over_days():
    start = dt("2026-07-01T00:00:00+00:00")
    end = dt("2026-07-02T00:00:01+00:00")  # 24 saat + 1 sn
    slots = funding_slots_between(start, end)
    hours = [s.hour for s in slots]
    # 1 Temmuz: 00 (hariç, start eşit), 08, 16 ve 2 Temmuz: 00
    assert hours == [8, 16, 0]


def test_weekend_slots_exist():
    """Hafta sonu da funding slotları işler — takvim 7/24."""
    start = dt("2026-07-04T05:00:00+00:00")   # Cumartesi
    end = dt("2026-07-05T05:00:00+00:00")
    slots = funding_slots_between(start, end)
    assert len(slots) == 3  # 08, 16, 00


def test_sorted_dedup():
    start = dt("2026-07-01T00:00:01+00:00")
    end = dt("2026-07-01T08:00:00+00:00")
    slots = funding_slots_between(start, end)
    assert slots == sorted(set(slots))
    assert len(slots) == 1
