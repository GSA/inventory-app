"""Convert a valid DCAT-US v1.1 catalog to a valid DCAT-US v3.0 catalog."""
import copy
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import click
from curl_cffi import requests
from curl_cffi.requests.exceptions import RequestException

from . import transforms
from .schema_paths import V1_1_DEFINITIONS_DIR, V3_0_DEFINITIONS_DIR
from .validator import (
    CatalogValidationException,
    V1_1_CATALOG_SCHEMA_ID,
    V1_1_DATASET_SCHEMA_ID,
    V3_0_CATALOG_SCHEMA_ID,
    V3_0_DATASET_SCHEMA_ID,
    load_schema_registry,
    validate_catalog,
    validate_datasets,
)


class CatalogFetchException(Exception):
    pass


class CatalogConversionException(Exception):
    pass


def fetch_dcat_catalog(url: str) -> dict:
    """Fetch a DCAT-US v1.1 catalog to convert to DCAT-US v3.0."""
    try:
        response = requests.get(url, timeout=60, impersonate="safari17_0")
        response.raise_for_status()
    except RequestException as e:
        raise CatalogFetchException(
            f"Request failed: {type(e).__name__}: {e!r}"
        ) from e

    try:
        text = response.content.decode("utf-8-sig")
        text = text.lstrip("﻿")
    except UnicodeDecodeError:
        text = response.content.decode("cp1252")

    try:
        parsed = json.loads(text)
    except ValueError as e:
        raise CatalogFetchException(
            f"Response was not valid JSON: {e}"
        ) from e

    if not isinstance(parsed, dict):
        raise CatalogFetchException(
            f"Expected a JSON object at the catalog root, "
            f"got {type(parsed).__name__}"
        )

    return parsed


def convert_dcat_catalog(old_catalog: dict) -> tuple[dict, list]:
    """Convert DCAT-US v1.1 catalog to DCAT-US v3.0 catalog.

    Returns a tuple of (catalog, errors) where:
    - catalog: dict with successfully transformed datasets
    - errors: list of dicts with metadata about failed datasets
    """
    new_catalog = copy.deepcopy(old_catalog)
    errors = []

    # conformsTo on the Catalog
    new_catalog["conformsTo"] = {
        "@type": "Standard",
        "title": "DCAT-US 3.0",
        "identifier": "https://resources.data.gov/dcat-us/3.0.0",
    }

    # remove @context and describedBy from the Catalog
    new_catalog.pop("@context", None)
    new_catalog.pop("describedBy", None)

    # The catalog may have a `modified` timestamp so we normalize
    # it to a timezone-aware date-time string (v3.0 requires one).
    catalog_modified = new_catalog.get("modified")
    if isinstance(catalog_modified, str):
        try:
            parsed = datetime.fromisoformat(catalog_modified)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            new_catalog["modified"] = parsed.astimezone(
                timezone.utc
            ).strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            del new_catalog["modified"]

    datasets = new_catalog.get("dataset", [])
    click.echo(f"Transforming {len(datasets)} datasets.")
    transformed_datasets = []

    for i, dataset in enumerate(datasets):
        identifier = dataset.get("identifier", f"index {i}")
        title = dataset.get("title", "Unknown")
        try:
            dataset = transforms.transform_modified(dataset)
            dataset = transforms.transform_temporal(dataset)
            dataset = transforms.transform_spatial(dataset)
            dataset = transforms.transform_language(dataset)
            dataset = transforms.transform_access_rights(dataset)
            dataset = transforms.propagate_license(dataset)
            dataset = transforms.transform_rights(dataset)
            dataset = transforms.transform_described_by(dataset)
            dataset = transforms.transform_sub_organization_of(dataset)
            dataset = transforms.transform_conforms_to(dataset)
            dataset = transforms.transform_landing_page(dataset)
            dataset = transforms.transform_issued(dataset)
            transformed_datasets.append(dataset)
        except Exception as e:
            error_entry = {
                "identifier": identifier,
                "title": title,
                "error": str(e)
            }
            errors.append(error_entry)
            click.echo(f"Error transforming dataset {identifier}: {e}")

    new_catalog["dataset"] = transformed_datasets
    return new_catalog, errors


