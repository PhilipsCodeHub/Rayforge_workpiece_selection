"""Tests for the GTK-free selection rules."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from workpiece_selection.selection_model import (  # noqa: E402
    SelectionState,
    classify,
    effective_selection,
    filter_for,
    toggled_filter,
)

LAYER = ["a", "b", "c", "d"]


def test_new_step_selects_everything():
    assert effective_selection([], LAYER) == LAYER
    assert classify([], LAYER) is SelectionState.ALL


def test_deselect_one_makes_explicit_list_in_layer_order():
    assert toggled_filter([], LAYER, "b", False) == ["a", "c", "d"]


def test_reselect_returns_to_all():
    assert toggled_filter(["a", "c", "d"], LAYER, "b", True) == []


def test_partial_reselect_stays_explicit():
    assert toggled_filter(["a"], LAYER, "c", True) == ["a", "c"]


def test_select_all_value_is_empty_list():
    assert filter_for(LAYER, LAYER) == []
    assert filter_for(["a", "b"], LAYER) == ["a", "b"]


def test_last_selected_cannot_be_deselected():
    assert toggled_filter(["b"], LAYER, "b", False) is None
    assert toggled_filter([], ["only"], "only", False) is None


def test_never_produces_empty_selection():
    f = []
    for uid in ["a", "b", "c", "d"]:
        new = toggled_filter(f, LAYER, uid, False)
        if new is None:
            break
        f = new
    assert f == ["d"]
    assert effective_selection(f, LAYER) == ["d"]


def test_stale_uids_are_ignored_and_dropped_on_write():
    stale = ["a", "gone"]
    assert effective_selection(stale, LAYER) == ["a"]
    assert classify(stale, LAYER) is SelectionState.PARTIAL
    assert toggled_filter(stale, LAYER, "b", True) == ["a", "b"]


def test_all_selected_workpieces_deleted_is_nothing_state():
    assert classify(["gone1", "gone2"], LAYER) is SelectionState.NOTHING
    assert effective_selection(["gone1"], LAYER) == []
    # user can recover by ticking one
    assert toggled_filter(["gone1"], LAYER, "c", True) == ["c"]


def test_unknown_uid_rejected():
    assert toggled_filter([], LAYER, "zzz", True) is None


def test_empty_layer():
    assert filter_for([], []) == []
    assert classify([], []) is SelectionState.ALL


def test_explicit_full_list_normalised_when_ticking_last():
    assert toggled_filter(["a", "b", "c"], LAYER, "d", True) == []
