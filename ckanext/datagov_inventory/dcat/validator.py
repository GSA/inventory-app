"""DCAT-US validation utilities for v1.1 and v3.0 schemas."""
import json
from pathlib import Path

from .schema_paths import (
    EXTERNAL_DIR,
    V1_1_DEFINITIONS_DIR,
    V3_0_DEFINITIONS_DIR,
)

try:
    from jsonschema import Draft202012Validator as ValidatorClass
    from referencing import Registry, Resource
    USE_NEW_API = True
except ImportError:
    try:
        from jsonschema import Draft7Validator as ValidatorClass
        USE_NEW_API = False
    except ImportError:
        from jsonschema import Draft4Validator as ValidatorClass
        USE_NEW_API = False


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


def create_validator(schema_id: str, registry_or_store):
    """Create a validator with the given schema and registry/store."""
    # Get format_checker - handle both old and new jsonschema APIs
    try:
        format_checker = ValidatorClass.FORMAT_CHECKER
    except AttributeError:
        # jsonschema 2.4.0 doesn't have FORMAT_CHECKER class attribute
        from jsonschema import FormatChecker
        format_checker = FormatChecker()

    if USE_NEW_API:
        validator = ValidatorClass(
            {"$ref": schema_id},
            registry=registry_or_store,
            format_checker=format_checker,
        )
    else:
        from jsonschema import RefResolver
        schema = {"$ref": schema_id}
        # RefResolver constructor: (base_uri, referrer, store, ...)
        # In 2.4.0, from_schema creates resolver but doesn't accept store
        # Must use constructor directly to pass store
        resolver = RefResolver(
            base_uri="",
            referrer=schema,
            store=registry_or_store
        )
        validator = ValidatorClass(
            schema,
            resolver=resolver,
            format_checker=format_checker,
        )
    return validator


def load_schema_registry(definitions_dir: Path):
    """Load schemas into a registry (new API) or store dict (old API).

    Raises FileNotFoundError if the directory holds no schemas: missing and
    empty both glob to nothing, and an empty registry only surfaces later as
    an opaque $ref resolution error.
    """
    schema_files = sorted(definitions_dir.glob("*.json"))
    if not schema_files:
        message = f"No JSON Schema definitions found in {definitions_dir}."
        # An uninitialized submodule is an empty directory, not a missing one.
        # Only advise it for paths under _external, never for v1.1_definitions.
        if EXTERNAL_DIR in definitions_dir.resolve().parents:
            message += (
                " The DCAT-US 3.0 schemas come from the GSA/dcat-us git"
                " submodule; run"
                " `git submodule update --init _external/dcat-us`."
            )
        raise FileNotFoundError(message)

    if USE_NEW_API:
        registry = Registry()
        for schema_file in schema_files:
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
    else:
        store = {}
        for schema_file in schema_files:
            with schema_file.open() as f:
                schema = json.load(f)
                if "$id" in schema:
                    store[schema["$id"]] = schema

        non_federal = definitions_dir / "non-federal_dataset.json"
        if non_federal.exists():
            with non_federal.open() as f:
                contents = json.load(f)
            store["https://project-open-data.cio.gov/v1.1/schema/"
                  "non-federal_dataset.json"] = contents
        return store


def validate_catalog(
    schema_id: str, registry, catalog: dict
) -> None:
    """Validate a DCAT-US v1.1 or v3.0 catalog."""
    validator = create_validator(schema_id, registry)
    errors = list(validator.iter_errors(catalog))
    if errors:
        version_number = "v1.1" if "v1.1" in schema_id else "v3.0"
        raise CatalogValidationException(
            f"{version_number} validation failed with "
            f"{len(errors)} error(s):\n"
            + format_validation_errors(errors, indent=2)
        )


def validate_datasets(
    schema_id: str, registry, datasets: list
) -> tuple[int, int, int]:
    """Validate each dataset individually."""
    validator = create_validator(schema_id, registry)
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

    validator = create_validator(V1_1_DATASET_SCHEMA_ID, v1_1_registry)

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

    validator = create_validator(V1_1_DATASET_SCHEMA_ID, v1_1_registry)

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

    validator = create_validator(V3_0_DATASET_SCHEMA_ID, v3_0_registry)

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

    validator = create_validator(V3_0_DATASET_SCHEMA_ID, v3_0_registry)

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