def export_converted_catalog(catalog: dict, output_dir: str) -> None:
    """Write the converted DCAT-US v3.0 catalog to disk as JSON."""
    click.echo("Saving converted DCAT-US 3.0 to disk.")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    output_file = output_path / "catalog.json"
    with output_file.open("w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)

    click.echo(f"Wrote {output_file}")


@click.command()
@click.option(
    "-o", "--output-dir",
    help="Output directory",
    default="converted_dcat_data"
)
@click.option(
    "-u", "--url",
    help="URL of DCAT-US v1.1 catalog to be converted",
    required=True
)
@click.option(
    "--dry-run",
    help="Validate and convert without saving to disk",
    is_flag=True,
    default=False
)
def main(output_dir, url, dry_run):
    """Convert DCAT catalog."""
    v1_1_registry = load_schema_registry(V1_1_DEFINITIONS_DIR)
    v3_0_registry = load_schema_registry(V3_0_DEFINITIONS_DIR)

    results = {
        "error": False,
        "conversion_successful": False
    }

    counts = {
        "datasets": 0,
        "valid_v1_1": 0,
        "invalid_v1_1": 0,
        "validation_errors_v1_1": 0,
        "valid_v3_0": 0,
        "invalid_v3_0": 0,
        "validation_errors_v3_0": 0,
    }

    click.echo(f"Converting DCAT-US v1.1 to DCAT-US v3.0 for {url}")
    try:
        catalog_to_convert = fetch_dcat_catalog(url)
        datasets = catalog_to_convert.get("dataset", [])

        try:
            validate_catalog(
                V1_1_CATALOG_SCHEMA_ID, v1_1_registry, catalog_to_convert
            )
            click.echo("Input catalog is valid DCAT-US v1.1.")
        except CatalogValidationException:
            click.echo(
                "Warning: input catalog failed v1.1 validation "
                "— converting anyway."
            )

        # Per-dataset v1.1 validation
        # The v1.1 catalog schema validates the catalog wrapper,
        # not individual datasets directly.
        valid_v1_1, invalid_v1_1, validation_errors_v1_1 = (
            validate_datasets(
                V1_1_DATASET_SCHEMA_ID, v1_1_registry, datasets
            )
        )
        counts["valid_v1_1"] = valid_v1_1
        counts["invalid_v1_1"] = invalid_v1_1
        counts["validation_errors_v1_1"] = validation_errors_v1_1
        counts["datasets"] = valid_v1_1 + invalid_v1_1
        click.echo(
            f"Per-dataset v1.1: {valid_v1_1} valid, "
            f"{invalid_v1_1} invalid."
        )

        converted_catalog, conversion_errors = convert_dcat_catalog(
            catalog_to_convert
        )

        if conversion_errors:
            click.echo(
                f"Conversion errors: {len(conversion_errors)} "
                "datasets failed transformation"
            )

        try:
            validate_catalog(
                V3_0_CATALOG_SCHEMA_ID, v3_0_registry, converted_catalog
            )
        except CatalogValidationException as e:
            click.echo(f"Invalid DCAT-US data: {e}", err=True)

        converted_datasets = converted_catalog.get("dataset", [])
        valid_v3_0, invalid_v3_0, validation_errors_v3_0 = (
            validate_datasets(
                V3_0_DATASET_SCHEMA_ID, v3_0_registry, converted_datasets
            )
        )
        counts["valid_v3_0"] = valid_v3_0
        counts["invalid_v3_0"] = invalid_v3_0
        counts["validation_errors_v3_0"] = validation_errors_v3_0
        click.echo(
            f"Per-dataset v3.0: {valid_v3_0} valid, "
            f"{invalid_v3_0} invalid."
        )

        if dry_run:
            click.echo("Dry run complete.")
        else:
            export_converted_catalog(converted_catalog, output_dir)

    except CatalogFetchException as e:
        results["error"] = True
        click.echo(
            f"There was an error fetching a DCAT-US v1.1 catalog "
            f"to convert: {e}",
            err=True
        )
    except CatalogConversionException as e:
        results["error"] = True
        click.echo(
            f"There was an error converting a DCAT-US v1.1 catalog "
            f"to DCAT-US v3.0: {e}",
            err=True
        )

    if not results["error"] and counts["datasets"] == counts["valid_v3_0"]:
        results["conversion_successful"] = True

    click.echo(f"RESULTS:{json.dumps(results)}")
    click.echo(f"COUNTS:{json.dumps(counts)}")

    if results["error"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
