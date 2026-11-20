"""Workpiece Selection tab: the editable counterpart of the read-only
Workpieces tab.

All reads and writes go through Rayforge's own ``Step.workpiece_uids``
filter. Writes use ``set_step_property`` so they are undoable and
notify listeners. The selection rules live in ``selection_model``.
"""

from gettext import gettext as _
from typing import TYPE_CHECKING, Any

from gi.repository import Adw, Gtk

from rayforge.ui_gtk.doceditor.step_settings.pages.base import (
    StepSettingsPage,
)

from . import selection_model as model

if TYPE_CHECKING:
    from rayforge.doceditor.editor import DocEditor


class WorkpieceSelectionPage(StepSettingsPage):
    """Tick the workpieces of the step's layer that the step processes."""

    show_identity = False

    def __init__(self, editor: "DocEditor", step: Any):
        super().__init__(editor, step)
        self._closed = False
        self._updating = False
        self._layer = None
        self._layer_uids: list[str] = []
        self._snapshot: list[tuple[str, str]] | None = None
        self._checks: dict[str, Gtk.CheckButton] = {}
        self._only_buttons: dict[str, Gtk.Button] = {}
        self._wp_rows: list[Adw.ActionRow] = []
        self._build_ui()
        self._connect_layer()
        self._refresh()

    # --- UI construction -------------------------------------------------

    def _build_ui(self):
        info = Adw.PreferencesGroup(
            title=_("Workpiece Selection"),
            description=_(
                "Select the workpieces processed by this step. "
                "At least one workpiece must stay selected."
            ),
        )
        self._select_all_button = Gtk.Button(label=_("Select All"))
        self._select_all_button.set_valign(Gtk.Align.CENTER)
        self._select_all_button.connect("clicked", self._on_select_all)
        info.set_header_suffix(self._select_all_button)
        self._layer_row = Adw.ActionRow(title=_("Layer"))
        self._layer_row.set_use_markup(False)
        info.add(self._layer_row)
        self.add_group(info)

        self._list_group = Adw.PreferencesGroup(
            title=_("Workpieces on this layer")
        )
        self.add_group(self._list_group)

    def _rebuild_rows(self, workpieces: list):
        for row in self._wp_rows:
            self._list_group.remove(row)
        self._wp_rows = []
        self._checks = {}
        self._only_buttons = {}
        for wp in workpieces:
            row = Adw.ActionRow(title=wp.name or _("(unnamed)"))
            row.set_use_markup(False)  # names may contain "&" or "<"
            check = Gtk.CheckButton()
            check.set_valign(Gtk.Align.CENTER)
            check.connect("toggled", self._on_check_toggled, wp.uid)
            row.add_prefix(check)
            row.set_activatable_widget(check)
            only = Gtk.Button(label=_("Only this"))
            only.add_css_class("flat")
            only.set_valign(Gtk.Align.CENTER)
            only.set_tooltip_text(
                _("Process only this workpiece and untick all others.")
            )
            only.connect("clicked", self._on_only_clicked, wp.uid)
            row.add_suffix(only)
            self._only_buttons[wp.uid] = only
            self._list_group.add(row)
            self._wp_rows.append(row)
            self._checks[wp.uid] = check

    # --- Layer tracking (same signals the read-only tab uses) -------------

    def _connect_layer(self):
        layer = self.step.layer
        if layer is None:
            return
        self._layer = layer
        layer.descendant_added.connect(self._on_layer_changed)
        layer.descendant_removed.connect(self._on_layer_changed)
        layer.descendant_updated.connect(self._on_layer_changed)

    def _disconnect_layer(self):
        layer = self._layer
        if layer is None:
            return
        self._layer = None
        for signal in (
            "descendant_added",
            "descendant_removed",
            "descendant_updated",
        ):
            try:
                getattr(layer, signal).disconnect(self._on_layer_changed)
            except KeyError:
                pass

    def _on_layer_changed(self, *args, **kwargs):
        if not self._closed:
            self._refresh()

    def _sync_widgets_to_model(self, *args):
        """Called on ``step.updated``: undo, redo, external edits."""
        if self._closed:
            return
        super()._sync_widgets_to_model()
        if self.step.layer is not self._layer:
            self._disconnect_layer()
            self._connect_layer()
        self._refresh()

    # --- Refresh ---------------------------------------------------------

    def _refresh(self):
        workpieces = (
            list(self._layer.all_workpieces)
            if self._layer and self._uses_workpieces()
            else []
        )
        self._layer_uids = [wp.uid for wp in workpieces]
        snapshot = [(wp.uid, wp.name) for wp in workpieces]
        # descendant_updated also fires while workpieces are dragged on
        # the canvas; only rebuild the rows when the list really changed.
        if snapshot != self._snapshot:
            self._snapshot = snapshot
            self._rebuild_rows(workpieces)
        self._update_states()

    def _uses_workpieces(self) -> bool:
        """False for geometry-less steps (e.g. the Command step)."""
        return bool(getattr(self.step, "needs_workpieces", True))

    def _update_states(self):
        filter_uids = list(self.step.workpiece_uids)
        selected = set(model.effective_selection(filter_uids, self._layer_uids))
        state = model.classify(filter_uids, self._layer_uids)
        only_one = len(selected) == 1

        self._updating = True
        try:
            for uid, check in self._checks.items():
                is_selected = uid in selected
                if check.get_active() != is_selected:
                    check.set_active(is_selected)
                locked = is_selected and only_one
                check.set_sensitive(not locked)
                check.set_tooltip_text(
                    _("At least one workpiece must stay selected.")
                    if locked
                    else None
                )
                # Pointless when this is already the only one processed.
                self._only_buttons[uid].set_sensitive(selected != {uid})
        finally:
            self._updating = False

        layer = self._layer
        self._layer_row.set_subtitle(layer.name if layer else "")
        self._select_all_button.set_sensitive(
            bool(self._layer_uids) and state is not model.SelectionState.ALL
        )
        self._list_group.set_description(
            self._status_text(state, len(selected), len(self._layer_uids))
        )

    def _status_text(
        self, state: model.SelectionState, selected: int, total: int
    ) -> str:
        if not self._uses_workpieces():
            return _("This step does not use workpieces.")
        if self._layer is None:
            return _("This step is not attached to a layer.")
        if state is model.SelectionState.ALL:
            return _(
                "All {total} workpieces are processed. Workpieces added "
                "later are included automatically."
            ).format(total=total)
        if state is model.SelectionState.NOTHING:
            return _(
                "None of the workpieces selected earlier exist any more, "
                "so this step currently processes nothing. "
                "Select at least one workpiece."
            )
        return _(
            "Selected: {selected} of {total}. Workpieces added later are "
            "not included automatically; use Select All to process every "
            "workpiece."
        ).format(selected=selected, total=total)

    # --- User actions ----------------------------------------------------

    def _on_check_toggled(self, check: Gtk.CheckButton, uid: str):
        if self._updating or self._closed:
            return
        new_filter = model.toggled_filter(
            list(self.step.workpiece_uids),
            self._layer_uids,
            uid,
            check.get_active(),
        )
        if new_filter is not None:
            self.set_step_property(
                "workpiece_uids",
                new_filter,
                name=_("Change workpiece selection"),
            )
        # Redraw from the model: reverts a refused change and keeps
        # every row consistent after an accepted one.
        self._update_states()

    def _on_only_clicked(self, _button, uid: str):
        if self._closed:
            return
        new_filter = model.only_filter(uid, self._layer_uids)
        if new_filter is not None:
            self.set_step_property(
                "workpiece_uids",
                new_filter,
                name=_("Select only one workpiece"),
            )
        self._update_states()

    def _on_select_all(self, _button):
        # [] is Rayforge's "all workpieces" value (never "none").
        self.set_step_property(
            "workpiece_uids", [], name=_("Select all workpieces")
        )
        self._update_states()

    # --- Lifecycle -------------------------------------------------------

    def _cleanup(self):
        self._closed = True
        self._disconnect_layer()
        try:
            self.step.updated.disconnect(self._sync_widgets_to_model)
        except (KeyError, ValueError, TypeError):
            pass
        super()._cleanup()
