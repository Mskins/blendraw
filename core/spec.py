"""Declarative description of the BlendRaw UI.

Every slider, curve widget and mute toggle the addon exposes is described here
as data.  The panel code only interprets these tables, so adding/renaming a
control never means touching UI code again.

Bindings are declared with *both* the socket name and the historical index.
Blender 5.0 moved most node parameters from RNA properties to sockets; the
name is authoritative, the index is the fallback that keeps saved node groups
from earlier builds working.
"""

from dataclasses import dataclass
from typing import Optional, Tuple

BLENDRAW = "BlendRaw"
EFFECTS = "Q_Effects"


@dataclass(frozen=True)
class Field:
    """One bound widget."""

    label: str
    node: str
    socket: str
    index: int
    group: str = BLENDRAW
    kind: str = "float"  # float | int | color | vector
    component: Optional[int] = None
    tag: Optional[str] = None


@dataclass(frozen=True)
class Reset:
    group: str
    node: str
    socket: Optional[str]
    index: Optional[int]
    value: object
    component: Optional[int] = None


@dataclass(frozen=True)
class Section:
    key: str
    title: str
    node: str
    group: str = BLENDRAW
    kind: str = "normal"  # normal | grey_removal | selective | color_balance | curve
    curve_type: str = ""
    curve_prop: str = "mapping"
    fields: Tuple[Field, ...] = ()
    has_reset: bool = True


# --- Selective colour tags -------------------------------------------------

# identifier, description, icon
SELECTIVE_TAGS = (
    ("R", "Red", "COLORSET_01_VEC"),
    ("G", "Green", "COLORSET_03_VEC"),
    ("B", "Blue", "COLORSET_04_VEC"),
    ("C", "Cyan", "COLORSET_07_VEC"),
    ("M", "Magenta", "COLORSET_05_VEC"),
    ("Y", "Yellow", "COLORSET_09_VEC"),
)


def _selective_fields() -> Tuple[Field, ...]:
    out = [Field("Blend", "Q_Selective Color", "Fac", 26)]
    for i, (tag, _description, _icon) in enumerate(SELECTIVE_TAGS):
        base = 2 + 4 * i
        out.append(Field("Hue", "Q_Selective Color", "Hue", base, tag=tag))
        out.append(Field("Saturation", "Q_Selective Color", "Saturation", base + 1, tag=tag))
        out.append(Field("Bright", "Q_Selective Color", "Bright", base + 2, tag=tag))
    return tuple(out)


# --- Colour Adjust tab -----------------------------------------------------

