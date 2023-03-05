from tuneflow_py import TuneflowPlugin
from tuneflow_devkit.validation_utils import find_match_plugin_info, validate_plugin
import unittest
import pytest


class TestPluginAnd(unittest.TestCase):
    def test_invalid_provider_id(self):
        class InvalidPlugin1(TuneflowPlugin):
            @staticmethod
            def provider_id() -> str:
                return '0abc'

            @staticmethod
            def plugin_id() -> str:
                return 'abc'

        class InvalidPlugin2(TuneflowPlugin):
            @staticmethod
            def provider_id() -> str:
                return 'a_bc'

            @staticmethod
            def plugin_id() -> str:
                return 'abc'

        bundle_info = {
            "plugins": [
                {
                    "providerId": "0abc",
                    "pluginId": "abc"
                }
            ]
        }

        with pytest.raises(Exception) as e_info_1:
            validate_plugin(plugin_class=InvalidPlugin1)

        self.assertIn("provider_id must only use", e_info_1.value.args[0])

        with pytest.raises(Exception) as e_info_2:
            validate_plugin(plugin_class=InvalidPlugin2)

        self.assertIn("provider_id must only use", e_info_2.value.args[0])

    def test_invalid_plugin_id(self):
        class InvalidPlugin1(TuneflowPlugin):
            @staticmethod
            def provider_id() -> str:
                return 'abc'

            @staticmethod
            def plugin_id() -> str:
                return '0abc'

        class InvalidPlugin2(TuneflowPlugin):
            @staticmethod
            def provider_id() -> str:
                return 'abc'

            @staticmethod
            def plugin_id() -> str:
                return 'a_bc'

        bundle_info = {
            "plugins": [
                {
                    "providerId": "0abc",
                    "pluginId": "abc"
                }
            ]
        }

        with pytest.raises(Exception) as e_info:
            validate_plugin(plugin_class=InvalidPlugin1)

        self.assertIn("plugin_id must only use", e_info.value.args[0])

        with pytest.raises(Exception) as e_info:
            validate_plugin(plugin_class=InvalidPlugin2)

        self.assertIn("plugin_id must only use", e_info.value.args[0])

    def test_missing_in_bundle(self):
        bundle_info = {
            "plugins": [
                {
                    "providerId": "cde",
                    "pluginId": "cde"
                }
            ]
        }
        plugin_info = find_match_plugin_info(bundle_info=bundle_info, provider_id='c_de', plugin_id='cde')
        self.assertIsNone(plugin_info)
