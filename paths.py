"""Filesystem locations used by the addon."""

import os

ADDON_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(ADDON_DIR, "assets")
ASSET_PATH = os.path.join(ASSETS_DIR, "BlendRaw_Node_E.blend")
LOGO_PATH = os.path.join(ASSETS_DIR, "logo.svg")
PRESETS_DIRNAME = "BlendRaw Presets"
