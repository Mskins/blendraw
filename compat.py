"""Blender version compatibility helpers.

This addon targets Blender 5.0+ where the compositor tree moved from
``scene.node_tree`` to ``scene.compositing_node_group``.  All direct API
poking lives here so the rest of the addon never has to care.
"""

import bpy


def get_compositor_tree(scene):
    """Return the scene compositor node tree, or ``None`` when unavailable."""
    tree = getattr(scene, "compositing_node_group", None)
    if tree is not None:
        return tree
    return getattr(scene, "node_tree", None)


def ensure_compositor_tree(scene):
    """Return the compositor tree, creating and assigning one if missing."""
    tree = get_compositor_tree(scene)
    if tree is not None:
        return tree

    # Blender 5.0: ``scene.use_nodes`` no longer creates a tree by itself.
    tree = bpy.data.node_groups.new(name="Compositing Nodetree", type="CompositorNodeTree")
    scene.compositing_node_group = tree
    return tree


def enable_compositing(scene):
    """Turn on rendering-time compositing when the property exists."""
    if hasattr(scene.render, "use_compositing"):
        scene.render.use_compositing = True


def area_ui_type():
    """``context.area.ui_type`` or ``None`` when running without a UI."""
    area = getattr(bpy.context, "area", None)
    return getattr(area, "ui_type", None)


def active_space():
    """The active space of the current area, or ``None``."""
    area = getattr(bpy.context, "area", None)
    spaces = getattr(area, "spaces", None) if area is not None else None
    if spaces:
        return spaces.active or spaces[0]
    return None


def tag_redraw():
    """Redraw every area; safe to call from background mode."""
    screen = getattr(bpy.context, "screen", None)
    if not screen:
        return
    for area in screen.areas:
        area.tag_redraw()
