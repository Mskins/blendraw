"""Initialise, repair and tear down the BlendRaw compositor setup."""

import bpy

from ..compat import enable_compositing, ensure_compositor_tree
from ..core import tree


def initialize(scene, asset_path) -> bool:
    """Build (or repair) the compositor chain and return ``True`` on success."""
    view_prefs = bpy.context.preferences.view
    if view_prefs.language != "en_US" and view_prefs.use_translate_new_dataname:
        # Node names are the addon's contract; translated data names would break it.
        view_prefs.use_translate_new_dataname = False

    scene.use_nodes = True
    node_tree = ensure_compositor_tree(scene)
    if node_tree is None:
        return False
    enable_compositing(scene)

    render_layers = tree.ensure_node(node_tree, "CompositorNodeRLayers", "Render Layers")
    anchor = render_layers.location
    file_output = tree.ensure_node(
        node_tree,
        "CompositorNodeOutputFile",
        "File Output",
        location=(anchor[0] + 1200.0, anchor[1] + 200.0),
    )

    try:
        group_node = tree.ensure_blendraw_node(node_tree, asset_path)
    except RuntimeError as exc:
        print(f"[BlendRaw] {exc}")
        return False

    output_node = tree.ensure_output_node(node_tree)
    output_node.location = (anchor[0] + 800.0, anchor[1] + 200.0)
    viewer = tree.ensure_node(
        node_tree, "CompositorNodeViewer", "Viewer", location=(anchor[0] + 1000.0, anchor[1] + 200.0)
    )

    tree.link(node_tree, group_node.inputs.get("Image"), render_layers.outputs[0])
    output_socket = tree.ensure_output_socket(node_tree, output_node, "Image")
    tree.link(node_tree, output_socket, group_node.outputs.get("Image"))
    tree.link(node_tree, viewer.inputs.get("Image"), group_node.outputs.get("Image"))

    from ..core import state

    state.sync_from_viewports(scene)

    if file_output is not None:
        scene.braw_to_file_output = True
        # Setting the property is a no-op when it was already true, so make
        # sure the slot exists even in that case.
        if scene.braw_to_file_output:
            tree.link_file_output(True)

    scene.render.compositor_device = "GPU"
    return True


class BRawInitialize(bpy.types.Operator):
    bl_idname = "braw.initialize"
    bl_label = "Initialize BlendRaw"
    bl_description = "Initialize BlendRaw Basic Settings"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        from ..paths import ASSET_PATH

        if not initialize(context.scene, ASSET_PATH):
            self.report({"ERROR"}, "BlendRaw: could not initialise the compositor")
            return {"CANCELLED"}
        return {"FINISHED"}


class BRawCleanup(bpy.types.Operator):
    bl_idname = "braw.cleanup"
    bl_label = "Clean up BlendRaw Nodes Group"
    bl_description = "Clean up BlendRaw Nodes Group"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        if not tree.cleanup_scene(context):
            self.report({"WARNING"}, "BlendRaw: nothing to clean up")
            return {"CANCELLED"}
        return {"FINISHED"}


CLASSES = (BRawInitialize, BRawCleanup)
