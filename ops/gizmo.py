"""Background-image (backdrop) zoom gizmos for the compositor node editor."""

import bpy

_ZOOM_IN_FACTOR = 1.2
_ZOOM_OUT_FACTOR = 0.8333330154418945


class BRawBackdropZoomIn(bpy.types.Operator):
    bl_idname = "braw.backdrop_zoom_in"
    bl_label = "Backdrop Zoom In"
    bl_description = "Backdrop Zoom In"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        bpy.ops.node.backimage_zoom("INVOKE_DEFAULT", factor=_ZOOM_IN_FACTOR)
        return {"FINISHED"}

    def invoke(self, context, event):
        return self.execute(context)


class BRawBackdropZoomOut(bpy.types.Operator):
    bl_idname = "braw.backdrop_zoom_out"
    bl_label = "Backdrop Zoom Out"
    bl_description = "Backdrop Zoom Out"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        bpy.ops.node.backimage_zoom("INVOKE_DEFAULT", factor=_ZOOM_OUT_FACTOR)
        return {"FINISHED"}

    def invoke(self, context, event):
        return self.execute(context)


class BRawBackdropFit(bpy.types.Operator):
    bl_idname = "braw.backdrop_fit"
    bl_label = "Fit Backdrop to Available Space"
    bl_description = "Fit Backdrop to Available Space"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        bpy.ops.node.backimage_fit("INVOKE_DEFAULT")
        return {"FINISHED"}

    def invoke(self, context, event):
        return self.execute(context)


class BRawBackdropGizmos(bpy.types.GizmoGroup):
    bl_idname = "BRAW_GG_backdrop_zoom"
    bl_label = "Backdrop Zoom Gizmo Group"
    bl_space_type = "NODE_EDITOR"
    bl_region_type = "WINDOW"
    bl_options = {"PERSISTENT", "SCALE", "SHOW_MODAL_ALL"}

    _BUTTONS = (
        ("backdrop_zoom_in", "ADD", "braw.backdrop_zoom_in"),
        ("backdrop_zoom_out", "REMOVE", "braw.backdrop_zoom_out"),
        ("backdrop_zoom_fit", "FULLSCREEN_ENTER", "braw.backdrop_fit"),
    )

    @classmethod
    def poll(cls, context):
        return cls._in_compositor(context)

    @staticmethod
    def _in_compositor(context) -> bool:
        area = getattr(context, "area", None)
        return bool(area) and area.ui_type == "CompositorNodeTree"

    def setup(self, context):
        for name, icon, operator in self._BUTTONS:
            gizmo = self.gizmos.new("GIZMO_GT_button_2d")
            gizmo.bl_idname = name
            gizmo.draw_options = {"BACKDROP", "OUTLINE"}
            gizmo.icon = icon
            gizmo.alpha = 1.0
            gizmo.color = (0.094, 0.094, 0.094)
            gizmo.color_highlight = (0.22, 0.22, 0.22)
            gizmo.alpha_highlight = 1.0
            gizmo.scale_basis = 14.0
            gizmo.use_tooltip = True
            gizmo.show_drag = True
            gizmo.use_draw_value = True
            gizmo.target_set_operator(operator)

    def draw_prepare(self, context):
        xpos, ypos = 100.0, 100.0
        for gizmo in self.gizmos:
            gizmo.matrix_basis[0][3] = xpos
            gizmo.matrix_basis[1][3] = ypos
            xpos += 68.0


CLASSES = (
    BRawBackdropZoomIn,
    BRawBackdropZoomOut,
    BRawBackdropFit,
    BRawBackdropGizmos,
)
