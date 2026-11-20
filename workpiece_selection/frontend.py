"""Frontend entry point of the Workpiece Selection addon."""

from rayforge.core.hooks import hookimpl

from .extension import extend_registered_pages

ADDON_NAME = "workpiece_selection"

# Assembler names (``step.ASSEMBLER_NAME``) that get the tab. To support
# another operation, add its name here. Pages are discovered from the
# registry, so no per-operation code is needed as long as the step
# processes workpieces through the standard ``workpiece_uids`` filter.
#
# Do NOT add "material_test_grid": Rayforge identifies those steps by
# ``workpiece_uids == [<test workpiece>]``, so editing it breaks the link.
SUPPORTED_ASSEMBLERS: tuple[str, ...] = ("contour", "raster", "offset_fill")


# trylast: pluggy calls hooks of later-registered plugins first, and
# Laser Essentials registers *its* Contour page in this same hook. We
# must run after it to find and extend its class instead of being
# overwritten by it.
@hookimpl(trylast=True)
def register_step_settings_pages(step_settings_page_registry):
    extend_registered_pages(
        step_settings_page_registry, SUPPORTED_ASSEMBLERS, ADDON_NAME
    )