PALETTE_SECTIONS = (
    Section(
        "white_balance",
        "White Balance",
        "Q_White Balance",
        fields=(
            Field("Temperature", "Q_White Balance", "Temperature", 1),
            Field("Tint", "Q_White Balance", "Tint", 2),
        ),
    ),
    Section(
        "grey_removal",
        "Grey Removal",
        "Q_Grey Removal",
        kind="grey_removal",
        fields=(Field("Grey Removal", "Q_Grey Removal", "Grey Removal", 1),),
    ),
    Section(
        "basic",
        "Basic",
        "Q_Basic_Options",
        fields=(
            Field("Natural Exposure", "Q_Basic_Options", "Natural Exposure", 1),
            Field("Exposure", "Q_Basic_Options", "Exposure", 2),
            Field("Smart Contrast", "Q_Basic_Options", "Smart Contrast", 3),
            Field("Contrast", "Q_Basic_Options", "Contrast", 4),
            Field("Highlight", "Q_Basic_Options", "Highlight", 5),
            Field("Shadow", "Q_Basic_Options", "Shadow", 6),
            Field("White", "Q_Basic_Options", "White", 7),
            Field("Black", "Q_Basic_Options", "Black", 8),
        ),
    ),
    Section(
        "sharpness",
        "Sharpness",
        "Q_Sharpness",
        fields=(
            Field("Texture", "Q_Sharpness", "Texture", 1),
            Field("Sharpness", "Q_Sharpness", "Sharpness", 2),
            Field("Natural Sharpen", "Q_Sharpness", "Natural Sharpen", 3),
        ),
    ),
    Section(
        "hsv",
        "Hue/Saturation/Value",
        "Q_Hue/Saturation/Value",
        fields=(
            Field("Hue", "Q_Hue/Saturation/Value", "Hue", 1),
            Field("Smart Saturation", "Q_Hue/Saturation/Value", "Smart Saturation", 2),
            Field("Natural Saturation", "Q_Hue/Saturation/Value", "Natural Saturation", 3),
            Field("Contrast Saturation", "Q_Hue/Saturation/Value", "Contrast Saturation", 4),
            Field("Saturation", "Q_Hue/Saturation/Value", "Saturation", 5),
            Field("Value", "Q_Hue/Saturation/Value", "Value", 6),
            Field("Blend", "Q_Hue/Saturation/Value", "Blend", 7),
        ),
    ),
    Section(
        "selective_color",
        "Selective Color",
        "Q_Selective Color",
        kind="selective",
        fields=_selective_fields(),
    ),
    Section(
        "hue_correct",
        "Hue Correct",
        "Q_Hue Correct",
        kind="curve",
        curve_type="HUE",
        fields=(Field("Blend", "Q_Hue Correct", "Factor", 1),),
        has_reset=False,
    ),
    Section(
        "color_balance",
        "Color Balance",
        "Q_Color Balance",
        kind="color_balance",
        fields=(
            Field("Lift", "Q_Color Balance", "Lift", 4, kind="color"),
            Field("Gamma", "Q_Color Balance", "Gamma", 6, kind="color"),
            Field("Gain", "Q_Color Balance", "Gain", 8, kind="color"),
            Field("Blend", "Q_Color Balance", "Factor", 1),
        ),
    ),
    Section(
        "rgb_curves",
        "RGB Curves",
        "Q_RGB Curves",
        kind="curve",
        curve_type="COLOR",
        fields=(
            Field("Black Level", "Q_RGB Curves", "Black Level", 2, kind="color"),
            Field("White Level", "Q_RGB Curves", "White Level", 3, kind="color"),
            Field("Blend", "Q_RGB Curves", "Factor", 1),
        ),
        has_reset=False,
    ),
    Section(
        "vignetting",
        "Vignetting",
        "Q_Vignetting",
        fields=(
            Field("Exposure", "Q_Vignetting", "Exposure", 1),
            Field("Blur", "Q_Vignetting", "Size", 2),
            Field("Width", "Ellipse Mask", "Size", 4, group="Q_Vignetting", kind="vector", component=0),
            Field("Height", "Ellipse Mask", "Size", 4, group="Q_Vignetting", kind="vector", component=1),
        ),
        has_reset=False,
    ),
)


# --- Glare Effects tab -----------------------------------------------------

