"""Scene-level properties and their update callbacks.

Property identifiers live in the ``braw_`` namespace.  They are persisted in
saved .blend files, so treat them as a data schema: add new keys rather than
renaming existing ones.
"""

import bpy
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    IntProperty,
    StringProperty,
)

from .. import presets
from ..compat import tag_redraw
from ..ui import icons
from . import spec, tree


class BlendRawPresetItem(bpy.types.PropertyGroup):
    lable: StringProperty(name="Lable", default="")
    name: StringProperty(name="Name", default="")


# --- Enum item tables ------------------------------------------------------

PANEL_ITEMS = (
    ("Color Adjust", "Color Adjust", "", icons.icon("BRUSHES_ALL"), 0),
    ("Glare Effects", "Glare Effects", "", icons.icon("SHADERFX"), 1),
)

VIEW3D_ITEMS = (
    ("Disabled", "Disabled", "The compositor is disabled", 0, 0),
    ("Camera", "Camera", "The compositor is enabled only in camera view", 0, 1),
    ("Always", "Always", "The compositor is enabled regardless of the view", 0, 2),
)

GREY_SPACE_ITEMS = (
    ("Standard", "Standard", "", 0, 0),
    ("Khronos PBR", "Khronos PBR", "", 0, 1),
    ("AgX", "AgX", "", 0, 2),
    ("Filmic", "Filmic", "", 0, 3),
)

_category_items = []


def _tag_items(self, context):
    return [
        (tag, tag, description, icons.icon(icon_name), i)
        for i, (tag, description, icon_name) in enumerate(spec.SELECTIVE_TAGS)
    ]


def _category_items_cb(self, context):
    if not _category_items:
        scene = getattr(context, "scene", None)
        refresh_categories(scene)
    return _category_items


def refresh_categories(scene=None):
    """Rebuild the preset category enum from disk and select a valid entry.

    Blender calls the addon's ``register()`` with a restricted context that has
    no ``scene``, so the scene part is entirely optional.
    """
    global _category_items
    names = presets.categories()
    _category_items = [
        (name, name, "", icons.icon("OUTLINER"), i) for i, name in enumerate(names)
    ]
    if scene is None:
        scene = getattr(bpy.context, "scene", None)
    if scene is not None and names:
        try:
            if scene.braw_presets_category not in names:
                scene.braw_presets_category = names[0]
        except (AttributeError, TypeError):
            pass
    return names


def refresh_preset_collection(scene=None):
    scene = scene or bpy.context.scene
    collection = scene.braw_presets
    collection.clear()
    category = scene.braw_presets_category
    for name in presets.presets(category):
        item = collection.add()
        item.lable = name
        item.name = name


# --- Update callbacks ------------------------------------------------------

def iter_view3d_spaces():
    """Yield every 3D viewport space in every window of the session."""
    window_manager = getattr(bpy.context, "window_manager", None)
    if window_manager is None:
        return
    for window in window_manager.windows:
        screen = getattr(window, "screen", None)
        if screen is None:
            continue
        for area in screen.areas:
            if area.type != "VIEW_3D":
                continue
            for space in area.spaces:
                if space.type == "VIEW_3D":
                    yield space


def apply_compositor_mode(mode, redraw=True):
    """Apply the viewport compositor mode to every 3D view in every window."""
    changed = False
    for space in iter_view3d_spaces():
        shading = getattr(space, "shading", None)
        if shading is None or shading.use_compositor == mode:
            continue
        try:
            shading.use_compositor = mode
            changed = True
        except (AttributeError, TypeError):
            pass
    if changed and redraw:
        tag_redraw()
    return changed


# Set once the user (or the addon) has made an explicit choice; until then the
# timer stays out of the way so it never fights a fresh scene.
_sync_enabled = False


def update_view3d_use_compositor(self, context):
    global _sync_enabled
    _sync_enabled = True
    apply_compositor_mode(self.braw_view3d_compositor.upper())


def update_view3d_always(self, context):
    if self.braw_view3d_compositor_always:
        self.braw_view3d_compositor = "Always"
    else:
        self.braw_view3d_compositor = "Disabled"


