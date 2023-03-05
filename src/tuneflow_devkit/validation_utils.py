from typing import Type
from tuneflow_py import TuneflowPlugin
import re


def validate_plugin(plugin_class: Type[TuneflowPlugin]):
    MAX_ID_LENGTH = 100
    if plugin_class.plugin_id() is None:
        raise Exception("plugin_id must be provided")

    if len(plugin_class.plugin_id()) > MAX_ID_LENGTH:
        raise Exception(f"plugin_id must not be longer than {MAX_ID_LENGTH}")

    if re.compile(r'[a-zA-Z]+[0-9a-zA-Z-]*').fullmatch(plugin_class.plugin_id()) is None:
        raise Exception('plugin_id must only use [0-9a-zA-Z-] and the first letter cannot be a digit`')

    if plugin_class.provider_id() is None:
        raise Exception("provider_id must be provided")

    if len(plugin_class.provider_id()) > MAX_ID_LENGTH:
        raise Exception(f"provider_id must not be longer than {MAX_ID_LENGTH}")

    if re.compile(r'[a-zA-Z]+[0-9a-zA-Z-]*').fullmatch(plugin_class.provider_id()) is None:
        raise Exception('provider_id must only use [0-9a-zA-Z-] and the first letter cannot be a digit`')


def find_match_plugin_info(bundle_info, provider_id: str, plugin_id: str):
    for plugin_info in bundle_info["plugins"]:
        if plugin_info["providerId"] == provider_id and plugin_info["pluginId"] == plugin_id:
            return plugin_info
    return None
