"""Safe access to compositor nodes and the BlendRaw node group.

All node lookups go through this module.  Nothing here raises when a node,
socket or node group is missing: callers get ``None``/``False`` and the UI
degrades gracefully instead of crashing the whole panel draw.
"""

import bpy

from ..compat import area_ui_type, get_compositor_tree

BLENDRAW = "BlendRaw"
FILE_OUTPUT_SLOT = "Image_BRaw"
ASSET_FILENAME = "BlendRaw_Node_E.blend"


# --- Lookups ---------------------------------------------------------------

def scene_tree(scene=None):
    return get_compositor_tree(scene or bpy.context.scene)


def get_group(name):
    return bpy.data.node_groups.get(name)


def get_node(group_name, node_name):
    group = get_group(group_name)
    if group is None:
        return None
    return group.nodes.get(node_name)


def input_socket(node, name=None, index=None):
    """Resolve an input socket by name, falling back to its historical index.

    Several nodes (Color Balance, Glare) expose two sockets with the same
    name (a float factor and a color), so the index is checked first *and*
    validated against the expected name before the plain name lookup.
    """
    if node is None:
        return None
    if index is not None:
        try:
            socket = node.inputs[index]
        except (IndexError, TypeError):
            socket = None
        if socket is not None and socket.bl_idname != "NodeSocketVirtual":
            if name is None or socket.name == name:
                return socket
    if name:
        socket = node.inputs.get(name)
        if socket is not None:
            return socket
    return None


def get_input(group_name, node_name, name=None, index=None):
    return input_socket(get_node(group_name, node_name), name, index)


def set_input(group_name, node_name, value, name=None, index=None, component=None) -> bool:
    socket = get_input(group_name, node_name, name, index)
    if socket is None:
        return False
    try:
        if component is None:
            socket.default_value = value
        else:
            socket.default_value[component] = value
        return True
    except (AttributeError, TypeError, IndexError, ValueError):
        return False


def get_value(group_name, node_name, name=None, index=None, component=None):
    socket = get_input(group_name, node_name, name, index)
    if socket is None:
        return None
    from_value = socket.default_value
    if component is not None:
        try:
            return from_value[component]
        except (IndexError, TypeError):
            return None
    return from_value


def set_property(node, prop, value) -> bool:
    if node is None or not hasattr(node, prop):
        return False
    try:
        setattr(node, prop, value)
        return True
    except (AttributeError, TypeError, ValueError):
        return False


# --- Switch nodes ----------------------------------------------------------
# Blender 5.0 renamed the boolean input from "Check" to "Switch".

SWITCH_INPUTS = ("Switch", "Check")


def switch_socket(node):
    if node is None:
        return None
    for name in SWITCH_INPUTS:
        socket = node.inputs.get(name)
        if socket is not None:
            return socket
    return None


def get_switch(node) -> bool:
    socket = switch_socket(node)
    if socket is None:
        return False
    try:
        return bool(socket.default_value)
    except (AttributeError, TypeError):
        return False


def set_switch(node, value) -> bool:
    socket = switch_socket(node)
    if socket is None:
        return False
    try:
        socket.default_value = bool(value)
        return True
    except (AttributeError, TypeError):
        return False


# --- Scene compositor wiring ----------------------------------------------

def find_by_type(tree, bl_idname):
    """Return the first node of ``bl_idname`` in ``tree`` (names are user-editable)."""
    if tree is None:
        return None
    for node in tree.nodes:
        if node.bl_idname == bl_idname:
            return node
    return None


def ensure_node(tree, bl_idname, name=None, location=None):
    """Return an existing node of this type, creating one only when needed.

    Node names are localised and user-editable, so a name lookup alone would
    duplicate singleton nodes (Viewer, File Output, Render Layers).  Matching
    by type keeps user-created and renamed nodes intact.
    """
    if name:
        existing = tree.nodes.get(name)
        if existing is not None and existing.bl_idname == bl_idname:
            return existing
    existing = find_by_type(tree, bl_idname)
    if existing is not None:
        return existing
    node = tree.nodes.new(type=bl_idname)
    if name:
        node.name = name
        node.label = name
    if location is not None:
        node.location = location
    return node


def get_output_node(tree):
    if tree is None:
        return None
    if "Composite" in tree.nodes:
        return tree.nodes["Composite"]
    output = tree.nodes.get("Group Output")
    if output is not None:
        return output
    return find_by_type(tree, "NodeGroupOutput")


def ensure_interface_output(tree, name="Image", socket_type="NodeSocketColor"):
    interface = tree.interface
    for item in interface.items_tree:
        if (
            getattr(item, "item_type", "SOCKET") == "SOCKET"
            and item.name == name
            and item.in_out == "OUTPUT"
        ):
            return item
    try:
        return interface.new_socket(name=name, in_out="OUTPUT", socket_type=socket_type)
    except (TypeError, RuntimeError) as exc:
        print(f"[BlendRaw] Could not create '{name}' output socket: {exc}")
        return None


