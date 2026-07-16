"""DCAT-US validation utilities for v1.1 and v3.0 schemas."""
import json
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource


SCRIPT_DIR = Path(__file__).parent
V1_1_DEFINITIONS_DIR = SCRIPT_DIR / "v1.1_definitions"
V3_0_DEFINITIONS_DIR = SCRIPT_DIR / "definitions"

V1_1_CATALOG_SCHEMA_ID = (
    "https://project-open-data.cio.gov/v1.1/schema/catalog.json"
)
V1_1_DATASET_SCHEMA_ID = (
    "https://project-open-data.cio.gov/v1.1/schema/non-federal_dataset.json"
)
V3_0_CATALOG_SCHEMA_ID = (
    "https://resources.data.gov/dcat-us/3.0.0/definitions/catalog"
)
V3_0_DATASET_SCHEMA_ID = (
    "https://resources.data.gov/dcat-us/3.0.0/definitions/dataset"
)


class CatalogValidationException(Exception):
    pass


def format_path(path):
    """Format a jsonschema path as a readable string."""
    if not path:
        return "(root)"
    parts = []
    for p in path:
        if isinstance(p, int):
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

    for error in sorted(errors, key=lambda e: list(e.path)):
        summary = summarize_error(error, prefix=prefix)
        if summary:
            output.append(summary)

    return "\n".join(output)


def summarize_error(error, prefix=""):
    """Summarize a single error into a human-readable string."""
    path = format_path(error.path)

    if error.validator in ("anyOf", "oneOf") and error.context:
        meaningful = find_meaningful_errors(error.context)

        if not meaningful:
            return (
                f"{prefix}{path}: field is not null and does not match "
                "any allowed type"
            )

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

    if "$ref" in error.schema:
        class_name = extract_schema_name(error.schema)
        if error.context:
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

    if error.validator == "required":
        missing = error.validator_value
        if isinstance(missing, list):
            missing_fields = [f for f in missing if f in error.message]
            if missing_fields:
                return f"missing required field '{missing_fields[0]}'"
        if "is a required property" in error.message:
            field = error.message.split("'")[1]
            return f"missing required field '{field}'"
        return error.message

    if error.validator == "type":
        expected = error.validator_value
        if isinstance(expected, list):
            expected = " or ".join(expected)
        return f"{prefix}{path}: expected type '{expected}'"

    if error.validator == "enum":
        return f"value not in allowed values: {error.validator_value}"

    if error.validator == "pattern":
        return f"does not match pattern '{error.validator_value}'"

    if error.validator == "format":
        return f"invalid format, expected '{error.validator_value}'"

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


def validate_v1_1_catalog(catalog: dict) -> list:
    """Validate DCAT-US v1.1 catalog and return errors with dataset context.

    Returns a list of error objects, one per invalid dataset.
    Each error object includes:
    - identifier: dataset identifier
    - title: dataset title
    - errors: list of validation error messages
    """
    v1_1_registry = load_schema_registry(V1_1_DEFINITIONS_DIR)

    validator = Draft202012Validator(
        {"$ref": V1_1_DATASET_SCHEMA_ID},
        registry=v1_1_registry,
        format_checker=Draft202012Validator.FORMAT_CHECKER,
    )

    errors = []
    datasets = catalog.get("dataset", [])

    for i, dataset in enumerate(datasets):
        validation_errors = list(validator.iter_errors(dataset))
        if validation_errors:
            identifier = dataset.get("identifier", f"index {i}")
            title = dataset.get("title", "Unknown")
            error_messages = [
                format_validation_errors([err], indent=0)
                for err in validation_errors
            ]
            errors.append({
                "identifier": identifier,
                "title": title,
                "errors": error_messages
            })

    return errors


def validate_v1_1_catalog_with_counts(catalog: dict) -> tuple[int, int, list]:
    """Validate DCAT-US v1.1 catalog and return counts with errors.

    Returns:
    - valid: number of valid datasets
    - invalid: number of invalid datasets
    - errors: list of error objects with dataset context
    """
    v1_1_registry = load_schema_registry(V1_1_DEFINITIONS_DIR)

    validator = Draft202012Validator(
        {"$ref": V1_1_DATASET_SCHEMA_ID},
        registry=v1_1_registry,
        format_checker=Draft202012Validator.FORMAT_CHECKER,
    )

    valid = 0
    invalid = 0
    errors = []
    datasets = catalog.get("dataset", [])

    for i, dataset in enumerate(datasets):
        validation_errors = list(validator.iter_errors(dataset))
        if validation_errors:
            invalid += 1
            identifier = dataset.get("identifier", f"index {i}")
            title = dataset.get("title", "Unknown")
            error_messages = [
                format_validation_errors([err], indent=0)
                for err in validation_errors
            ]
            errors.append({
                "identifier": identifier,
                "title": title,
                "errors": error_messages
            })
        else:
            valid += 1

    return valid, invalid, errors


def validate_v3_0_catalog(catalog: dict) -> list:
    """Validate DCAT-US v3.0 catalog and return errors with dataset context.

    Returns a list of error objects, one per invalid dataset.
    Each error object includes:
    - identifier: dataset identifier
    - title: dataset title
    - errors: list of validation error messages
    """
    v3_0_registry = load_schema_registry(V3_0_DEFINITIONS_DIR)

    validator = Draft202012Validator(
        {"$ref": V3_0_DATASET_SCHEMA_ID},
        registry=v3_0_registry,
        format_checker=Draft202012Validator.FORMAT_CHECKER,
    )

    errors = []
    datasets = catalog.get("dataset", [])

    for i, dataset in enumerate(datasets):
        validation_errors = list(validator.iter_errors(dataset))
        if validation_errors:
            identifier = dataset.get("identifier", f"index {i}")
            title = dataset.get("title", "Unknown")
            error_messages = [
                format_validation_errors([err], indent=0)
                for err in validation_errors
            ]
            errors.append({
                "identifier": identifier,
                "title": title,
                "errors": error_messages
            })

    return errors


def validate_v3_0_catalog_with_counts(catalog: dict) -> tuple[int, int, list]:
    """Validate DCAT-US v3.0 catalog and return counts with errors.

    Returns:
    - valid: number of valid datasets
    - invalid: number of invalid datasets
    - errors: list of error objects with dataset context
    """
    v3_0_registry = load_schema_registry(V3_0_DEFINITIONS_DIR)

    validator = Draft202012Validator(
        {"$ref": V3_0_DATASET_SCHEMA_ID},
        registry=v3_0_registry,
        format_checker=Draft202012Validator.FORMAT_CHECKER,
    )

    valid = 0
    invalid = 0
    errors = []
    datasets = catalog.get("dataset", [])

    for i, dataset in enumerate(datasets):
        validation_errors = list(validator.iter_errors(dataset))
        if validation_errors:
            invalid += 1
            identifier = dataset.get("identifier", f"index {i}")
            title = dataset.get("title", "Unknown")
            error_messages = [
                format_validation_errors([err], indent=0)
                for err in validation_errors
            ]
            errors.append({
                "identifier": identifier,
                "title": title,
                "errors": error_messages
            })
        else:
            valid += 1

    return valid, invalid, errors
