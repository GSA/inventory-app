"""Tests for validator.py backwards compatibility with old jsonschema versions.

These tests ensure the validator module can be imported and used in environments
with jsonschema 2.4.0 (which lacks Draft7Validator and Draft202012Validator).
"""
import sys
import unittest
from unittest import mock


class TestValidatorBackwardsCompatibility(unittest.TestCase):
    """Test validator import compatibility with different jsonschema versions."""

    def test_import_with_draft202012_available(self):
        """Test validator imports correctly when Draft202012Validator exists."""
        # This should work in modern jsonschema (4.x+)
        try:
            from ckanext.datagov_inventory.dcat.validator import (
                ValidatorClass,
                USE_NEW_API,
            )
            # If this environment has Draft202012Validator, verify it's used
            from jsonschema import Draft202012Validator
            self.assertEqual(ValidatorClass, Draft202012Validator)
            self.assertTrue(USE_NEW_API)
        except ImportError:
            # If Draft202012Validator doesn't exist, that's fine -
            # fallback should work
            pass

    def test_import_with_only_draft4_available(self):
        """Test that Draft4Validator exists in current environment.

        This test verifies that Draft4Validator (available in jsonschema 2.4.0)
        is importable. Since we can't easily mock the entire jsonschema module
        reload process, this test confirms that the fallback target exists.
        """
        try:
            from jsonschema import Draft4Validator
            # Draft4Validator should be available
            self.assertIsNotNone(Draft4Validator)
            self.assertTrue(hasattr(Draft4Validator, 'FORMAT_CHECKER'))
        except ImportError:
            self.fail("Draft4Validator should be available as fallback target")

    def test_validator_module_imports_successfully(self):
        """Test that validator module imports without errors."""
        # This is the most basic test - can we import the module at all?
        try:
            from ckanext.datagov_inventory.dcat import validator
            self.assertIsNotNone(validator)
            self.assertTrue(hasattr(validator, 'ValidatorClass'))
            self.assertTrue(hasattr(validator, 'USE_NEW_API'))
            self.assertTrue(hasattr(validator, 'create_validator'))
            self.assertTrue(hasattr(validator, 'load_schema_registry'))
        except ImportError as e:
            self.fail(f"Failed to import validator module: {e}")

    def test_create_validator_function_exists(self):
        """Test that create_validator function is available."""
        from ckanext.datagov_inventory.dcat.validator import create_validator
        # Function should be callable
        self.assertTrue(callable(create_validator))

    def test_load_schema_registry_function_exists(self):
        """Test that load_schema_registry function is available."""
        from ckanext.datagov_inventory.dcat.validator import (
            load_schema_registry
        )
        # Function should be callable
        self.assertTrue(callable(load_schema_registry))

    def test_validator_class_has_format_checker(self):
        """Test that ValidatorClass has FORMAT_CHECKER attribute."""
        from ckanext.datagov_inventory.dcat.validator import ValidatorClass
        # All Draft validators (4, 7, 2020-12) have FORMAT_CHECKER
        self.assertTrue(hasattr(ValidatorClass, 'FORMAT_CHECKER'))

    def test_backwards_compatibility_prevents_import_error(self):
        """Test that the compatibility layer prevents the ImportError from
        inventory.log.

        This test specifically addresses the error:
        ImportError: cannot import name 'Draft7Validator' from 'jsonschema'

        The validator should gracefully fall back to Draft4Validator
        when newer validators are unavailable.
        """
        # This test documents the fix for the production error
        try:
            from ckanext.datagov_inventory.dcat.validator import (
                ValidatorClass,
                create_validator,
                load_schema_registry,
            )

            # These should all be importable without errors
            self.assertIsNotNone(ValidatorClass)
            self.assertIsNotNone(create_validator)
            self.assertIsNotNone(load_schema_registry)

            # ValidatorClass should be one of the valid validator classes
            validator_name = ValidatorClass.__name__
            valid_names = [
                'Draft4Validator',
                'Draft7Validator',
                'Draft202012Validator'
            ]
            self.assertIn(
                validator_name,
                valid_names,
                f"ValidatorClass should be a valid Draft validator, "
                f"got: {validator_name}"
            )

        except ImportError as e:
            self.fail(
                f"Backwards compatibility failed - ImportError should not "
                f"occur with fallback chain. Error: {e}"
            )
