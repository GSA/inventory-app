"""Convert a valid DCAT-US v1.1 catalog to a valid DCAT-US v3.0 catalog."""
import copy
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import click
from curl_cffi import requests
from curl_cffi.requests.exceptions import RequestException
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from . import transforms


V1_1_CATALOG_SCHEMA_ID = (
    "https://project-open-data.cio.gov/v1.1/schema/catalog.json"
)
V3_0_CATALOG_SCHEMA_ID = (
    "https://resources.data.gov/dcat-us/3.0.0/definitions/catalog"
)
SCRIPT_DIR = Path(__file__).parent
V1_1_DEFINITIONS_DIR = SCRIPT_DIR / "v1.1_definitions"
V3_0_DEFINITIONS_DIR = SCRIPT_DIR / "definitions"


class CatalogFetchException(Exception):
    pass


class CatalogValidationException(Exception):
    pass


class CatalogConversionException(Exception):
    pass


def format_path(path):
    """Format a jsonschema path as a readable string."""
    if not path:
        return "(root)"
    parts = []
    for p in path:
        if isinstance(p, int):
            # Array index - append to previous part
            if parts:
                parts[-1] = f"{parts[-1]}[{p}]"
            else:
                parts.append(f"[{p}]")
        else:
            parts.append(str(p))
    return ".".join(parts)


def format_validation_errors(errors, indent=0):
    """Format validation errors with summarization and clear nesting."""
    output = []
    prefix = "  " * indent

    # Group errors by their root path for cleaner output
    for error in sorted(errors, key=lambda e: list(e.path)):
        summary = summarize_error(error, prefix=prefix)
        if summary:
            output.append(summary)

    return "\n".join(output)


def summarize_error(error, prefix=""):
    """Summarize a single error into a human-readable string."""
    path = format_path(error.path)

    # Handle anyOf/oneOf errors by finding meaningful sub-errors
    if error.validator in ("anyOf", "oneOf") and error.context:
        meaningful = find_meaningful_errors(error.context)

        # If all sub-errors are null-type, we have a different problem
        if not meaningful:
            return (
                f"{prefix}{path}: field is not null and does not match "
                "any allowed type"
            )

        # Check if it's a simple "not null and wrong type" case
        has_null_alternative = any(
            is_null_type_error(e) for e in error.context
        )

        summaries = []
        for sub_error in meaningful:
            sub_summary = summarize_error(sub_error, prefix="")
            if sub_summary:
                summaries.append(sub_summary)

        if has_null_alternative and summaries:
            intro = f"{path}: field is not null and "
            if len(summaries) == 1:
                return f"{prefix}{intro}{summaries[0]}"
            else:
                return (
                    f"{prefix}{intro}does not match alternatives:\n"
                    + "\n".join(f"{prefix}  - {s}" for s in summaries)
                )
        elif summaries:
            if len(summaries) == 1:
                return f"{prefix}{path}: {summaries[0]}"
            else:
                return (
                    f"{prefix}{path}: does not match any alternative:\n"
                    + "\n".join(f"{prefix}    - {s}" for s in summaries)
                )

    # Handle $ref errors - find the expected class
    if "$ref" in error.schema:
        class_name = extract_schema_name(error.schema)
        if error.context:
            # Dig into what specifically failed
            meaningful = find_meaningful_errors(error.context)
            if meaningful:
                sub_summaries = [
                    summarize_error(e, prefix="") for e in meaningful
                ]
                sub_summaries = [s for s in sub_summaries if s]
                if sub_summaries:
                    if class_name:
                        return (
                            f"does not conform to {class_name}: "
                            f"{'; '.join(sub_summaries)}"
                        )
                    return "; ".join(sub_summaries)
        if class_name:
            return f"does not conform to {class_name}"

    # Handle required field errors
    if error.validator == "required":
        missing = error.validator_value
        if isinstance(missing, list):
            missing_fields = [f for f in missing if f in error.message]
            if missing_fields:
                return f"missing required field '{missing_fields[0]}'"
        # Parse from message: "'fieldname' is a required property"
        if "is a required property" in error.message:
            field = error.message.split("'")[1]
            return f"missing required field '{field}'"
        return error.message

    # Handle type errors
    if error.validator == "type":
        expected = error.validator_value
        if isinstance(expected, list):
            expected = " or ".join(expected)
        return f"{prefix}{path}: expected type '{expected}'"

    # Handle enum errors
    if error.validator == "enum":
        return f"value not in allowed values: {error.validator_value}"

    # Handle pattern errors
    if error.validator == "pattern":
        return f"does not match pattern '{error.validator_value}'"

    # Handle format errors
    if error.validator == "format":
        return f"invalid format, expected '{error.validator_value}'"

    # Default: use the message
    return error.message


