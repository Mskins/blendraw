"""Preset storage for the BlendRaw node group.

Presets are stored exactly like the original addon stored them, so existing
user presets keep working: one directory per category under
``<blender user config>/BlendRaw Presets``, one ``.blend`` datablock per preset.

Only the storage-level logic lives here.  The operators that call it are in
``ops/presets.py``.
"""

import os

import bpy

PRESETS_DIRNAME = "BlendRaw Presets"
NODE_GROUP_NAME = "BlendRaw"


def presets_root() -> str:
    """Absolute path of the preset root directory."""
    return os.path.join(bpy.utils.resource_path("USER"), "config", PRESETS_DIRNAME)


def ensure_root() -> str:
    root = presets_root()
    os.makedirs(root, exist_ok=True)
    return root


def _valid_name(name: str) -> bool:
    """Reject names that would escape the preset directory."""
    if not name or name in {".", ".."}:
        return False
    separators = {os.sep, os.altsep, "/", "\\"}
    return not any(sep and sep in name for sep in separators)


def category_path(category: str) -> str:
    return os.path.join(presets_root(), category)


def categories() -> list:
    """Sorted category names present on disk."""
    root = ensure_root()
    try:
        entries = os.listdir(root)
    except OSError:
        return []
    return sorted(name for name in entries if os.path.isdir(os.path.join(root, name)))


def first_category() -> str:
    found = categories()
    return found[0] if found else ""


def presets(category: str) -> list:
    """Sorted preset names (file stems) inside ``category``."""
    if not category or not _valid_name(category):
        return []
    directory = category_path(category)
    try:
        entries = os.listdir(directory)
    except OSError:
        return []
    stems = []
    for entry in entries:
        path = os.path.join(directory, entry)
        if os.path.isfile(path):
            stems.append(os.path.splitext(entry)[0])
    return sorted(stems)


def preset_path(category: str, name: str) -> str:
    return os.path.join(category_path(category), f"{name}.blend")


def create_category(name: str) -> str:
    """Create a category directory.

    Returns ``"created"``, ``"exists"`` or ``"invalid"``.
    """
    if not _valid_name(name):
        return "invalid"
    if os.path.isdir(category_path(name)):
        return "exists"
    os.makedirs(category_path(name), exist_ok=True)
    return "created"


def delete_category(category: str) -> bool:
    """Delete every preset file in the category, then the directory itself."""
    directory = category_path(category)
    if not os.path.isdir(directory):
        return False
    for entry in os.listdir(directory):
        path = os.path.join(directory, entry)
        if os.path.isfile(path):
            try:
                os.remove(path)
            except OSError:
                pass
    try:
        os.rmdir(directory)
    except OSError:
        return False
    return True


def save_preset(category: str, name: str) -> bool:
    """Write the current ``BlendRaw`` node group as a preset."""
    if not _valid_name(category) or not _valid_name(name):
        return False
    group = bpy.data.node_groups.get(NODE_GROUP_NAME)
    if group is None:
        return False
    path = preset_path(category, name)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        bpy.data.libraries.write(path, {group}, path_remap="RELATIVE", fake_user=True)
        return True
    except (OSError, RuntimeError) as exc:
        print(f"[BlendRaw] Failed to save preset '{path}': {exc}")
        return False


def delete_preset(category: str, name: str) -> bool:
    try:
        os.remove(preset_path(category, name))
        return True
    except OSError:
        return False
