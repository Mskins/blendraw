"""Icon helpers.

The original addon resolved icons from strings at runtime (``string_to_icon``)
and kept one preview collection for the SVG logo.  Both are wrapped here so UI
code never touches ``bpy.types.UILayout.bl_rna`` directly.
"""

import os

import bpy
import bpy.utils.previews

_preview_collection = None


def icon(name_or_number):
    """Resolve an icon name (``"TRASH"``) or a raw icon number to an icon value."""
    if isinstance(name_or_number, int):
        return name_or_number
    parameters = bpy.types.UILayout.bl_rna.functions["prop"].parameters["icon"]
    entry = parameters.enum_items.get(name_or_number)
    if entry is not None:
        return entry.value
    try:
        return int(name_or_number)
    except (TypeError, ValueError):
        return 0


def mute_icon(muted: bool):
    """Icon for a section's mute toggle.

    The original addon used the (now removed) handle/keyframe icons; fall back
    to checkboxes when those are unavailable.
    """
    legacy = icon("HANDLETYPE_FREE_VEC" if muted else "KEYTYPE_KEYFRAME_VEC")
    if legacy:
        return legacy
    return icon("CHECKBOX_DEHLT" if muted else "CHECKBOX_HLT")


def init_previews():
    global _preview_collection
    if _preview_collection is None:
        _preview_collection = bpy.utils.previews.new()
    return _preview_collection


def free_previews():
    global _preview_collection
    if _preview_collection is not None:
        bpy.utils.previews.remove(_preview_collection)
        _preview_collection = None


def image_icon(path):
    """Load an image as a preview icon; returns 0 when the file is missing."""
    if _preview_collection is None or not os.path.exists(path):
        return 0
    if path not in _preview_collection:
        _preview_collection.load(path, path, "IMAGE")
    return _preview_collection[path].icon_id
