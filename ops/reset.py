"""One parameterised reset operator for every resetable section."""

import bpy
from bpy.props import EnumProperty

from ..core import spec, tree

_RESETTABLE = [section for section in spec.ALL_SECTIONS if section.key in spec.RESETS]


def _section_items(self, context):
    return [(section.key, section.title, "", 0, i) for i, section in enumerate(_RESETTABLE)]


def apply_reset(section_key: str) -> int:
    """Write the section's defaults; returns how many sockets were updated."""
    applied = 0
    for assignment in spec.RESETS.get(section_key, ()):
        if tree.set_input(
            assignment.group,
            assignment.node,
            assignment.value,
            name=assignment.socket,
            index=assignment.index,
            component=assignment.component,
        ):
            applied += 1
    return applied


class BRawResetSection(bpy.types.Operator):
    bl_idname = "braw.reset_section"
    bl_label = "Reset Section"
    bl_options = {"REGISTER", "UNDO"}

    section: EnumProperty(items=_section_items, name="Section")

    def execute(self, context):
        if not apply_reset(self.section):
            self.report({"WARNING"}, "BlendRaw: node group is not initialised")
            return {"CANCELLED"}
        return {"FINISHED"}


CLASSES = (BRawResetSection,)
