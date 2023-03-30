from __future__ import annotations
from fastapi import Request, HTTPException, status
from fastapi.testclient import TestClient
from tuneflow_devkit import Runner
from tuneflow_py import Song
from hello_world_plugin import HelloWorldPlugin
import unittest
import pathlib
import json
from typing import Optional
from msgpack import packb, unpackb


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

    def test_sync_runner(self):
        bundle_file_path = str(pathlib.PurePath(
            __file__).parent.joinpath('hello_world_plugin.bundle.json'))

        app = Runner(plugin_class_list=[HelloWorldPlugin], bundle_file_path=bundle_file_path).start(config={
        })

        client = TestClient(app)
        response = client.post("/jobs", data=packb({
            "providerId": "andantei",
            "pluginId": "hello-world",
            "params": {},
            "song": Song().serialize_to_bytestring()
        }))
        actual_result = response.content
        assert actual_result is not None
        parsed_actual_result = unpackb(actual_result)
        assert parsed_actual_result["status"] == "OK"
        assert parsed_actual_result["song"] is not None

    def test_async_runner(self):
        bundle_file_path = str(pathlib.PurePath(
            __file__).parent.joinpath('hello_world_plugin.bundle.json'))
        global actual_result
        global actual_job_id
        actual_result = None
        actual_job_id = None

        def test_store_uploader(job_id, result):
            global actual_result
            global actual_job_id
            actual_result = result
            actual_job_id = job_id

        def get_result_url(job_id):
            return f"http://download.link/{job_id}"

        app = Runner(plugin_class_list=[HelloWorldPlugin], bundle_file_path=bundle_file_path).start(config={
            "async": {
                "store": {
                    "uploader": test_store_uploader,
                    "resultUrlResolver": get_result_url
                }
            }
        })

        client = TestClient(app)
        accepted_result = client.post("/jobs", data=packb({
            "providerId": "andantei",
            "pluginId": "hello-world",
            "params": {},
            "song": Song().serialize_to_bytestring()
        }))
        parsed_actual_result = unpackb(actual_result)
        assert parsed_actual_result["status"] == "OK"
        assert parsed_actual_result["jobId"] is not None
        assert parsed_actual_result["song"] is not None
        assert accepted_result is not None
        parsed_accepted_result = unpackb(accepted_result.content)
        assert parsed_accepted_result["status"] == "ACCEPTED"
        assert parsed_accepted_result["jobId"] == parsed_actual_result["jobId"]
        assert parsed_accepted_result["resultUrl"] == "http://download.link/{job_id}".format(
            job_id=parsed_actual_result["jobId"])
        assert actual_job_id == parsed_actual_result["jobId"]


if __name__ == '__main__':
    unittest.main()
