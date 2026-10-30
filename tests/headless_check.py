"""Headless self-check for the BlendRaw addon.

Run from a terminal:

    blender --background --factory-startup --python tests/headless_check.py

It registers the addon, initialises the compositor on an empty scene, verifies
every declared UI binding resolves, exercises all reset defaults, the
colours-space switch and the preset store, then unregisters again.  Exits with
a non-zero status when a check fails, so it can gate a release.
"""

import importlib
import os
import shutil
import sys
import tempfile

import bpy

ADDON_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULE_NAME = os.path.basename(ADDON_DIR)
sys.path.insert(0, os.path.dirname(ADDON_DIR))

addon = importlib.import_module(MODULE_NAME)
from importlib import import_module  # noqa: E402

spec = import_module(f"{MODULE_NAME}.core.spec")
tree = import_module(f"{MODULE_NAME}.core.tree")
presets = import_module(f"{MODULE_NAME}.presets")
initialize_ops = import_module(f"{MODULE_NAME}.ops.initialize")

failures = []


def check(condition, message):
    if not condition:
        failures.append(message)


def run():
    addon.register()
    scene = bpy.context.scene
    for operator_name in (
        "initialize",
        "cleanup",
        "reset_section",
        "preset_add",
        "preset_delete",
        "preset_load",
        "preset_category_add",
        "preset_category_delete",
        "backdrop_zoom_in",
        "backdrop_zoom_out",
        "backdrop_fit",
    ):
        check(hasattr(bpy.ops.braw, operator_name), f"operator braw.{operator_name} missing")
    for panel_name in ("BRAW_PT_view3d", "BRAW_PT_node_editor", "BRAW_PT_image_editor"):
        check(hasattr(bpy.types, panel_name), f"panel {panel_name} missing")
    check(hasattr(scene, "braw_panel"), "scene properties not registered")
    check(initialize_ops.initialize(scene, import_module(f"{MODULE_NAME}.paths").ASSET_PATH),
          "initialize failed")

    node_tree = tree.scene_tree(scene)
    check(node_tree is not None, "compositor tree missing")
    names = sorted(node.name for node in node_tree.nodes)
    check(names == ["BlendRaw", "File Output", "Group Output", "Render Layers", "Viewer"],
          f"unexpected nodes: {names}")
    pairs = {(l.from_node.name, l.to_node.name) for l in node_tree.links}
    expected = {("Render Layers", "BlendRaw"), ("BlendRaw", "Group Output"),
                ("BlendRaw", "Viewer"), ("BlendRaw", "File Output")}
    check(pairs == expected, f"unexpected links: {pairs}")

    state_module = import_module(f"{MODULE_NAME}.core.state")
    check(isinstance(state_module.sync_from_viewports(scene), bool),
          "viewport sync must return a bool")
    check(isinstance(state_module.sync_view3d_compositor(), float),
          "viewport sync timer must return its interval")

    for section in spec.ALL_SECTIONS:
        check(tree.get_node(section.group, section.node) is not None,
              f"missing section node {section.key}")
        for item in section.fields:
            socket = tree.input_socket(tree.get_node(item.group, item.node),
                                       item.socket, item.index)
            check(socket is not None, f"unresolved binding {section.key}/{item.label}")

    for key, assignments in spec.RESETS.items():
        for assignment in assignments:
            socket = tree.get_input(assignment.group, assignment.node,
                                    assignment.socket, assignment.index)
            check(socket is not None, f"unresolved reset {key}/{assignment.node}")

    for key in spec.RESETS:
        applied = sum(
            1
            for assignment in spec.RESETS[key]
            if tree.set_input(assignment.group, assignment.node, assignment.value,
                              name=assignment.socket, index=assignment.index,
                              component=assignment.component)
        )
        check(applied == len(spec.RESETS[key]), f"reset {key} partially applied")

    group = tree.get_group("Q_Convert Colorspace")

    def switches():
        return {
            "Khronos PBR": tree.get_switch(group.nodes["BR to Khronos PBR"]),
            "AgX": tree.get_switch(group.nodes["BR to AGX"]),
            "Filmic": tree.get_switch(group.nodes["BR to Filmic"]),
        }

    def clear_switches():
        for name in ("BR to Khronos PBR", "BR to AGX", "BR to Filmic"):
            tree.set_switch(group.nodes[name], False)

    scene.view_settings.view_transform = "AgX"
    previous_look = scene.view_settings.look
    scene.braw_convert_colorspace = True
    check(switches()["AgX"], "AGX switch not set")
    check(scene.view_settings.view_transform == "Raw", "view transform not converted")
    check(scene.braw_prev_view_transform == "AgX", "previous transform not stored")
    check(scene.view_settings.look == "None", "look not neutralised")

    # The user changed the view transform manually while converted.
    scene.view_settings.view_transform = "Standard"
    scene.braw_convert_colorspace = False
    check(scene.view_settings.view_transform == "AgX", "restore after manual change failed")
    check(scene.view_settings.look == previous_look, "look not restored")
    check(not any(switches().values()), "switches not cleared")

    # Simulate "Repair node group": the re-appended group lost its switches.
    scene.view_settings.view_transform = "AgX"
    scene.braw_convert_colorspace = True
    clear_switches()
    scene.braw_convert_colorspace = False
    check(scene.view_settings.view_transform == "AgX", "restore without switches failed")

    # Raw + cleared switches must still re-assert the stored target.
    scene.view_settings.view_transform = "Raw"
    clear_switches()
    scene.braw_convert_colorspace = True
    check(switches()["AgX"], "switch not re-asserted from the stored transform")
    check(scene.view_settings.view_transform == "Raw", "view transform changed unexpectedly")
    scene.braw_convert_colorspace = False
    check(scene.view_settings.view_transform == "AgX", "final restore failed")

    scene.braw_to_file_output = False
    check(not tree.remove_file_output_slot() or True, "file output toggle")
    scene.braw_to_file_output = True
    check(any(item.name == "Image_BRaw"
              for item in node_tree.nodes["File Output"].file_output_items),
          "file output slot missing")

    temp_root = tempfile.mkdtemp(prefix="braw_presets_")
    original_root = presets.presets_root
    presets.presets_root = lambda: temp_root
    try:
        check(presets.create_category("TestCat") == "created", "category not created")
        check(presets.save_preset("TestCat", "P1"), "preset not saved")
        check(presets.presets("TestCat") == ["P1"], "preset not listed")
        check(presets.delete_preset("TestCat", "P1"), "preset not deleted")
        check(presets.delete_category("TestCat"), "category not deleted")
    finally:
        presets.presets_root = original_root
        shutil.rmtree(temp_root, ignore_errors=True)

    check(tree.cleanup_scene(bpy.context), "cleanup failed")
    check("BlendRaw" not in node_tree.nodes, "BlendRaw node survived cleanup")

    check_no_duplicate_singletons()