def sync_from_viewports(scene):
    """Unify all viewports with the stored choice (or adopt it when unset)."""
    global _sync_enabled
    spaces = list(iter_view3d_spaces())
    if not spaces:
        return False

    stored = scene.braw_view3d_compositor
    if stored not in ("", "Disabled"):
        _sync_enabled = True
        apply_compositor_mode(stored.upper())
        return True

    shading = getattr(spaces[0], "shading", None)
    if shading is None:
        return False
    mode = shading.use_compositor
    _sync_enabled = True
    target = mode.title()
    if stored != target:
        scene.braw_view3d_compositor = target
    else:
        apply_compositor_mode(mode)
    return True


def sync_view3d_compositor():
    """Timer callback: keep new windows/workspaces on the chosen mode."""
    if not _sync_enabled:
        return 1.5
    scene = getattr(bpy.context, "scene", None)
    mode = getattr(scene, "braw_view3d_compositor", None) if scene is not None else None
    if mode:
        apply_compositor_mode(mode.upper())
    return 1.5


def update_to_file_output(self, context):
    tree.link_file_output(bool(self.braw_to_file_output))


_GREY_SPACE_SOCKETS = {
    "Standard": ("Standard",),
    "Khronos PBR": ("Khronos PBR",),
    "AgX": ("AgX",),
    "Filmic": ("Filmic",),
}
_GREY_SPACE_ALL = ("AgX", "Filmic", "Khronos PBR", "Standard")


def update_grey_removal_space(self, context):
    enabled = _GREY_SPACE_SOCKETS.get(self.braw_grey_removal_space, ())
    for name in _GREY_SPACE_ALL:
        value = 1.0 if name in enabled else 0.0
        tree.set_input("BlendRaw", "Q_Grey Removal", value, name=name)


def _safe(view_settings, prop, value):
    try:
        setattr(view_settings, prop, value)
    except (AttributeError, TypeError):
        pass


TRANSFORM_TO_SPACE = {
    "Khronos PBR Neutral": "Khronos PBR",
    "AgX": "AgX",
    "Filmic": "Filmic",
}
SPACE_TO_TRANSFORM = {space: transform for transform, space in TRANSFORM_TO_SPACE.items()}


def _convert_switches():
    group = tree.get_group("Q_Convert Colorspace")
    if group is None:
        return None
    return {
        "Khronos PBR": group.nodes.get("BR to Khronos PBR"),
        "AgX": group.nodes.get("BR to AGX"),
        "Filmic": group.nodes.get("BR to Filmic"),
    }


def update_convert_colorspace(self, context):
    """Swap between scene-managed and node-managed view transform.

    The pre-conversion transform and look are stored on the scene, so restoring
    still works after the node group was re-appended ("Repair node group"), after
    a file reload, or after the user changed the view transform manually while
    converted.  Without that record a re-appended node group loses its switch
    state and the scene would be stuck in Raw forever.
    """
    switches = _convert_switches()
    if switches is None:
        return
    scene = context.scene if context is not None and getattr(context, "scene", None) else bpy.context.scene
    view = scene.view_settings
    active = [space for space, node in switches.items() if tree.get_switch(node)]
    stored = scene.braw_prev_view_transform

    if self.braw_convert_colorspace:
        current = view.view_transform
        if current in TRANSFORM_TO_SPACE:
            scene.braw_prev_view_transform = current
            scene.braw_prev_look = view.look
            target_space = TRANSFORM_TO_SPACE[current]
        elif active:
            target_space = active[0]
        elif stored in TRANSFORM_TO_SPACE:
            target_space = TRANSFORM_TO_SPACE[stored]
        else:
            # Nothing representable to convert from (e.g. already Raw with no
            # recorded transform): leave the scene untouched.
            return

        for space, node in switches.items():
            tree.set_switch(node, space == target_space)
        _safe(view, "view_transform", "Raw")
        _safe(view, "look", "None")
        self.braw_grey_removal_space = target_space
        return

    transform = SPACE_TO_TRANSFORM.get(active[0]) if active else None
    if transform is None and stored in TRANSFORM_TO_SPACE:
        transform = stored
    if transform:
        _safe(view, "view_transform", transform)
    if scene.braw_prev_look:
        _safe(view, "look", scene.braw_prev_look)

    for node in switches.values():
        tree.set_switch(node, False)

    grey = tree.get_node("BlendRaw", "Q_Grey Removal")
    if grey is not None:
        grey.mute = True


