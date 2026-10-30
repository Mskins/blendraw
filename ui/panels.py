"""Panels for the 3D View, the compositor node editor and the image editor."""

import bpy

from ..compat import area_ui_type
from ..core import spec, tree
from ..paths import LOGO_PATH
from . import icons

MUTE_NODE = ("BlendRaw", "BR_Mute")


# --- Shared drawing helpers ------------------------------------------------

def draw_mute_toggle(layout):
    node = tree.get_node(*MUTE_NODE)
    socket = tree.switch_socket(node)
    if socket is None:
        return
    layout.prop(
        socket,
        "default_value",
        text="",
        icon_value=icons.icon("QUIT"),
        emboss=True,
        toggle=True,
    )


def draw_header_preset(layout, context):
    layout.operator(
        "braw.cleanup",
        text="",
        icon_value=icons.icon("TRASH"),
    )
    row = layout.row(align=False)
    row.scale_x = 0.6
    row.prop(
        context.scene.render,
        "compositor_device",
        text=context.scene.render.compositor_device,
        emboss=True,
        expand=True,
    )
    layout.prop(
        context.scene,
        "braw_show_presets",
        text="",
        icon_value=icons.icon("PRESET"),
    )


def draw_presets(layout, context):
    scene = context.scene
    box = layout.box()
    box.label(text="My Presets", icon_value=icons.icon("MENU_PANEL"))
    column = box.column(align=True)
    row = column.row(align=True)
    row.prop(scene, "braw_presets_category", text="")
    row.operator("braw.preset_category_add", text="", icon_value=icons.icon("ADD"))
    row.operator("braw.preset_category_delete", text="", icon_value=icons.icon("REMOVE"))
    column.template_list(
        "BRAW_UL_presets",
        "",
        scene,
        "braw_presets",
        scene,
        "braw_presets_index",
        rows=4,
    )
    row = column.row(align=True)
    row.scale_x = 3.0
    row.operator(
        "braw.preset_load",
        text="Load Preset",
        icon_value=icons.icon("IMPORT"),
    )
    row.operator("braw.preset_add", text="", icon_value=icons.icon("ADD"))
    row.operator("braw.preset_delete", text="", icon_value=icons.icon("REMOVE"))


def draw_colorspace(layout, context):
    scene = context.scene
    box = layout.box()
    converted = scene.braw_convert_colorspace
    if converted:
        group = tree.get_group("Q_Convert Colorspace")
        nodes = group.nodes if group is not None else {}
        if tree.get_switch(nodes.get("BR to Filmic")):
            text = "Restore To Filmic"
        elif tree.get_switch(nodes.get("BR to AGX")):
            text = "Restore To AgX"
        else:
            text = "Restore To Khronos PBR"
    else:
        text = "Convert To Raw"

    box.prop(
        scene,
        "braw_convert_colorspace",
        text=text,
        icon_value=icons.icon("RADIOBUT_ON" if converted else "RADIOBUT_OFF"),
        emboss=False,
    )


def draw_field(layout, field):
    node = tree.get_node(field.group, field.node)
    socket = tree.input_socket(node, field.socket, field.index)
    if socket is None:
        return
    if field.component is None:
        layout.prop(socket, "default_value", text=field.label)
    else:
        layout.prop(socket, "default_value", text=field.label, index=field.component)


def draw_color_field(layout, field):
    node = tree.get_node(field.group, field.node)
    socket = tree.input_socket(node, field.socket, field.index)
    if socket is None:
        return
    column = layout.column(align=True)
    try:
        column.template_color_picker(socket, "default_value", value_slider=True)
    except (TypeError, RuntimeError, AttributeError):
        pass
    column.prop(socket, "default_value", text=field.label)


def draw_section(layout, section, context):
    box = layout.box()
    node = tree.get_node(section.group, section.node)
    if node is None:
        box.label(text=f"{section.title}: node missing", icon="ERROR")
        return

    muted = bool(getattr(node, "mute", False))
    row = box.row(align=True)
    row.prop(
        node,
        "mute",
        text=section.title,
        emboss=False,
        icon_value=icons.mute_icon(muted),
    )
    if not muted and section.has_reset and section.key in spec.RESETS:
        operator = row.operator(
            "braw.reset_section", text="", icon_value=icons.icon("LOOP_BACK")
        )
        operator.section = section.key
    else:
        row.label(text="", icon_value=icons.icon("COLLAPSEMENU"))

    if muted:
        return

    scene = context.scene
    if section.kind == "curve":
        try:
            box.template_curve_mapping(node, section.curve_prop, type=section.curve_type)
        except (TypeError, RuntimeError, AttributeError):
            box.label(text=f"{section.title}: curve unavailable", icon="ERROR")
        for field in section.fields:
            draw_field(box, field)
        return

    if section.kind == "color_balance":
        for field in section.fields:
            if field.kind == "color":
                draw_color_field(box, field)
            else:
                draw_field(box, field)
        return

    if section.kind == "selective":
        for field in section.fields:
            if field.tag is None:
                draw_field(box, field)
        tag_row = box.row(align=True)
        tag_row.scale_y = 1.5
        tag_row.prop(
            scene,
            "braw_selective_color_tag",
            text=scene.braw_selective_color_tag,
            expand=True,
        )
        current = scene.braw_selective_color_tag
        for field in section.fields:
            if field.tag == current:
                draw_field(box, field)
        return

    if section.kind == "grey_removal" and section.fields:
        draw_field(box, section.fields[0])
        box.prop(
            scene,
            "braw_grey_removal_space",
            text=scene.braw_grey_removal_space,
            expand=True,
            toggle=True,
        )
        return

    for field in section.fields:
        draw_field(box, field)


