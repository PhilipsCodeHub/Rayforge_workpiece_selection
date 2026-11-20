"""Selection rules, independent of GTK and Rayforge.

Rayforge's step filter semantics (``Step.workpiece_uids``):

* ``[]``         -> every workpiece of the layer, including ones added later
* non-empty list -> only the listed workpieces

An empty list therefore can never mean "none", so this module never
produces an empty *selection*: the last selected workpiece cannot be
deselected (``toggled_filter`` returns ``None`` for that case).

All functions take ``layer_uids`` in layer order and return filters in
layer order, so results are deterministic.
"""

from enum import Enum
from typing import Iterable, Sequence


class SelectionState(Enum):
    ALL = "all"  # filter is empty: all workpieces, now and later
    PARTIAL = "partial"  # explicit list matching >= 1 current workpiece
    NOTHING = "nothing"  # explicit list matching no current workpiece


def effective_selection(
    filter_uids: Sequence[str], layer_uids: Sequence[str]
) -> list[str]:
    """Workpieces of the layer the step currently processes.

    Stale UIDs (workpieces that no longer exist) are ignored, exactly
    like ``Step.selected_workpieces`` ignores them.
    """
    if not filter_uids:
        return list(layer_uids)
    wanted = set(filter_uids)
    return [uid for uid in layer_uids if uid in wanted]


def classify(
    filter_uids: Sequence[str], layer_uids: Sequence[str]
) -> SelectionState:
    if not filter_uids:
        return SelectionState.ALL
    if not effective_selection(filter_uids, layer_uids):
        return SelectionState.NOTHING
    return SelectionState.PARTIAL


def filter_for(selected: Iterable[str], layer_uids: Sequence[str]) -> list[str]:
    """Filter value that processes exactly ``selected``.

    Selecting every workpiece is stored as ``[]`` so the step goes back
    to "all workpieces" and picks up workpieces added later. Stale UIDs
    are dropped.
    """
    chosen = set(selected)
    if not layer_uids or set(layer_uids) <= chosen:
        return []
    return [uid for uid in layer_uids if uid in chosen]


def toggled_filter(
    filter_uids: Sequence[str],
    layer_uids: Sequence[str],
    uid: str,
    checked: bool,
) -> list[str] | None:
    """New filter after (un)checking ``uid``.

    Returns ``None`` when the change is not allowed: unknown workpiece,
    or it would leave nothing selected.
    """
    if uid not in layer_uids:
        return None
    selected = set(effective_selection(filter_uids, layer_uids))
    if checked:
        selected.add(uid)
    else:
        selected.discard(uid)
        if not selected:
            return None
    return filter_for(selected, layer_uids)


def only_filter(uid: str, layer_uids: Sequence[str]) -> list[str] | None:
    """Filter that processes just ``uid``.

    Always a valid, non-empty selection. Returns ``None`` for an unknown
    workpiece. If ``uid`` is the layer's only workpiece the result is
    ``[]`` ("all"), which is the same thing and keeps the step in its
    default state.
    """
    if uid not in layer_uids:
        return None
    return filter_for([uid], layer_uids)