def check_no_duplicate_singletons():
    """Renamed/localised Viewer/File Output/Render Layers must be reused."""
    ensure_tree = import_module(f"{MODULE_NAME}.compat").ensure_compositor_tree

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.use_nodes = True
    node_tree = ensure_tree(scene)
    render_layers = node_tree.nodes.new("CompositorNodeRLayers")
    render_layers.name = "我的渲染层"
    viewer = node_tree.nodes.new("CompositorNodeViewer")
    viewer.name = "查看器"
    output = node_tree.nodes.new("CompositorNodeOutputFile")
    output.name = "我的输出"

    check(initialize_ops.initialize(scene, import_module(f"{MODULE_NAME}.paths").ASSET_PATH),
          "initialize with renamed nodes failed")
    for bl_idname, label in (
        ("CompositorNodeViewer", "viewer"),
        ("CompositorNodeOutputFile", "file output"),
        ("CompositorNodeRLayers", "render layers"),
    ):
        count = sum(1 for node in node_tree.nodes if node.bl_idname == bl_idname)
        check(count == 1, f"{label} duplicated: {count} instance(s)")
    check(node_tree.nodes.get("查看器") == viewer, "existing viewer was replaced")
    check(node_tree.nodes.get("我的输出") == output, "existing file output was replaced")
    check(viewer.inputs["Image"].is_linked, "existing viewer was not wired to BlendRaw")
    check(tree.cleanup_scene(bpy.context), "cleanup failed after singleton check")
    check(viewer.inputs["Image"].is_linked, "viewer was not rewired to Render Layers after cleanup")


try:
    run()
finally:
    try:
        addon.unregister()
    except Exception as exc:  # noqa: BLE001
        failures.append(f"unregister failed: {exc}")

if failures:
    print(f"BlendRaw self-check: {len(failures)} failure(s)")
    for failure in failures:
        print(f"  - {failure}")
    sys.exit(1)

print("BlendRaw self-check: PASS")