def detect_package_conversion_errors(
    package_results: list
) -> tuple[list, list]:
    """Separate valid packages from errored packages.

    Package2Pod.convert_package returns a dict with an 'errors' key
    when conversion fails. This function separates those from valid
    packages.

    Args:
        package_results: List of package dicts from convert_package

    Returns:
        Tuple of (valid_packages, error_packages)
        - valid_packages: packages without 'errors' key
        - error_packages: packages with 'errors' key (preserved as-is)
    """
    valid = []
    errors = []

    for package in package_results:
        if isinstance(package, dict) and 'errors' in package:
            errors.append(package)
        else:
            valid.append(package)

    return valid, errors


def capture_conversion_logs(conversion_function, logger_name):
    """Capture log output during conversion.

    Args:
        conversion_function: Callable that performs conversion
        logger_name: Name of logger to capture

    Returns:
        Tuple of (result, log_output)
        - result: return value from conversion_function
        - log_output: string containing captured log messages
    """
    import logging
    import io

    logger = logging.getLogger(logger_name)
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setLevel(logging.WARNING)
    formatter = logging.Formatter('%(levelname)s: %(message)s')
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    original_level = logger.level
    logger.setLevel(logging.WARNING)

    try:
        result = conversion_function()
        handler.flush()
        log_output = stream.getvalue()
        return result, log_output
    finally:
        logger.removeHandler(handler)
        logger.setLevel(original_level)
        handler.close()
        stream.close()


def write_zip(data, error_log=None, errors_json=None):
    """Create a ZIP file containing catalog data and optional error files.

    Args:
        data: Dict containing the catalog data, or None
        error_log: String containing log output, or None
        errors_json: List of error dicts, or None

    Returns:
        Binary ZIP file data
    """
    import zipfile
    import io
    import json

    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(
        zip_buffer, 'w', zipfile.ZIP_DEFLATED
    ) as zip_file:
        if data:
            data_json = json.dumps(data, indent=2, ensure_ascii=False)
            zip_file.writestr('data.json', data_json.encode('utf-8'))
        else:
            zip_file.writestr('empty.json', '')

        if errors_json:
            errors_json_str = json.dumps(
                errors_json, indent=2, ensure_ascii=False
            )
            zip_file.writestr('errors.json', errors_json_str.encode('utf-8'))

        if error_log:
            error_log_normalized = error_log.replace("\n", "\r\n")
            zip_file.writestr('errorlog.txt', error_log_normalized)

    zip_buffer.seek(0)
    return zip_buffer.getvalue()


def process_export_with_error_tracking(v1_1_catalog):
    """Process complete export with comprehensive error tracking.

    This orchestrates the full export pipeline:
    1. Convert v1.1 → v3.0 (capturing transformation errors)
    2. Validate v3.0 datasets
    3. Collect all errors and logs
    4. Create ZIP with data, errors, and logs

    Args:
        v1_1_catalog: Dict containing DCAT-US v1.1 catalog

    Returns:
        Binary ZIP file data

    Note: We only validate v3.0 since that's what's in the output data.json.
    Validating v1.1 would report false positives for fields required in v1.1
    but not in v3.0 (like 'keyword', 'modified', 'publisher', 'accessLevel').
    """
    import logging
    from . import dcat_converter

    logger = logging.getLogger(__name__)
    all_errors = []

    catalog_v3_0, conversion_errors = dcat_converter.convert_dcat_catalog(
        v1_1_catalog
    )
    if conversion_errors:
        all_errors.extend(conversion_errors)
        logger.warning(
            f"Transformation: {len(conversion_errors)} datasets failed"
        )

    v3_0_validation_errors = validate_v3_0_catalog(catalog_v3_0)
    if v3_0_validation_errors:
        all_errors.extend(v3_0_validation_errors)
        logger.warning(
            f"v3.0 validation: {len(v3_0_validation_errors)} "
            "invalid datasets"
        )

    def generate_output():
        return catalog_v3_0

    result, log_output = capture_conversion_logs(
        generate_output,
        logger_name=__name__
    )

    zip_binary = write_zip(
        data=result,
        error_log=log_output if log_output else None,
        errors_json=all_errors if all_errors else None
    )

    return zip_binary
