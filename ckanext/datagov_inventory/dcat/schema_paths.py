"""Filesystem locations of the JSON Schemas this extension validates against.

Defining the paths in one module keeps the on-disk layout in a single place.
Import from here rather than rebuilding paths from `__file__`.
"""
from pathlib import Path

DCAT_DIR = Path(__file__).resolve().parent

V1_1_DEFINITIONS_DIR = DCAT_DIR / "v1.1_definitions"
V3_0_DEFINITIONS_DIR = DCAT_DIR / "definitions"
