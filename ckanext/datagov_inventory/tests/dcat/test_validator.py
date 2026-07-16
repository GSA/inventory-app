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
