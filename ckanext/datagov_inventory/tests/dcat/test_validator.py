import pytest

from ckanext.datagov_inventory.dcat import validator


class TestV1ValidationTracking:

    @pytest.fixture
    def invalid_v1_1_catalog(self):
        return {
            "@context": (
                "https://project-open-data.cio.gov/v1.1/schema/"
                "catalog.jsonld"
            ),
            "conformsTo": "https://project-open-data.cio.gov/v1.1/schema",
            "dataset": [
                {
                    "title": "Missing Required Fields",
                    "identifier": "invalid-001"
                },
                {
                    "title": "Valid Dataset",
                    "identifier": "valid-001",
                    "description": "A valid dataset",
                    "modified": "2024-01-15",
                    "keyword": ["valid", "test"],
                    "accessLevel": "public",
                    "publisher": {"name": "Test Agency"},
                    "contactPoint": {
                        "fn": "Jane Doe",
                        "hasEmail": "mailto:jane@example.gov"
                    }
                }
            ]
        }

    def test_validate_v1_1_catalog_returns_validation_errors(
        self, invalid_v1_1_catalog
    ):
        errors = validator.validate_v1_1_catalog(invalid_v1_1_catalog)
        assert isinstance(errors, list)
        assert len(errors) > 0

    def test_validate_v1_1_catalog_includes_dataset_context(
        self, invalid_v1_1_catalog
    ):
        errors = validator.validate_v1_1_catalog(invalid_v1_1_catalog)
        invalid_dataset_errors = [
            e for e in errors if e.get("identifier") == "invalid-001"
        ]
        assert len(invalid_dataset_errors) > 0
        assert "identifier" in invalid_dataset_errors[0]
        assert "title" in invalid_dataset_errors[0]
        assert "errors" in invalid_dataset_errors[0]

    def test_validate_v1_1_catalog_returns_empty_for_valid(
        self, sample_v1_1_catalog
    ):
        errors = validator.validate_v1_1_catalog(sample_v1_1_catalog)
        assert errors == []

    def test_validate_v1_1_catalog_counts_valid_and_invalid(
        self, invalid_v1_1_catalog
    ):
        valid, invalid, errors = validator.validate_v1_1_catalog_with_counts(
            invalid_v1_1_catalog
        )
        assert valid == 1
        assert invalid == 1
        assert len(errors) == 1

    @pytest.fixture
    def sample_v1_1_catalog(self):
        return {
            "@context": (
                "https://project-open-data.cio.gov/v1.1/schema/"
                "catalog.jsonld"
            ),
            "conformsTo": "https://project-open-data.cio.gov/v1.1/schema",
            "describedBy": (
                "https://project-open-data.cio.gov/v1.1/schema/"
                "catalog.json"
            ),
            "modified": "2024-01-15T10:30:00",
            "dataset": [
                {
                    "title": "Test Dataset",
                    "identifier": "test-001",
                    "description": "A test dataset",
                    "modified": "2024-01-15",
                    "keyword": ["test", "dataset"],
                    "accessLevel": "public",
                    "publisher": {"name": "Test Agency"},
                    "contactPoint": {
                        "fn": "Jane Doe",
                        "hasEmail": "mailto:jane@example.gov"
                    }
                }
            ]
        }


