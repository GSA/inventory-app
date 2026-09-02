"""Filesystem locations of the JSON Schemas this extension validates against.

Import paths from here rather than rebuilding them from `__file__`.

DCAT-US 3.0 comes from the GSA/dcat-us submodule at `_external/dcat-us`; don't
edit it there, PR upstream instead (see README.md). DCAT-US 1.1 has no upstream
equivalent, so it stays vendored beside this module with a package-relative
path.

REPO_ROOT reaches outside the installed package, safe only because this
extension is always an editable install (`start.sh` and `.profile` both run
`pip3 install -e .`): `/app` under Docker, `/home/vcap/app` on cloud.gov.
"""
from pathlib import Path

DCAT_DIR = Path(__file__).resolve().parent

# dcat -> datagov_inventory -> ckanext -> repository root
REPO_ROOT = DCAT_DIR.parents[2]
EXTERNAL_DIR = REPO_ROOT / "_external"
DCAT_US_DIR = EXTERNAL_DIR / "dcat-us"

V1_1_DEFINITIONS_DIR = DCAT_DIR / "v1.1_definitions"
V3_0_DEFINITIONS_DIR = DCAT_US_DIR / "jsonschema" / "definitions"
