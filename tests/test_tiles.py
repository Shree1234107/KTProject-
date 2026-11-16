"""Tests for tracker.tiles: count_anim_html and stat_tile_html."""
from tracker.tiles import count_anim_html, stat_tile_html


# ---------------------------------------------------------------------------
# count_anim_html
# ---------------------------------------------------------------------------

def test_count_anim_contains_target():
    html = count_anim_html(29, "%")
    assert "--target:29" in html


def test_count_anim_sr_only_has_real_value_with_suffix():
    html = count_anim_html(29, "%")
    assert "29%" in html
    assert 'class="sr-only"' in html


def test_count_anim_pct_class_present_for_percent():
    html = count_anim_html(29, "%")
    assert "count-anim--pct" in html


def test_count_anim_no_pct_class_without_suffix():
    html = count_anim_html(15)
    assert "count-anim--pct" not in html
    assert "--target:15" in html
    assert "15" in html


def test_count_anim_aria_hidden():
    html = count_anim_html(50)
    assert 'aria-hidden="true"' in html


def test_count_anim_escapes_suffix():
    html = count_anim_html(5, "<")
    # The suffix must be HTML-escaped in the sr-only span
    assert "&lt;" in html
    # Raw unescaped suffix must not appear inside the sr-only span content
    assert 'class="sr-only">5&lt;<' in html


def test_count_anim_zero():
    html = count_anim_html(0, "%")
    assert "--target:0" in html
    assert "0%" in html


def test_count_anim_large_value():
    html = count_anim_html(9999)
    assert "--target:9999" in html
    assert ">9999<" in html or "9999" in html


# ---------------------------------------------------------------------------
# stat_tile_html
# ---------------------------------------------------------------------------

def test_stat_tile_contains_target_for_integer_value():
    html = stat_tile_html(1, "Total", "15", None, None, False)
    assert "--target:15" in html


def test_stat_tile_pct_value_has_target_and_pct_class():
    html = stat_tile_html(2, "Response rate", "29%", None, None, True)
    assert "--target:29" in html
    assert "count-anim--pct" in html


def test_stat_tile_sr_only_has_real_value():
    html = stat_tile_html(1, "Total", "15", None, None, False)
    assert 'class="sr-only"' in html
    assert ">15<" in html or "15" in html


def test_stat_tile_label_escaped():
    html = stat_tile_html(1, "<Total>", "5", None, None, False)
    assert "&lt;Total&gt;" in html
    assert "<Total>" not in html


def test_stat_tile_has_tile_n_class():
    html = stat_tile_html(3, "X", "10", None, None, False)
    assert "stat-tile-3" in html


def test_stat_tile_no_trend_when_none():
    html = stat_tile_html(1, "Total", "5", None, None, False)
    assert "stat-tile-trend" not in html
    assert "not enough data" not in html


def test_stat_tile_trend_up_rate():
    html = stat_tile_html(2, "Rate", "30%", 0.30, 0.20, True)
    assert "↑" in html and "up" in html
    assert "10 pts vs prior 30 days" in html


def test_stat_tile_trend_down_count():
    html = stat_tile_html(4, "Offers", "2", 2, 5, False)
    assert "↓" in html and "down" in html
    assert "3 vs prior 30 days" in html


def test_stat_tile_trend_flat():
    html = stat_tile_html(4, "Offers", "2", 2, 2, False)
    assert "no change vs prior 30 days" in html


def test_stat_tile_zero_value():
    html = stat_tile_html(5, "Active", "0", None, None, False)
    assert "--target:0" in html


def test_stat_tile_large_value():
    html = stat_tile_html(1, "Total", "1500", None, None, False)
    assert "--target:1500" in html