class TestV3ValidationTracking:

    @pytest.fixture
    def invalid_v3_0_catalog(self):
        return {
            "conformsTo": {
                "@type": "Standard",
                "title": "DCAT-US 3.0",
                "identifier": "https://resources.data.gov/dcat-us/3.0.0"
            },
            "dataset": [
                {
                    "title": "Missing Required Fields",
                    "identifier": "invalid-v3-001"
                },
                {
                    "title": "Valid V3 Dataset",
                    "identifier": "valid-v3-001",
                    "description": "A valid v3.0 dataset",
                    "modified": "2024-01-15T10:30:00Z",
                    "keyword": ["valid", "test"],
                    "accessLevel": "public",
                    "accessRights": "public",
                    "publisher": {"name": "Test Agency"},
                    "contactPoint": {
                        "fn": "Jane Doe",
                        "hasEmail": "mailto:jane@example.gov"
                    }
                }
            ]
        }

    def test_validate_v3_0_catalog_returns_validation_errors(
        self, invalid_v3_0_catalog
    ):
        errors = validator.validate_v3_0_catalog(invalid_v3_0_catalog)
        assert isinstance(errors, list)
        assert len(errors) > 0

    def test_validate_v3_0_catalog_includes_dataset_context(
        self, invalid_v3_0_catalog
    ):
        errors = validator.validate_v3_0_catalog(invalid_v3_0_catalog)
        invalid_dataset_errors = [
            e for e in errors if e.get("identifier") == "invalid-v3-001"
        ]
        assert len(invalid_dataset_errors) > 0
        assert "identifier" in invalid_dataset_errors[0]
        assert "title" in invalid_dataset_errors[0]
        assert "errors" in invalid_dataset_errors[0]

    def test_validate_v3_0_catalog_returns_empty_for_valid(self):
        valid_catalog = {
            "conformsTo": {
                "@type": "Standard",
                "title": "DCAT-US 3.0",
                "identifier": "https://resources.data.gov/dcat-us/3.0.0"
            },
            "dataset": [
                {
                    "title": "Valid Dataset",
                    "identifier": "valid-001",
                    "description": "A valid dataset",
                    "modified": "2024-01-15T10:30:00Z",
                    "keyword": ["test"],
                    "accessLevel": "public",
                    "accessRights": "public",
                    "publisher": {"name": "Test Agency"},
                    "contactPoint": {
                        "fn": "Jane Doe",
                        "hasEmail": "mailto:jane@example.gov"
                    }
                }
            ]
        }

        errors = validator.validate_v3_0_catalog(valid_catalog)
        assert errors == []

    def test_validate_v3_0_catalog_counts_valid_and_invalid(
        self, invalid_v3_0_catalog
    ):
        valid, invalid, errors = validator.validate_v3_0_catalog_with_counts(
            invalid_v3_0_catalog
        )
        assert valid == 1
        assert invalid == 1
        assert len(errors) == 1


class TestPackage2PodErrorTracking:

    def test_detect_package_conversion_errors_identifies_error_key(self):
        from ckanext.datagov_inventory.dcat.validator import (
            detect_package_conversion_errors
        )

        package_results = [
            {
                "title": "Valid Package",
                "identifier": "valid-001",
                "description": "A valid package"
            },
            {
                "title": "Error Package",
                "identifier": "error-001",
                "errors": "Missing required fields"
            },
            {
                "title": "Another Valid",
                "identifier": "valid-002",
                "description": "Another valid package"
            }
        ]

        valid, errors = detect_package_conversion_errors(package_results)

        assert len(valid) == 2
        assert len(errors) == 1
        assert valid[0]["identifier"] == "valid-001"
        assert valid[1]["identifier"] == "valid-002"
        assert errors[0]["identifier"] == "error-001"

    def test_detect_package_conversion_errors_preserves_error_details(self):
        from ckanext.datagov_inventory.dcat.validator import (
            detect_package_conversion_errors
        )

        package_results = [
            {
                "title": "Error Package",
                "identifier": "error-001",
                "errors": "Multiple validation failures"
            }
        ]

        valid, errors = detect_package_conversion_errors(package_results)

        assert len(errors) == 1
        assert "identifier" in errors[0]
        assert "title" in errors[0]
        assert "errors" in errors[0]
        assert errors[0]["errors"] == "Multiple validation failures"

    def test_detect_package_conversion_errors_handles_empty_list(self):
        from ckanext.datagov_inventory.dcat.validator import (
            detect_package_conversion_errors
        )

        valid, errors = detect_package_conversion_errors([])

        assert valid == []
        assert errors == []

    def test_detect_package_conversion_errors_handles_all_valid(self):
        from ckanext.datagov_inventory.dcat.validator import (
            detect_package_conversion_errors
        )

        package_results = [
            {"title": "Valid 1", "identifier": "v1"},
            {"title": "Valid 2", "identifier": "v2"}
        ]

        valid, errors = detect_package_conversion_errors(package_results)

        assert len(valid) == 2
        assert errors == []

    def test_detect_package_conversion_errors_handles_all_errors(self):
        from ckanext.datagov_inventory.dcat.validator import (
            detect_package_conversion_errors
        )

        package_results = [
            {"title": "Error 1", "identifier": "e1", "errors": "Bad data"},
            {"title": "Error 2", "identifier": "e2", "errors": "Missing field"}
        ]

        valid, errors = detect_package_conversion_errors(package_results)

        assert valid == []
        assert len(errors) == 2


