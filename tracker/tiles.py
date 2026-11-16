"""HTML helpers for the Dashboard KPI row (ruled, boxless) with CSS count-up."""
from __future__ import annotations

import html as _html


def count_anim_html(integer_val: int, suffix: str = "") -> str:
    """Return HTML for a CSS count-up animation with an accessible fallback.

    The animated element is aria-hidden; the real value lives in a sr-only
    span so screen readers and copy-paste always see the correct number.

    Args:
        integer_val: The final integer value to count up to.
        suffix: Optional suffix string.  Only "%" gets the CSS ::after rule;
                other suffixes appear only in the sr-only span.
    """
    pct_cls = " count-anim--pct" if suffix == "%" else ""
    real = _html.escape(f"{integer_val}{suffix}")
    return (
        f'<span class="count-anim{pct_cls}" aria-hidden="true"'
        f' style="--target:{integer_val}"></span>'
        f'<span class="sr-only">{real}</span>'
    )


def _trend_html(cur, prev, is_rate: bool) -> str:
    """One short trend line, e.g. "↓ 14 pts vs prior 30 days".

    Returns "" when there is not enough data — the KPI row shows nothing
    rather than a placeholder. Direction is spelled out for screen readers
    (the arrow is aria-hidden), so it never relies on colour alone.
    """
    if cur is None or prev is None:
        return ""
    diff = cur - prev
    if is_rate:
        mag = int(round(abs(diff * 100)))
        amount = f"{mag} pts"
    else:
        mag = abs(int(round(diff)))
        amount = str(mag)
    if mag == 0:
        return '<span class="trend-flat">no change vs prior 30 days</span>'
    if diff > 0:
        arrow, word, cls = "↑", "up", "trend-up"
    else:
        arrow, word, cls = "↓", "down", "trend-down"
    return (
        f'<span class="{cls}"><span aria-hidden="true">{arrow}</span>'
        f'<span class="sr-only">{word}</span> {amount} vs prior 30 days</span>'
    )


def stat_tile_html(
    n: int,
    label: str,
    value: str,
    cur,
    prev,
    is_rate: bool,
) -> str:
    """Build one stat tile HTML string with an animated big number.

    Args:
        n: Tile index 1–5 (selects the stagger CSS class stat-tile-N).
        label: Short lowercase label displayed below the number.
        value: Pre-formatted value string such as "15" or "29%".
        cur: Current 30-day window metric (float | int | None).
        prev: Previous 30-day window metric (float | int | None).
        is_rate: True when the value is a percentage rate.
    """
    try:
        if value.endswith("%"):
            int_val = int(round(float(value[:-1])))
            suffix = "%"
        else:
            int_val = int(round(float(value)))
            suffix = ""
    except (ValueError, AttributeError):
        int_val = 0
        suffix = ""

    value_html = count_anim_html(int_val, suffix)
    trend = _trend_html(cur, prev, is_rate)
    label_e = _html.escape(label)
    trend_div = f'<div class="stat-tile-trend">{trend}</div>' if trend else ""
    return (
        f'<div class="stat-tile stat-tile-{n}">'
        f'<div class="stat-tile-value">{value_html}</div>'
        f'<div class="stat-tile-label">{label_e}</div>'
        f'{trend_div}'
        f'</div>'
    )