def update_display_presets_panel(self, context):
    scene = context.scene if context is not None and context.scene else bpy.context.scene
    if not self.braw_show_presets:
        return
    refresh_categories(scene)
    refresh_preset_collection(scene)


def update_presets_category(self, context):
    refresh_preset_collection(context.scene)


# --- Registration ----------------------------------------------------------

def register_properties():
    bpy.types.Scene.braw_view3d_compositor = EnumProperty(
        name="View3D Use Compositor",
        description="",
        items=VIEW3D_ITEMS,
        update=update_view3d_use_compositor,
    )
    bpy.types.Scene.braw_view3d_compositor_always = BoolProperty(
        name="View3D Use Compositor Always",
        description="",
        default=False,
        update=update_view3d_always,
    )
    bpy.types.Scene.braw_selective_color_tag = EnumProperty(
        name="Selective Color Tags",
        description="",
        items=_tag_items,
    )
    bpy.types.Scene.braw_convert_colorspace = BoolProperty(
        name="BlendRaw Convert Colorspace",
        description="",
        default=False,
        update=update_convert_colorspace,
    )
    bpy.types.Scene.braw_to_file_output = BoolProperty(
        name="To File Output",
        description="Available when File Output Node in Compositor",
        default=False,
        update=update_to_file_output,
    )
    bpy.types.Scene.braw_panel = EnumProperty(
        name="BlendRaw Panel",
        description="",
        items=PANEL_ITEMS,
    )
    bpy.types.Scene.braw_grey_removal_space = EnumProperty(
        name="Grey Removal Color Space",
        description="",
        items=GREY_SPACE_ITEMS,
        update=update_grey_removal_space,
    )
    bpy.types.Scene.braw_show_histogram = BoolProperty(name="Display Histogram", default=False)
    bpy.types.Scene.braw_show_waveform = BoolProperty(name="Display Waveform", default=False)
    bpy.types.Scene.braw_show_vectorscope = BoolProperty(name="Display Vectorscope", default=False)
    bpy.types.Scene.braw_show_presets = BoolProperty(
        name="Display Presets Panel",
        default=False,
        update=update_display_presets_panel,
    )
    bpy.types.Scene.braw_presets_index = IntProperty(name="Presets Index", default=0)
    bpy.types.Scene.braw_presets_category = EnumProperty(
        name="Presets Categories",
        description="",
        items=_category_items_cb,
        update=update_presets_category,
    )
    bpy.types.Scene.braw_presets = CollectionProperty(
        name="Preset Collection",
        type=BlendRawPresetItem,
    )
    # Hidden bookkeeping for the colours-space toggle (persisted in the .blend).
    bpy.types.Scene.braw_prev_view_transform = StringProperty(
        name="BlendRaw Previous View Transform", default=""
    )
    bpy.types.Scene.braw_prev_look = StringProperty(
        name="BlendRaw Previous Look", default=""
    )


def unregister_properties():
    for name in (
        "braw_view3d_compositor",
        "braw_view3d_compositor_always",
        "braw_selective_color_tag",
        "braw_convert_colorspace",
        "braw_to_file_output",
        "braw_panel",
        "braw_grey_removal_space",
        "braw_show_histogram",
        "braw_show_waveform",
        "braw_show_vectorscope",
        "braw_show_presets",
        "braw_presets_index",
        "braw_presets_category",
        "braw_presets",
        "braw_prev_view_transform",
        "braw_prev_look",
    ):
        if hasattr(bpy.types.Scene, name):
            delattr(bpy.types.Scene, name)


__all__ = [
    "BlendRawPresetItem",
    "refresh_categories",
    "refresh_preset_collection",
    "register_properties",
    "unregister_properties",
]