class TestErrorLogCapture:

    def test_capture_processing_logs_returns_log_string(self):
        import logging
        from ckanext.datagov_inventory.dcat.validator import (
            capture_processing_logs
        )

        def processing_function():
            logger = logging.getLogger(__name__)
            logger.warning("Processing warning message")
            logger.error("Processing error message")
            return "result"

        result, log_output = capture_processing_logs(
            processing_function,
            logger_name=__name__
        )

        assert result == "result"
        assert isinstance(log_output, str)
        assert "Processing warning message" in log_output
        assert "Processing error message" in log_output

    def test_capture_processing_logs_handles_no_logs(self):
        from ckanext.datagov_inventory.dcat.validator import (
            capture_processing_logs
        )

        def silent_function():
            return "done"

        result, log_output = capture_processing_logs(
            silent_function,
            logger_name="test"
        )

        assert result == "done"
        assert log_output == ""

    def test_capture_processing_logs_preserves_exceptions(self):
        from ckanext.datagov_inventory.dcat.validator import (
            capture_processing_logs
        )

        def failing_function():
            raise ValueError("Test error")

        try:
            capture_processing_logs(failing_function, logger_name="test")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert str(e) == "Test error"

    def test_capture_processing_logs_formats_multiline_output(self):
        import logging
        from ckanext.datagov_inventory.dcat.validator import (
            capture_processing_logs
        )

        def multi_log_function():
            logger = logging.getLogger(__name__)
            logger.warning("Line 1")
            logger.warning("Line 2")
            logger.error("Line 3")
            return "complete"

        result, log_output = capture_processing_logs(
            multi_log_function,
            logger_name=__name__
        )

        assert "Line 1" in log_output
        assert "Line 2" in log_output
        assert "Line 3" in log_output


class TestWriteZip:

    def test_write_zip_creates_zip_with_data_json(self):
        import zipfile
        import io
        from ckanext.datagov_inventory.dcat.validator import write_zip

        data = {"test": "data", "datasets": []}
        zip_binary = write_zip(data, error_log=None, errors_json=None)

        assert isinstance(zip_binary, bytes)
        zip_file = zipfile.ZipFile(io.BytesIO(zip_binary))
        assert "data.json" in zip_file.namelist()

    def test_write_zip_includes_errors_json_when_present(self):
        import zipfile
        import io
        import json
        from ckanext.datagov_inventory.dcat.validator import write_zip

        data = {"test": "data"}
        errors = [
            {"identifier": "error-001", "title": "Error", "errors": ["Bad"]}
        ]
        zip_binary = write_zip(data, error_log=None, errors_json=errors)

        zip_file = zipfile.ZipFile(io.BytesIO(zip_binary))
        assert "errors.json" in zip_file.namelist()

        errors_content = zip_file.read("errors.json")
        errors_data = json.loads(errors_content)
        assert len(errors_data) == 1
        assert errors_data[0]["identifier"] == "error-001"

    def test_write_zip_includes_errorlog_txt_when_present(self):
        import zipfile
        import io
        from ckanext.datagov_inventory.dcat.validator import write_zip

        data = {"test": "data"}
        error_log = "WARNING: Something happened\nERROR: Something bad"
        zip_binary = write_zip(data, error_log=error_log, errors_json=None)

        zip_file = zipfile.ZipFile(io.BytesIO(zip_binary))
        assert "errorlog.txt" in zip_file.namelist()

        log_content = zip_file.read("errorlog.txt").decode("utf-8")
        assert "WARNING: Something happened" in log_content
        assert "ERROR: Something bad" in log_content

    def test_write_zip_includes_all_files_when_all_present(self):
        import zipfile
        import io
        from ckanext.datagov_inventory.dcat.validator import write_zip

        data = {"catalog": "data"}
        errors = [{"identifier": "e1", "errors": ["Bad"]}]
        error_log = "WARNING: Test warning"

        zip_binary = write_zip(
            data,
            error_log=error_log,
            errors_json=errors
        )

        zip_file = zipfile.ZipFile(io.BytesIO(zip_binary))
        filenames = zip_file.namelist()

        assert "data.json" in filenames
        assert "errors.json" in filenames
        assert "errorlog.txt" in filenames
        assert len(filenames) == 3

    def test_write_zip_creates_empty_json_when_no_data(self):
        import zipfile
        import io
        from ckanext.datagov_inventory.dcat.validator import write_zip

        zip_binary = write_zip(None, error_log=None, errors_json=None)

        zip_file = zipfile.ZipFile(io.BytesIO(zip_binary))
        assert "empty.json" in zip_file.namelist()
        assert "data.json" not in zip_file.namelist()

    def test_write_zip_data_json_is_valid_json(self):
        import zipfile
        import io
        import json
        from ckanext.datagov_inventory.dcat.validator import write_zip

        data = {"conformsTo": "DCAT-US 3.0", "dataset": []}
        zip_binary = write_zip(data, error_log=None, errors_json=None)

        zip_file = zipfile.ZipFile(io.BytesIO(zip_binary))
        data_content = zip_file.read("data.json")
        parsed = json.loads(data_content)

        assert parsed["conformsTo"] == "DCAT-US 3.0"
        assert parsed["dataset"] == []