def draw_effects(layout, context):
    scene = context.scene
    box = layout.box()
    row = box.row(align=True)
    row.prop(
        scene,
        "braw_panel",
        text=scene.braw_panel,
        expand=True,
    )
    sections = (
        spec.EFFECT_SECTIONS
        if scene.braw_panel == "Glare Effects"
        else spec.PALETTE_SECTIONS
    )
    for section in sections:
        draw_section(box, section, context)


def draw_scopes(layout, panel, context):
    scene = context.scene
    column = layout.column(align=False)
    row = column.row(align=True)
    row.prop(scene, "braw_show_histogram", text="Histogram", toggle=True)
    row.prop(scene, "braw_show_waveform", text="Waveform", toggle=True)
    row.prop(scene, "braw_show_vectorscope", text="Vectorscope", toggle=True)

    for prop_name, panel_name in (
        ("braw_show_histogram", "IMAGE_PT_view_histogram"),
        ("braw_show_waveform", "IMAGE_PT_view_waveform"),
        ("braw_show_vectorscope", "IMAGE_PT_view_vectorscope"),
    ):
        if not getattr(scene, prop_name):
            continue
        panel_type = getattr(bpy.types, panel_name, None)
        if panel_type is None:
            column.label(text="Can't display this panel!", icon="ERROR")
            continue
        poll = getattr(panel_type, "poll", None)
        if poll is not None:
            try:
                visible = bool(poll(context))
            except Exception:  # noqa: BLE001 - a foreign panel's poll may need context
                visible = False
            if not visible:
                column.label(text="Can't display this panel here!", icon="ERROR")
                continue
        try:
            panel_type.draw(panel, context)
        except (RuntimeError, TypeError):
            column.label(text="Can't display this panel here!", icon="ERROR")


class BRawPanelBase:
    bl_label = "BlendRaw"
    bl_region_type = "UI"
    bl_category = "BRaw"
    bl_order = 0
    bl_ui_units_x = 0

    show_view3d = False
    show_file_output = True
    show_scopes = False

    def draw_header(self, context):
        icon_id = icons.image_icon(LOGO_PATH)
        if icon_id:
            self.layout.template_icon(icon_value=icon_id, scale=1.0)

    def draw_header_preset(self, context):
        draw_header_preset(self.layout, context)

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        node_tree = tree.scene_tree(scene)
        group_node = node_tree.nodes.get("BlendRaw") if node_tree is not None else None

        if scene.braw_show_presets:
            draw_presets(layout, context)

        row = layout.row(align=True)
        row.scale_x = 2.0
        row.scale_y = 1.5
        if group_node is not None:
            draw_mute_toggle(row)
        row.operator(
            "braw.initialize",
            text="Repair node group" if group_node is not None else "Initialize",
            icon_value=icons.icon("NODE_COMPOSITING"),
        )
        if self.show_file_output:
            file_row = row.row(align=True)
            file_row.enabled = node_tree is not None and "File Output" in node_tree.nodes
            if group_node is not None:
                file_row.prop(
                    scene, "braw_to_file_output", text="", icon_value=icons.icon("OUTPUT")
                )

        if self.show_view3d and group_node is not None:
            layout.prop(
                scene,
                "braw_view3d_compositor",
                text=scene.braw_view3d_compositor,
                expand=True,
            )

        if group_node is None:
            return

        draw_colorspace(layout, context)
        if self.show_scopes:
            draw_scopes(layout, self, context)
        draw_effects(layout, context)


class BRawView3DPanel(BRawPanelBase, bpy.types.Panel):
    bl_idname = "BRAW_PT_view3d"
    bl_space_type = "VIEW_3D"
    bl_context = ""
    show_view3d = True
    show_file_output = False


class BRawNodeEditorPanel(BRawPanelBase, bpy.types.Panel):
    bl_idname = "BRAW_PT_node_editor"
    bl_space_type = "NODE_EDITOR"
    bl_context = ""

    @classmethod
    def poll(cls, context):
        return area_ui_type() == "CompositorNodeTree"


class BRawImageEditorPanel(BRawPanelBase, bpy.types.Panel):
    bl_idname = "BRAW_PT_image_editor"
    bl_space_type = "IMAGE_EDITOR"
    bl_context = ""
    show_file_output = False
    show_scopes = True


PANEL_CLASSES = (BRawView3DPanel, BRawNodeEditorPanel, BRawImageEditorPanel)
