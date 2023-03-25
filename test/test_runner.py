from __future__ import annotations
from fastapi import Request, HTTPException, status
from fastapi.testclient import TestClient
from tuneflow_devkit import Runner
from hello_world_plugin import HelloWorldPlugin
import unittest
import pathlib
import json
from typing import Optional


class TestPluginCases(unittest.TestCase):
    def test_simple_runner(self):
        bundle_file_path = str(pathlib.PurePath(
            __file__).parent.joinpath('hello_world_plugin.bundle.json'))
        app = Runner(plugin_class_list=[HelloWorldPlugin], bundle_file_path=bundle_file_path).start()

        client = TestClient(app)
        response = client.get("/plugin-bundle-info")
        assert response.status_code == 200
        with open(bundle_file_path, 'r') as bundle_file:
            bundle_info = json.load(bundle_file)
            assert response.json() == bundle_info

    def test_auth_enabled_runner(self):
        bundle_file_path = str(pathlib.PurePath(
            __file__).parent.joinpath('hello_world_plugin.bundle.json'))

        def auth_failed_handler():
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

        app = Runner(plugin_class_list=[HelloWorldPlugin], bundle_file_path=bundle_file_path).start(config={
            "auth": {
                "handler": auth_failed_handler
            }
        })

        client = TestClient(app)
        response = client.post("/init-plugin-params")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


if __name__ == '__main__':
    unittest.main()
