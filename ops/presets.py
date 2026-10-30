"""Preset operators: categories, save, load, delete."""

import os

import bpy
from bpy.props import StringProperty

from .. import presets
from ..compat import tag_redraw
from ..core import state, tree
from .initialize import initialize


def _popup(title, message, icon="INFO"):
    def draw(menu, context):
        menu.layout.label(text=message)

    bpy.context.window_manager.popup_menu(draw, title=title, icon=icon)


def _after_preset_change(context, select=None):
    scene = context.scene
    state.refresh_categories(scene)
    if select and select in presets.categories():
        scene.braw_presets_category = select
    state.refresh_preset_collection(scene)
    tag_redraw()


class BRawCreateCategory(bpy.types.Operator):
    bl_idname = "braw.preset_category_add"
    bl_label = "Create New Category"
    bl_description = "Create a new preset category"
    bl_options = {"REGISTER", "UNDO"}

    category_name: StringProperty(name="Name", default="My Preset")

    def execute(self, context):
        status = presets.create_category(self.category_name)
        if status == "exists":
            _popup("Info", "Already exists!", icon="ERROR")
            return {"CANCELLED"}
        if status == "invalid":
            self.report({"ERROR"}, "BlendRaw: invalid category name")
            return {"CANCELLED"}
        _after_preset_change(context, select=self.category_name)
        return {"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=200)

    def draw(self, context):
        self.layout.prop(self, "category_name", text="Category")


class BRawDeleteCategory(bpy.types.Operator):
    bl_idname = "braw.preset_category_delete"
    bl_label = "Delete Category"
    bl_description = "Delete current category"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return bool(presets.categories())

    def execute(self, context):
        scene = context.scene
        if not scene.braw_presets_category:
            return {"CANCELLED"}
        scene.braw_presets.clear()
        presets.delete_category(scene.braw_presets_category)
        _after_preset_change(context)
        return {"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)


class BRawAddPreset(bpy.types.Operator):
    bl_idname = "braw.preset_add"
    bl_label = "Add Preset"
    bl_description = "Save current BlendRaw as a preset"
    bl_options = {"REGISTER", "UNDO"}

    preset_name: StringProperty(name="Name", default="My BlendRaw Preset01")

    @classmethod
    def poll(cls, context):
        return tree.get_group("BlendRaw") is not None

    def execute(self, context):
        scene = context.scene
        if not presets.save_preset(scene.braw_presets_category, self.preset_name):
            self.report({"ERROR"}, "BlendRaw: could not save the preset")
            return {"CANCELLED"}
        _after_preset_change(context)
        self.report({"INFO"}, "Save Successful")
        return {"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=200)

    def draw(self, context):
        self.layout.prop(self, "preset_name", text="")


class BRawDeletePreset(bpy.types.Operator):
    bl_idname = "braw.preset_delete"
    bl_label = "Delete Preset"
    bl_description = "Delete current BlendRaw preset"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return bool(context.scene.braw_presets)

    def execute(self, context):
        scene = context.scene
        index = scene.braw_presets_index
        if not (0 <= index < len(scene.braw_presets)):
            return {"CANCELLED"}
        name = scene.braw_presets[index].lable
        if not presets.delete_preset(scene.braw_presets_category, name):
            self.report({"ERROR"}, "BlendRaw: could not delete the preset")
            return {"CANCELLED"}
        scene.braw_presets_index = 0
        _after_preset_change(context)
        self.report({"INFO"}, "Delete Successful")
        return {"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)


class BRawLoadPreset(bpy.types.Operator):
    bl_idname = "braw.preset_load"
    bl_label = "Load Preset"
    bl_description = "Load current BlendRaw preset"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return bool(context.scene.braw_presets)

    def execute(self, context):
        scene = context.scene
        index = scene.braw_presets_index
        if not (0 <= index < len(scene.braw_presets)):
            return {"CANCELLED"}
        name = scene.braw_presets[index].lable
        path = presets.preset_path(scene.braw_presets_category, name)
        if not os.path.exists(path):
            self.report({"ERROR"}, f"BlendRaw: preset not found: {path}")
            return {"CANCELLED"}

        tree.cleanup_scene(context)
        if not initialize(scene, path):
            self.report({"ERROR"}, "BlendRaw: could not load the preset")
            return {"CANCELLED"}

        group = tree.get_group("Q_Convert Colorspace")
        if group is not None:
            converted = any(
                tree.get_switch(group.nodes.get(name))
                for name in ("BR to Khronos PBR", "BR to AGX", "BR to Filmic")
            )
            if converted:
                try:
                    scene.view_settings.view_transform = "Raw"
                except TypeError:
                    pass
        return {"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)


class BRAW_UL_presets(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        layout.prop(item, "lable", text="", icon_value=0, emboss=False)

    def filter_items(self, context, data, propname):
        items = getattr(data, propname)
        filter_name = self.filter_name.lower()
        flags = [
            self.bitflag_filter_item
            if filter_name and filter_name in item.name.lower()
            else (self.bitflag_filter_item if not filter_name else 0)
            for item in items
        ]
        return flags, []


CLASSES = (
    BRawCreateCategory,
    BRawDeleteCategory,
    BRawAddPreset,
    BRawDeletePreset,
    BRawLoadPreset,
    BRAW_UL_presets,
)
