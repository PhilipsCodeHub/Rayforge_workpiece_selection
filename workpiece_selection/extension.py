"""Operation-independent logic for extending step settings pages.

This module deliberately has no GTK or Rayforge imports at module level,
so it can be unit tested without a display. It knows nothing about
Contour: it extends *whatever page class is registered* for a given
assembler name. Supporting another operation is therefore a one-line
change to ``frontend.SUPPORTED_ASSEMBLERS``.
"""

import logging
from gettext import gettext as _
from typing import Any, Iterable

logger = logging.getLogger(__name__)

TAB_METHOD = "create_workpiece_selection_page"
_WRAPPED_MARKER = "_workpiece_selection_wrapped"

# base page class -> extended subclass. Keeps one GType per base class
# even when the registration hook runs repeatedly (startup, addon
# enable/reload).
_wrapped_cache: dict[type, type] = {}


def selection_tab() -> tuple[tuple[str, str, str], ...]:
    """The ``extra_pages`` entry that declares our tab."""
    return (
        (TAB_METHOD, _("Workpiece Selection"), "object-select-symbolic"),
    )


class WorkpieceSelectionMixin:
    """Adds the producer method for the Workpiece Selection tab.

    Mixed in *before* the registered page class, so everything the
    original page provides (sections, other extra tabs) is inherited
    unchanged.
    """

    def create_workpiece_selection_page(self) -> Any:
        # Imported lazily: keeps this module importable without GTK.
        from .selection_page import WorkpieceSelectionPage

        return WorkpieceSelectionPage(
            self.editor,  # type: ignore[attr-defined]
            self.step,  # type: ignore[attr-defined]
        )


def _has_tab(page_cls: type) -> bool:
    return any(
        entry[0] == TAB_METHOD for entry in getattr(page_cls, "extra_pages", ())
    )


def wrap_page_class(base: type) -> type:
    """Return a subclass of ``base`` that also offers our tab.

    ``extra_pages`` is *concatenated* with the base's tuple. Assigning a
    new tuple instead would drop tabs the base declares (for laser
    steps: the "Laser" tab). Returns ``base`` itself if it is already
    extended, so wrapping is idempotent.
    """
    if getattr(base, _WRAPPED_MARKER, False) or _has_tab(base):
        return base
    cached = _wrapped_cache.get(base)
    if cached is not None:
        return cached
    namespace = {
        "__module__": __name__,
        "__doc__": base.__doc__,
        "extra_pages": tuple(getattr(base, "extra_pages", ()))
        + selection_tab(),
        _WRAPPED_MARKER: True,
    }
    # type(base) keeps the GObject metaclass of GTK-based pages.
    wrapped = type(base)(
        f"WorkpieceSelection{base.__name__}",
        (WorkpieceSelectionMixin, base),
        namespace,
    )
    _wrapped_cache[base] = wrapped
    return wrapped


def extend_registered_pages(
    registry: Any, assemblers: Iterable[str], addon_name: str
) -> list[str]:
    """Extend the registered page class of each assembler.

    Assemblers without a registered page (their addon is missing or
    disabled) are skipped. Returns the names actually extended.
    """
    extended: list[str] = []
    for assembler in assemblers:
        base = registry.get(assembler)
        if base is None:
            logger.warning(
                "No settings page registered for %r; "
                "Workpiece Selection tab not added",
                assembler,
            )
            continue
        wrapped = wrap_page_class(base)
        if wrapped is base:
            continue
        registry.register(assembler, wrapped, addon_name)
        extended.append(assembler)
    return extended