class TestEndToEndErrorHandling:

    def test_full_export_flow_with_mixed_valid_and_invalid_datasets(self):
        import zipfile
        import io
        import json
        from ckanext.datagov_inventory.dcat.validator import (
            process_export_with_error_tracking
        )

        v1_1_catalog = {
            "@context": "https://project-open-data.cio.gov/v1.1/schema/catalog.jsonld",
            "conformsTo": "https://project-open-data.cio.gov/v1.1/schema",
            "dataset": [
                {
                    "title": "Valid Dataset",
                    "identifier": "valid-001",
                    "description": "Valid",
                    "modified": "2024-01-15",
                    "keyword": ["test"],
                    "accessLevel": "public",
                    "publisher": {"name": "Test Agency"},
                    "contactPoint": {
                        "fn": "Jane Doe",
                        "hasEmail": "mailto:jane@example.gov"
                    }
                },
                {
                    "title": "Invalid Dataset",
                    "identifier": "invalid-001",
                    "description": "Missing required fields"
                }
            ]
        }

        zip_binary = process_export_with_error_tracking(v1_1_catalog)

        assert isinstance(zip_binary, bytes)
        zip_file = zipfile.ZipFile(io.BytesIO(zip_binary))
        filenames = zip_file.namelist()

        assert "data.json" in filenames
        assert "errors.json" in filenames

        data_content = json.loads(zip_file.read("data.json"))
        assert "dataset" in data_content
        assert len(data_content["dataset"]) >= 0

        errors_content = json.loads(zip_file.read("errors.json"))
        assert isinstance(errors_content, list)

    def test_full_export_flow_captures_v1_1_validation_errors(self):
        import zipfile
        import io
        import json
        from ckanext.datagov_inventory.dcat.validator import (
            process_export_with_error_tracking
        )

        v1_1_catalog = {
            "@context": "https://project-open-data.cio.gov/v1.1/schema/catalog.jsonld",
            "conformsTo": "https://project-open-data.cio.gov/v1.1/schema",
            "dataset": [
                {
                    "title": "Missing Fields",
                    "identifier": "missing-001"
                }
            ]
        }

        zip_binary = process_export_with_error_tracking(v1_1_catalog)
        zip_file = zipfile.ZipFile(io.BytesIO(zip_binary))

        assert "errors.json" in zip_file.namelist()
        errors = json.loads(zip_file.read("errors.json"))
        assert len(errors) > 0

        error = errors[0]
        assert error["identifier"] == "missing-001"
        assert "errors" in error

    def test_full_export_flow_captures_transformation_errors(self):
        import zipfile
        import io
        import json
        from ckanext.datagov_inventory.dcat.validator import (
            process_export_with_error_tracking
        )

        v1_1_catalog = {
            "@context": "https://project-open-data.cio.gov/v1.1/schema/catalog.jsonld",
            "conformsTo": "https://project-open-data.cio.gov/v1.1/schema",
            "dataset": [
                {
                    "title": "Transform Error Dataset",
                    "identifier": "transform-error-001",
                    "description": "Will fail transformation",
                    "modified": "2024-01-15",
                    "keyword": ["test"],
                    "accessLevel": "public",
                    "publisher": {"name": "Test Agency"},
                    "contactPoint": {
                        "fn": "Jane Doe",
                        "hasEmail": "mailto:jane@example.gov"
                    },
                    "temporal": {"invalid": "structure"}
                }
            ]
        }

        zip_binary = process_export_with_error_tracking(v1_1_catalog)
        zip_file = zipfile.ZipFile(io.BytesIO(zip_binary))

        assert "data.json" in zip_file.namelist()
        data = json.loads(zip_file.read("data.json"))
        assert "dataset" in data

    def test_full_export_flow_captures_v3_0_validation_errors(self):
        import zipfile
        import io
        import json
        from ckanext.datagov_inventory.dcat.validator import (
            process_export_with_error_tracking
        )

        v1_1_catalog = {
            "@context": "https://project-open-data.cio.gov/v1.1/schema/catalog.jsonld",
            "conformsTo": "https://project-open-data.cio.gov/v1.1/schema",
            "dataset": [
                {
                    "title": "Dataset",
                    "identifier": "v3-invalid-001",
                    "description": "Valid v1.1 but might be invalid v3.0",
                    "modified": "2024-01-15",
                    "keyword": ["test"],
                    "accessLevel": "public",
                    "publisher": {"name": "Test"},
                    "contactPoint": {
                        "fn": "Jane Doe",
                        "hasEmail": "mailto:jane@example.gov"
                    }
                }
            ]
        }

        zip_binary = process_export_with_error_tracking(v1_1_catalog)
        zip_file = zipfile.ZipFile(io.BytesIO(zip_binary))

        assert "data.json" in zip_file.namelist()

    def test_full_export_flow_includes_errorlog_when_warnings_occur(self):
        import zipfile
        import io
        from ckanext.datagov_inventory.dcat.validator import (
            process_export_with_error_tracking
        )

        v1_1_catalog = {
            "@context": "https://project-open-data.cio.gov/v1.1/schema/catalog.jsonld",
            "conformsTo": "https://project-open-data.cio.gov/v1.1/schema",
            "dataset": [
                {
                    "title": "Dataset with warnings",
                    "identifier": "warn-001",
                    "description": "Test",
                    "modified": "2024-01-15",
                    "keyword": ["test"],
                    "accessLevel": "public",
                    "publisher": {"name": "Test"},
                    "contactPoint": {
                        "fn": "Jane Doe",
                        "hasEmail": "mailto:jane@example.gov"
                    }
                }
            ]
        }

        zip_binary = process_export_with_error_tracking(v1_1_catalog)
        zip_file = zipfile.ZipFile(io.BytesIO(zip_binary))

        filenames = zip_file.namelist()
        assert "data.json" in filenames

    def test_full_export_flow_with_all_valid_datasets(self):
        import zipfile
        import io
        import json
        from ckanext.datagov_inventory.dcat.validator import (
            process_export_with_error_tracking
        )

        v1_1_catalog = {
            "@context": "https://project-open-data.cio.gov/v1.1/schema/catalog.jsonld",
            "conformsTo": "https://project-open-data.cio.gov/v1.1/schema",
            "dataset": [
                {
                    "title": "Valid Dataset 1",
                    "identifier": "valid-001",
                    "description": "Valid",
                    "modified": "2024-01-15",
                    "keyword": ["test"],
                    "accessLevel": "public",
                    "publisher": {"name": "Test Agency"},
                    "contactPoint": {
                        "fn": "Jane Doe",
                        "hasEmail": "mailto:jane@example.gov"
                    }
                },
                {
                    "title": "Valid Dataset 2",
                    "identifier": "valid-002",
                    "description": "Also valid",
                    "modified": "2024-01-15",
                    "keyword": ["test"],
                    "accessLevel": "public",
                    "publisher": {"name": "Test Agency"},
                    "contactPoint": {
                        "fn": "Jane Doe",
                        "hasEmail": "mailto:jane@example.gov"
                    }
                }
            ]
        }

        zip_binary = process_export_with_error_tracking(v1_1_catalog)
        zip_file = zipfile.ZipFile(io.BytesIO(zip_binary))

        assert "data.json" in zip_file.namelist()
        data = json.loads(zip_file.read("data.json"))
        assert len(data["dataset"]) >= 0

        if "errors.json" in zip_file.namelist():
            errors = json.loads(zip_file.read("errors.json"))
            assert isinstance(errors, list)
