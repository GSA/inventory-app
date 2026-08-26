"""Filesystem locations of the JSON Schemas this extension validates against.

Defining the paths in one module keeps the on-disk layout in a single place.
Import from here rather than rebuilding paths from `__file__`.

DCAT-US 3.0 lives in the GSA/dcat-us git submodule at `_external/dcat-us`, not
in this repo. Do not edit anything under there -- open a PR against GSA/dcat-us
instead. See "DCAT-US 3.0 schemas" in README.md.

DCAT-US 1.1 has no GSA/dcat-us equivalent and stays vendored next to this
module, so its path stays package-relative.

REPO_ROOT reaches outside the installed package. That is safe here only
because this extension is always an editable install (`start.sh` and `.profile`
both run `pip3 install -e .`), so the package directory is always the working
tree: `/app` under Docker and docker compose, `/home/vcap/app` on cloud.gov.
"""
from pathlib import Path

DCAT_DIR = Path(__file__).resolve().parent

# dcat -> datagov_inventory -> ckanext -> repository root
REPO_ROOT = DCAT_DIR.parents[2]
EXTERNAL_DIR = REPO_ROOT / "_external"
DCAT_US_DIR = EXTERNAL_DIR / "dcat-us"

V1_1_DEFINITIONS_DIR = DCAT_DIR / "v1.1_definitions"
V3_0_DEFINITIONS_DIR = DCAT_US_DIR / "jsonschema" / "definitions"
