from __future__ import annotations
from tuneflow_py import TuneflowPlugin, Song
from typing import Type, List
import json
from msgpack import unpackb, packb
from tuneflow_devkit.validation_utils import validate_plugin, find_match_plugin_info
from collections import defaultdict
from fastapi import FastAPI, Request, Response, Depends, BackgroundTasks
import asyncio
import functools
from fastapi.middleware.cors import CORSMiddleware
import traceback
from nanoid import generate as generate_nanoid
from urllib.parse import urljoin


class Runner:
    def __init__(self, plugin_class_list: List[Type[TuneflowPlugin]], bundle_file_path: str) -> None:
        '''
        Creates a server for a plugin bundle.

        A plugin bundle can contain multiple plugins in the same virtualenv, their information is specified in the bundle.json.
        '''
        for plugin_class in plugin_class_list:
            validate_plugin(plugin_class=plugin_class)
        self._plugin_class_list = plugin_class_list
        self._plugin_info_map = defaultdict(dict)
        self._bundle_info: dict | None = None
        with open(bundle_file_path, 'r', encoding='utf-8') as bundle_file:
            bundle_info = json.load(bundle_file)
            self._bundle_info = bundle_info
            # Validate plugin and bundle.
            for plugin_class in plugin_class_list:
                provider_id = plugin_class.provider_id()
                plugin_id = plugin_class.plugin_id()
                plugin_info = find_match_plugin_info(
                    bundle_info=bundle_info, provider_id=provider_id,
                    plugin_id=plugin_id)
                if plugin_info is None:
                    raise Exception(
                        "plugin not specified in the bundle, check your bundle.json. For more information checkout https://github.com/tuneflow/tuneflow-py")
                self._plugin_info_map[provider_id][plugin_id] = plugin_info
            # Ensure all entries in bundle.info have corresponding plugin code.
            for plugin_info in bundle_info["plugins"]:
                if not any(
                        plugin_class.provider_id() == plugin_info["providerId"] and plugin_class.plugin_id() ==
                        plugin_info["pluginId"] for plugin_class in plugin_class_list):
                    raise Exception(
                        f'Plugin {plugin_info["providerId"]} {plugin_info["pluginId"]} has no corresponding source code in the plugin list')

    def start(self, path_prefix='/', config=None):
        '''
        @param port Port to run the server
        '''

        app = FastAPI()
        print(f'Using config: {config}')

        cors_allowed_origins = config["corsConfig"]["allowedOrigins"] if config is not None and "corsConfig" in config and "allowedOrigins" in config["corsConfig"] else [
            "*"]
        print(f'Using cors allowed origins: {cors_allowed_origins}')
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_allowed_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        async_config = config["async"] if config and "async" in config else None
        exception_handler = config["exception"]["handler"] if config and "exception" in config and "handler" in config["exception"] else None

        @app.middleware("http")
        async def add_vary_origin_header(request: Request, call_next):
            response = await call_next(request)
            response.headers["Vary"] = 'Origin'
            return response

        if not path_prefix.endswith('/'):
            path_prefix += '/'

        get_info_path = urljoin(path_prefix, 'plugin-bundle-info')
        init_plugin_path = urljoin(path_prefix, 'init-plugin-params')
        run_plugin_path = urljoin(path_prefix, 'jobs')

        print(f'Serving bundle info at: {get_info_path}')

        def init_plugin_task(plugin_class: Type[TuneflowPlugin], song: Song):
            try:
                params_config = plugin_class.params(song)
                return {"status": "OK",
                        "paramsConfig": params_config,
                        "params": plugin_class._get_default_params(param_config=params_config)
                        }
            except Exception as e:
                print(traceback.format_exc())
                return {
                    "status": "ERROR"
                }

        def run_plugin_task(plugin_class: Type[TuneflowPlugin], song, params):
            try:
                plugin_class.run(song, params)
            except Exception as e:
                print(traceback.format_exc())
                return {
                    "status": "ERROR",
                    "error": e
                }
            return {
                "status": "OK",
                "song": song.serialize_to_bytestring()
            }

        async def run_plugin_async_task(plugin_class: Type[TuneflowPlugin], song, params, job_id: str, store_uploader):
            # TODO: Revisit to see if we can call run_plugin_task directly.
            response = run_plugin_task(plugin_class=plugin_class, song=song, params=params)
            error = response["error"] if "error" in response else None
            if "error" in response:
                del response["error"]
            response["jobId"] = job_id
            store_uploader(job_id, packb(response))
            if response["status"] == "ERROR" and error is not None and exception_handler is not None:
                exception_handler(error)

        def find_plugin_by_id(plugin_class_list: List[Type[TuneflowPlugin]], provider_id, plugin_id):
            for plugin_class in plugin_class_list:
                if plugin_class.provider_id() == provider_id and plugin_class.plugin_id() == plugin_id:
                    return plugin_class
            raise Exception(f"Cannot find plugin by id {provider_id} {plugin_id}")

        def no_auth_handler():
            pass
        auth_handler = config["auth"]["handler"] if config is not None and "auth" in config and "handler" in config["auth"] else None

        @app.get(get_info_path)
        def handle_get_bundle_info():
            return self._bundle_info

        @app.post(init_plugin_path, dependencies=[Depends(auth_handler if auth_handler else no_auth_handler)])
        async def handle_init_plugin(request: Request):
            raw_body = await request.body()
            body = unpackb(raw_body)
            song = Song.deserialize_from_bytestring(body["song"])
            provider_id = body["providerId"]
            plugin_id = body["pluginId"]
            plugin_class = find_plugin_by_id(self._plugin_class_list, provider_id=provider_id, plugin_id=plugin_id)
            response = await asyncio.get_event_loop().run_in_executor(None, functools.partial(init_plugin_task, plugin_class=plugin_class, song=song))
            return Response(packb(response), headers={"Content-Type": "application/octet-stream"})

        @app.post(run_plugin_path, dependencies=[Depends(auth_handler if auth_handler else no_auth_handler)])
        async def handle_run_plugin(request: Request, background_tasks: BackgroundTasks):
            body = await request.body()
            decoded_data = unpackb(body)
            params = decoded_data["params"]
            provider_id = decoded_data["providerId"]
            plugin_id = decoded_data["pluginId"]
            plugin_class = find_plugin_by_id(self._plugin_class_list, provider_id=provider_id, plugin_id=plugin_id)
            song = Song.deserialize_from_bytestring(decoded_data["song"])
            if async_config:
                # Run in async path.
                job_id = generate_nanoid()
                background_tasks.add_task(
                    run_plugin_async_task, plugin_class=plugin_class, song=song, params=params, job_id=job_id,
                    store_uploader=async_config["store"]["uploader"])
                return Response(packb({
                    "status": "ACCEPTED",
                    "jobId": job_id,
                    "resultUrl": async_config["store"]["resultUrlResolver"](job_id)
                }), headers={"Content-Type": "application/octet-stream"})
            else:
                result = await asyncio.get_event_loop().run_in_executor(None,  functools.partial(run_plugin_task, plugin_class=plugin_class, song=song, params=params))
                if result["status"] == "ERROR" and "error" in result:
                    if exception_handler:
                        exception_handler(result["error"])
                if "error" in result:
                    del result["error"]
                return Response(packb(result), headers={"Content-Type": "application/octet-stream"})

        return app