def find_meaningful_errors(errors):
    """Filter errors, skipping null-type failures."""
    meaningful = []
    for error in errors:
        if is_null_type_error(error):
            continue
        meaningful.append(error)
    return meaningful if meaningful else list(errors)


def is_null_type_error(error):
    """Check if this error is just 'type is not null'."""
    return (
        error.validator == "type" and error.validator_value == "null"
    )


def extract_schema_name(schema):
    """Extract a human-readable schema/class name."""
    if isinstance(schema, dict):
        if "$ref" in schema:
            ref = schema["$ref"]
            return ref.split("/")[-1].title()
        if "title" in schema:
            return schema["title"]
    return None


def load_schema_registry(definitions_dir: Path) -> Registry:
    registry = Registry()
    for schema_file in definitions_dir.glob("*.json"):
        with schema_file.open() as f:
            resource = Resource.from_contents(json.load(f))
            registry = resource @ registry

    # Some catalogs reference non-federal_dataset.json directly;
    # register it under that URI as an alias.
    non_federal = definitions_dir / "non-federal_dataset.json"
    if non_federal.exists():
        with non_federal.open() as f:
            contents = json.load(f)
        contents_copy = {
            **contents,
            "$id": (
                "https://project-open-data.cio.gov/v1.1/schema/"
                "non-federal_dataset.json"
            )
        }
        registry = Resource.from_contents(contents_copy) @ registry

    return registry


def fetch_dcat_catalog(url: str) -> dict:
    """Fetch a DCAT-US v1.1 catalog to convert to DCAT-US v3.0."""
    # Some servers reject non-browser TLS/HTTP2 fingerprints,
    # so we impersonate a real browser using curl_cffi.
    try:
        response = requests.get(url, timeout=60, impersonate="safari17_0")
        response.raise_for_status()
    except RequestException as e:
        raise CatalogFetchException(
            f"Request failed: {type(e).__name__}: {e!r}"
        ) from e

    try:
        text = response.content.decode("utf-8-sig")
        text = text.lstrip("\ufeff")
    except UnicodeDecodeError:
        text = response.content.decode("cp1252")

    try:
        parsed = json.loads(text)
    except ValueError as e:
        raise CatalogFetchException(f"Response was not valid JSON: {e}") from e

    if not isinstance(parsed, dict):
        raise CatalogFetchException(
            f"Expected a JSON object at the catalog root, "
            f"got {type(parsed).__name__}"
        )

    return parsed


def validate_catalog(
    schema_id: str, registry: Registry, catalog: dict
) -> None:
    """Validate a DCAT-US v1.1 or v3.0 catalog."""
    validator = Draft202012Validator(
        {"$ref": schema_id},
        registry=registry,
        format_checker=Draft202012Validator.FORMAT_CHECKER,
    )
    errors = list(validator.iter_errors(catalog))
    if errors:
        version_number = "v1.1" if "v1.1" in schema_id else "v3.0"
        raise CatalogValidationException(
            f"{version_number} validation failed with "
            f"{len(errors)} error(s):\n"
            + format_validation_errors(errors, indent=2)
        )


def validate_datasets(
    schema_id: str, registry: Registry, datasets: list
) -> tuple[int, int, int]:
    """Validate each dataset individually."""
    validator = Draft202012Validator(
        {"$ref": schema_id},
        registry=registry,
        format_checker=Draft202012Validator.FORMAT_CHECKER,
    )
    valid = 0
    invalid = 0
    error_count = 0
    for dataset in datasets:
        errors = list(validator.iter_errors(dataset))
        if errors:
            invalid += 1
            error_count += len(errors)
        else:
            valid += 1
    return valid, invalid, error_count


def convert_dcat_catalog(old_catalog: dict) -> dict:
    """Convert DCAT-US v1.1 catalog to DCAT-US v3.0 catalog."""
    new_catalog = copy.deepcopy(old_catalog)

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
    for i, dataset in enumerate(datasets):
        identifier = dataset.get("identifier", f"index {i}")
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
            datasets[i] = dataset
        except Exception as e:
            raise CatalogConversionException(
                f"Failed to convert dataset {identifier}: {e}"
            ) from e

    return new_catalog


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
        V1_1_DATASET_SCHEMA_ID = (
            "https://project-open-data.cio.gov/v1.1/schema/"
            "non-federal_dataset.json"
        )
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

        converted_catalog = convert_dcat_catalog(catalog_to_convert)

        try:
            validate_catalog(
                V3_0_CATALOG_SCHEMA_ID, v3_0_registry, converted_catalog
            )
        except CatalogValidationException as e:
            click.echo(f"Invalid DCAT-US data: {e}", err=True)

        converted_datasets = converted_catalog.get("dataset", [])
        V3_0_DATASET_SCHEMA_ID = (
            "https://resources.data.gov/dcat-us/3.0.0/definitions/dataset"
        )
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
        elif results["error"] is False:
            click.echo("Could not convert.")
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