EFFECT_SECTIONS = (
    Section(
        "fx_overall",
        "Overall",
        EFFECTS,
        fields=(
            Field("Threshold", EFFECTS, "Threshold", 1),
            Field("Blur", EFFECTS, "Blur Size", 2),
            Field("Strength", EFFECTS, "Overall Strength", 3),
        ),
    ),
    Section(
        "fx_bloom",
        "Bloom",
        "Q_Bloom",
        group=EFFECTS,
        fields=(
            Field("Strength", "Q_Bloom", "Bloom Strength", 2, group=EFFECTS),
            Field("Threshold", "Bloom", "Threshold", 3, group="Q_Bloom"),
            Field("Size", "Bloom", "Size", 10, group="Q_Bloom"),
        ),
    ),
    Section(
        "fx_asterisks",
        "Asterisks",
        "Q_Asterisks",
        group=EFFECTS,
        fields=(
            Field("Strength", "Q_Asterisks", "Asterisks Strength", 2, group=EFFECTS),
            Field("Blur", "Q_Asterisks", "Asterisks Blur", 3, group=EFFECTS),
            Field("Streaks", "Q_Asterisks", "Streaks", 11, group="Q_Asterisks", kind="int"),
            Field("Angle Offset", "Q_Asterisks", "Streaks Angle", 12, group="Q_Asterisks"),
        ),
    ),
    Section(
        "fx_streaks",
        "Streaks",
        "Q_Streaks",
        group=EFFECTS,
        fields=(
            Field("Strength", "Q_Streaks", "Streaks Strength", 2, group=EFFECTS),
            Field("Size", "Q_Streaks", "Streaks Size", 3, group=EFFECTS),
            Field("Contrast", "Q_Streaks", "Streaks Contrast", 4, group=EFFECTS),
            Field("Direction", "Q_Streaks", "Streaks Direction", 5, group=EFFECTS),
            Field("Hue", "Q_Streaks", "Streaks Hue", 6, group=EFFECTS),
            Field("Saturation", "Q_Streaks", "Streaks Saturation", 7, group=EFFECTS),
        ),
    ),
    Section(
        "fx_ghosts",
        "Ghosts",
        "Q_Ghosts",
        group=EFFECTS,
        fields=(
            Field("Strength", "Q_Ghosts", "Ghosts Strength", 2, group=EFFECTS),
            Field("Blur", "Q_Ghosts", "Ghosts Blur", 3, group=EFFECTS),
            Field("Hue", "Q_Ghosts", "Ghosts Hue", 4, group=EFFECTS),
            Field("Saturation", "Q_Ghosts", "Ghosts Saturation", 5, group=EFFECTS),
            Field("Distortion", "Q_Ghosts", "Distortion", 6, group=EFFECTS),
            Field("Dispersion", "Q_Ghosts", "Dispersion", 7, group=EFFECTS),
        ),
    ),
    Section(
        "fx_sun_beams",
        "Sun Beams",
        "Q_Sun Beams",
        group=EFFECTS,
        fields=(
            Field("Strength", "Q_Sun Beams", "Sun Beams", 2, group=EFFECTS),
            Field("Blur", "Q_Sun Beams", "Blur", 3, group=EFFECTS),
        ),
    ),
)

ALL_SECTIONS = PALETTE_SECTIONS + EFFECT_SECTIONS
SECTION_BY_KEY = {section.key: section for section in ALL_SECTIONS}


# --- Reset values ----------------------------------------------------------
# Faithful to the original addon.  Where Blender 5.0 replaced a node property
# with a socket, the equivalent socket value is used instead (see MIGRATION.md).

def _selective_resets() -> Tuple[Reset, ...]:
    out = []
    for i in range(len(SELECTIVE_TAGS)):
        base = 2 + 4 * i
        out.append(Reset(BLENDRAW, "Q_Selective Color", "Hue", base, 0.5))
        out.append(Reset(BLENDRAW, "Q_Selective Color", "Saturation", base + 1, 0.0))
        out.append(Reset(BLENDRAW, "Q_Selective Color", "Bright", base + 2, 0.0))
    out.append(Reset(BLENDRAW, "Q_Selective Color", "Fac", 26, 1.0))
    return tuple(out)


_WHITE = (1.0, 1.0, 1.0, 1.0)

