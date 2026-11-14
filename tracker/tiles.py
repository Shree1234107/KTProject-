"""HTML helpers for Dashboard stat tiles with CSS count-up animation."""
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
    if cur is None or prev is None:
        return '<span class="trend-none">not enough data for a trend</span>'
    diff = cur - prev
    if is_rate:
        cur_str = f"{cur:.0%}"
        mag = abs(diff * 100)
        if mag < 0.5:
            change_str, cls = "no change", "trend-flat"
        elif diff > 0:
            change_str, cls = f"up {mag:.1f} points", "trend-up"
        else:
            change_str, cls = f"down {mag:.1f} points", "trend-down"
    else:
        cur_str = str(int(round(cur)))
        mag = abs(int(round(diff)))
        if mag == 0:
            change_str, cls = "no change", "trend-flat"
        elif diff > 0:
            change_str, cls = f"up {mag}", "trend-up"
        else:
            change_str, cls = f"down {mag}", "trend-down"
    return (
        f'<span class="{cls}">last 30 days: {cur_str} '
        f'({change_str} from the 30 days before)</span>'
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
        label: Tile label displayed above the number.
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
    return (
        f'<div class="stat-tile stat-tile-{n}">'
        f'<div class="stat-tile-label">{label_e}</div>'
        f'<div class="stat-tile-value">{value_html}</div>'
        f'<div class="stat-tile-trend">{trend}</div>'
        f'</div>'
    )