def ensure_output_socket(tree, output_node, name="Image"):
    """Make sure the group output node exposes ``name`` and return that input."""
    if output_node is None:
        return None
    socket = output_node.inputs.get(name)
    if socket is not None:
        return socket
    ensure_interface_output(tree, name)
    socket = output_node.inputs.get(name)
    if socket is not None:
        return socket
    try:
        output_node.inputs.new("NodeSocketColor", name)
    except (RuntimeError, TypeError):
        pass
    return output_node.inputs.get(name)


def ensure_output_node(tree):
    output_node = get_output_node(tree)
    if output_node is not None:
        return output_node
    output_node = tree.nodes.new(type="NodeGroupOutput")
    ensure_output_socket(tree, output_node, "Image")
    return output_node


def link(tree, to_socket, from_socket, replace=True):
    """Create ``from_socket -> to_socket``; idempotent when already linked."""
    if tree is None or to_socket is None or from_socket is None:
        return None
    if to_socket.is_linked and replace:
        for existing in list(to_socket.links):
            tree.links.remove(existing)
    try:
        return tree.links.new(input=to_socket, output=from_socket)
    except RuntimeError as exc:
        print(f"[BlendRaw] Link failed: {exc}")
        return None


def _anchor(tree):
    render_layers = find_by_type(tree, "CompositorNodeRLayers")
    return render_layers.location if render_layers is not None else None


def ensure_blendraw_node(tree, asset_path):
    """Append the BlendRaw node group when needed and return its group node."""
    group = get_group(BLENDRAW)
    if group is None:
        before = set(bpy.data.node_groups)
        bpy.ops.wm.append(directory=asset_path + r"\NodeTree", filename=BLENDRAW, link=False)
        appended = [g for g in bpy.data.node_groups if g not in before]
        group = appended[0] if appended else None
        if group is None:
            raise RuntimeError(f"BlendRaw node group missing from {asset_path}")

    node = tree.nodes.get(BLENDRAW)
    if node is None:
        node = tree.nodes.new(type="CompositorNodeGroup")
        node.name = BLENDRAW
    node.node_tree = group

    anchor = _anchor(tree)
    if anchor is not None:
        node.location = (anchor[0] + 600.0, anchor[1] + 200.0)
    else:
        node.location = (600.0, 200.0)
    return node


def remove_blendraw_node(tree):
    node = tree.nodes.get(BLENDRAW)
    if node is not None:
        tree.nodes.remove(node)
    return node is not None


def link_file_output(enabled):
    """(Dis)connect BlendRaw to a dedicated ``Image_BRaw`` File Output slot."""
    tree = scene_tree()
    if tree is None:
        return False
    output_node = find_by_type(tree, "CompositorNodeOutputFile")
    if output_node is None:
        return False

    if enabled:
        group_node = tree.nodes.get(BLENDRAW)
        if group_node is None:
            return False
        items = output_node.file_output_items
        if not any(item.name == FILE_OUTPUT_SLOT for item in items):
            try:
                items.new(socket_type="RGBA", name=FILE_OUTPUT_SLOT)
            except (AttributeError, TypeError, RuntimeError) as exc:
                print(f"[BlendRaw] Could not add file output slot: {exc}")
                return False
        target = output_node.inputs.get(FILE_OUTPUT_SLOT)
        if target is None and len(output_node.inputs):
            target = output_node.inputs[-1]
        source = group_node.outputs.get("Image")
        return link(tree, target, source) is not None

    return remove_file_output_slot()


def remove_file_output_slot():
    tree = scene_tree()
    if tree is None:
        return False
    output_node = find_by_type(tree, "CompositorNodeOutputFile")
    if output_node is None:
        return False

    items = getattr(output_node, "file_output_items", None)
    if items is not None:
        item = items.get(FILE_OUTPUT_SLOT)
        if item is not None:
            items.remove(item)
            return True
        return False

    slots = getattr(output_node, "file_slots", None)
    if slots is not None and FILE_OUTPUT_SLOT in slots:
        output_node.active_input_index = slots.find(FILE_OUTPUT_SLOT)
        bpy.ops.node.output_file_remove_active_socket("INVOKE_DEFAULT")
        return True
    return False


def cleanup_scene(context):
    """Remove BlendRaw from the scene and restore a straight Render Layers path."""
    tree = scene_tree()
    if tree is None:
        return False

    if area_ui_type() == "CompositorNodeTree":
        remove_file_output_slot()

    if tree.nodes.get(BLENDRAW) is None:
        return False

    remove_blendraw_node(tree)

    render_layers = find_by_type(tree, "CompositorNodeRLayers")
    output_node = get_output_node(tree)
    if render_layers is not None:
        output_socket = ensure_output_socket(tree, output_node, "Image")
        if output_socket is not None:
            link(tree, output_socket, render_layers.outputs[0])
        viewer = find_by_type(tree, "CompositorNodeViewer")
        if viewer is not None:
            link(tree, viewer.inputs.get("Image"), render_layers.outputs[0])

    bpy.data.orphans_purge(do_recursive=True)
    return True