RESETS = {
    "white_balance": (
        Reset(BLENDRAW, "Q_White Balance", "Temperature", 1, 0.5),
        Reset(BLENDRAW, "Q_White Balance", "Tint", 2, 0.0),
    ),
    "basic": tuple(
        Reset(BLENDRAW, "Q_Basic_Options", name, index, 0.0)
        for index, name in enumerate(
            (
                "Natural Exposure",
                "Exposure",
                "Smart Contrast",
                "Contrast",
                "Highlight",
                "Shadow",
                "White",
                "Black",
            ),
            start=1,
        )
    ),
    "sharpness": (
        Reset(BLENDRAW, "Q_Sharpness", "Texture", 1, 0.0),
        Reset(BLENDRAW, "Q_Sharpness", "Sharpness", 2, 0.0),
        Reset(BLENDRAW, "Q_Sharpness", "Natural Sharpen", 3, 0.0),
    ),
    "hsv": (
        Reset(BLENDRAW, "Q_Hue/Saturation/Value", "Hue", 1, 0.5),
        Reset(BLENDRAW, "Q_Hue/Saturation/Value", "Smart Saturation", 2, 0.0),
        Reset(BLENDRAW, "Q_Hue/Saturation/Value", "Natural Saturation", 3, 0.0),
        Reset(BLENDRAW, "Q_Hue/Saturation/Value", "Contrast Saturation", 4, 0.0),
        Reset(BLENDRAW, "Q_Hue/Saturation/Value", "Saturation", 5, 0.0),
        Reset(BLENDRAW, "Q_Hue/Saturation/Value", "Value", 6, 1.0),
        Reset(BLENDRAW, "Q_Hue/Saturation/Value", "Blend", 7, 1.0),
    ),
    "selective_color": _selective_resets(),
    "color_balance": (
        Reset(BLENDRAW, "Q_Color Balance", "Lift", 4, _WHITE),
        Reset(BLENDRAW, "Q_Color Balance", "Gamma", 6, _WHITE),
        Reset(BLENDRAW, "Q_Color Balance", "Gain", 8, _WHITE),
        Reset(BLENDRAW, "Q_Color Balance", "Factor", 1, 1.0),
    ),
    "grey_removal": (Reset(BLENDRAW, "Q_Grey Removal", "Grey Removal", 1, 0.0),),
    "fx_overall": (
        Reset(BLENDRAW, EFFECTS, "Threshold", 1, 0.5),
        Reset(BLENDRAW, EFFECTS, "Blur Size", 2, 1.0),
        Reset(BLENDRAW, EFFECTS, "Overall Strength", 3, 0.5),
    ),
    "fx_bloom": (
        Reset(EFFECTS, "Q_Bloom", "Bloom Strength", 2, 0.5),
        Reset("Q_Bloom", "Bloom", "Threshold", 3, 1.0),
        Reset("Q_Bloom", "Bloom", "Size", 10, 1.0),
    ),
    "fx_asterisks": (
        Reset(EFFECTS, "Q_Asterisks", "Asterisks Strength", 2, 0.5),
        Reset(EFFECTS, "Q_Asterisks", "Asterisks Blur", 3, 0.5),
        Reset("Q_Asterisks", "Q_Asterisks", "Streaks", 11, 4),
        Reset("Q_Asterisks", "Q_Asterisks", "Streaks Angle", 12, 0.0),
    ),
    "fx_streaks": (
        Reset(EFFECTS, "Q_Streaks", "Streaks Strength", 2, 0.0),
        Reset(EFFECTS, "Q_Streaks", "Streaks Size", 3, 1.0),
        Reset(EFFECTS, "Q_Streaks", "Streaks Contrast", 4, 1.0),
        Reset(EFFECTS, "Q_Streaks", "Streaks Direction", 5, 1.0),
        Reset(EFFECTS, "Q_Streaks", "Streaks Hue", 6, 0.5),
        Reset(EFFECTS, "Q_Streaks", "Streaks Saturation", 7, 1.0),
    ),
    "fx_ghosts": (
        Reset(EFFECTS, "Q_Ghosts", "Ghosts Strength", 2, 0.0),
        Reset(EFFECTS, "Q_Ghosts", "Ghosts Blur", 3, 0.0),
        Reset(EFFECTS, "Q_Ghosts", "Ghosts Hue", 4, 0.5),
        Reset(EFFECTS, "Q_Ghosts", "Ghosts Saturation", 5, 0.5),
        Reset(EFFECTS, "Q_Ghosts", "Distortion", 6, 0.0),
        Reset(EFFECTS, "Q_Ghosts", "Dispersion", 7, 0.0),
    ),
    "fx_sun_beams": (
        Reset(EFFECTS, "Q_Sun Beams", "Sun Beams", 2, 0.0),
        Reset(EFFECTS, "Q_Sun Beams", "Blur", 3, 0.0),
    ),
}
