"""BlendRaw - fast colour grading for Blender's realtime compositor.

This package is a structured rewrite of the original single-file,
Serpens-generated addon.  The colour pipeline itself is still shipped as the
``BlendRaw`` node group asset; everything else (UI, operators, presets,
wiring) is plain, typed Python.
"""

bl_info = {
    "name": "快捷调色BlendRaw",
    "author": "亮锅不服LAO",
    "description": "使用 Blender 的实时合成进行快速调色",
    "blender": (5, 0, 0),
    "version": (0, 3, 0),
    "location": "3D View",
    "warning": "",
    "doc_url": "https://qaddons.com/",
    "tracker_url": "https://space.bilibili.com/429605217?spm_id_from=333.1007.0.0",
    "category": "亮锅出品",
}

import bpy
from bpy.props import StringProperty

from . import localdb
from .compat import tag_redraw
from .core import state
from .ops import gizmo, initialize, presets as preset_ops, reset
from .ui import icons, panels

# --- Preference-driven panel category -------------------------------------

DEFAULT_CATEGORY = "BRaw"


def update_panel(self, context):
    """Re-register the panels under the category chosen in the preferences."""
    try:
        for panel in panels.PANEL_CLASSES:
            if "bl_rna" in panel.__dict__:
                bpy.utils.unregister_class(panel)
        for panel in panels.PANEL_CLASSES:
            panel.bl_category = self.category
            bpy.utils.register_class(panel)
    except Exception as exc:  # pragma: no cover - UI-level failure
        print(f"[BlendRaw] Updating the panel category failed: {exc}")


class BlendRawPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    category: StringProperty(
        name="Tab Category",
        description="Choose a name for the category of the panel",
        default=DEFAULT_CATEGORY,
        update=update_panel,
    )

    def draw(self, context):
        column = self.layout.column()
        column.label(text="Tab Category:")
        column.prop(self, "category", text="")


# --- Tool header button ----------------------------------------------------

def draw_view3d_tool_header(self, context):
    self.layout.prop(
        context.scene,
        "braw_view3d_compositor_always",
        text="",
        icon_value=icons.icon("HIDE_OFF"),
    )


# --- Load handlers ---------------------------------------------------------

def on_load_post(_dummy):
    scene = getattr(bpy.context, "scene", None)
    if scene is None:
        return
    try:
        state.sync_from_viewports(scene)
        scene.braw_show_presets = False
        state.refresh_categories(scene)
        state.refresh_preset_collection(scene)
    except (AttributeError, TypeError):
        pass


# --- Registration ----------------------------------------------------------

CLASSES = (
    state.BlendRawPresetItem,
    BlendRawPreferences,
) + gizmo.CLASSES + initialize.CLASSES + reset.CLASSES + preset_ops.CLASSES + panels.PANEL_CLASSES


def _saved_category():
    try:
        preferences = bpy.context.preferences.addons[__name__].preferences
        return preferences.category or DEFAULT_CATEGORY
    except (KeyError, AttributeError):
        return DEFAULT_CATEGORY


def register():
    icons.init_previews()
    category = _saved_category()
    for panel in panels.PANEL_CLASSES:
        panel.bl_category = category

    for cls in CLASSES:
        bpy.utils.register_class(cls)

    state.register_properties()

    bpy.app.handlers.load_post.append(on_load_post)
    bpy.types.VIEW3D_HT_tool_header.append(draw_view3d_tool_header)
    if not bpy.app.timers.is_registered(state.sync_view3d_compositor):
        bpy.app.timers.register(state.sync_view3d_compositor, first_interval=1.5, persistent=True)
    localdb.register()


def unregister():
    localdb.unregister()

    if bpy.app.timers.is_registered(state.sync_view3d_compositor):
        bpy.app.timers.unregister(state.sync_view3d_compositor)

    try:
        bpy.types.VIEW3D_HT_tool_header.remove(draw_view3d_tool_header)
    except ValueError:
        pass

    if on_load_post in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(on_load_post)

    state.unregister_properties()

    for cls in reversed(CLASSES):
        if "bl_rna" in cls.__dict__:
            bpy.utils.unregister_class(cls)

    icons.free_previews()
    tag_redraw()


if __name__ == "__main__":
    register()
