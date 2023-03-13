from __future__ import annotations
import socketio
import uvicorn
from tuneflow_py import TuneflowPlugin, Song
from typing import Type
import traceback
from tuneflow_devkit.translate_utils import translate_label
import asyncio
import functools
import json
from tuneflow_devkit.validation_utils import validate_plugin, find_match_plugin_info
from msgpack import unpackb, packb


class Debugger:
    def __init__(self, plugin_class: Type[TuneflowPlugin], bundle_file_path: str) -> None:
        '''
        Creates a local debug server for a single plugin.
        '''

        if plugin_class is None or bundle_file_path is None:
            raise Exception("plugin_class and bundle_file must be provided")
        validate_plugin(plugin_class=plugin_class)
        self._plugin_class = plugin_class
        with open(bundle_file_path, 'r') as bundle_file:
            bundle_info = json.load(bundle_file)
            # Validate plugin and bundle.
            plugin_info = find_match_plugin_info(
                bundle_info=bundle_info, provider_id=plugin_class.provider_id(),
                plugin_id=plugin_class.plugin_id())
            if plugin_info is None:
                raise Exception(
                    "plugin not specified in the bundle, check your bundle.json. For more information checkout https://github.com/tuneflow/tuneflow-py")
            self._plugin_info = plugin_info

        self._daw_sid: None | str = None
        self._sio: None | socketio.AsyncServer = None
        self.port = 18818

    def start(self):
        # create a Socket.IO server
        # Maximum http buffer size set to 100MB.
        sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*', max_http_buffer_size=1e8)
        self._sio = sio

        async def handle_connect(sid, environ, auth):
            self._daw_sid = sid
            print(
                "===========================================================================")
            print("TuneFlow connected")
            print(
                "===========================================================================")

        async def handle_disconnect(sid):
            self._daw_sid = None
            print(
                "===========================================================================")
            print("TuneFlow disconnected")
            print()
            print(translate_label({
                "en": "IMPORTANT: Please undo the plugin under debugging and re-run it after you restart the DevKit.",
                "zh": "注意: 请在TuneFlow中撤销正在调试的插件，并在DevKit重新启动后重新运行该插件"
            }))
            print(
                "===========================================================================")

        async def handle_get_bundle_info(sid, data):
            return {
                "status": "OK",
                "pluginInfo": self._plugin_info
            }

        def init_plugin_task(plugin_class: Type[TuneflowPlugin], song: Song, sio, sid):
            try:
                params_config = plugin_class.params(song)
                return {"status": "OK",
                        "paramsConfig": params_config,
                        "params": plugin_class._get_default_params(param_config=params_config)
                        }
            except Exception as e:
                print(
                    "=========================== Run Plugin Exception ==========================")
                traceback.print_exc()
                print(
                    "===========================================================================")
                return {
                    "status": "INIT_PLUGIN_EXCEPTION"
                }

        async def handle_init_plugin(sid, data):
            decoded_data = unpackb(data)
            song = Song.deserialize_from_bytestring(decoded_data["song"])
            response = await asyncio.get_event_loop().run_in_executor(None, functools.partial(init_plugin_task, plugin_class=self._plugin_class, song=song, sio=self._sio, sid=self._daw_sid))
            return packb(response)

        def run_plugin_task(plugin_class: Type[TuneflowPlugin], song, params, sio, sid):
            try:
                plugin_class.run(song, params)
            except Exception as e:
                print("================ Run Plugin Exception ================")
                traceback.print_exc()
                print("======================================================")
                return {
                    "status": "RUN_PLUGIN_EXCEPTION"
                }
            return {
                "status": "OK",
                "song": song.serialize_to_bytestring()
            }

        async def handle_run_plugin(sid, data):
            print('run plugin')
            decoded_data = unpackb(data)
            params = decoded_data["params"]
            song = Song.deserialize_from_bytestring(decoded_data["song"])
            result = await asyncio.get_event_loop().run_in_executor(None,  functools.partial(run_plugin_task, plugin_class=self._plugin_class, song=song, params=params, sio=self._sio, sid=self._daw_sid))
            return packb(result)

        sio.on("connect", handle_connect, namespace='/daw')
        sio.on("disconnect", handle_disconnect, namespace='/daw')
        sio.on('get-bundle-info', handle_get_bundle_info, namespace='/daw')
        sio.on('init-plugin', handle_init_plugin, namespace='/daw')
        sio.on('run-plugin', handle_run_plugin, namespace='/daw')

        self._sio = sio

        # Wrap with ASGI application
        self._app = socketio.ASGIApp(self._sio)
        self.print_plugin_info(plugin_info=self._plugin_info)
        print()
        print("======================================================")
        print(translate_label({
            "en": "IMPORTANT: Install this plugin in debug mode from the TuneFlow plugin library panel, then run this plugin from the right-click menu specified in the triggers",
            "zh": "注意: 从 TuneFlow 库中以debug模式安装此插件，随后即可从各级右键菜单中运行此插件"
        }))
        print("======================================================")
        uvicorn.run(self._app, host='127.0.0.1', port=self.port)

    @staticmethod
    def print_plugin_info(plugin_info):
        print(translate_label(
            {"en": "============= Plugin Info =============",
             "zh": "=============== 插件信息 ==============="}))
        print("Provider ID:", plugin_info["providerId"])
        print("Provider Name:", translate_label(
            plugin_info["providerDisplayName"]))
        print("Plugin ID:", plugin_info["pluginId"])
        print("Plugin Name:", translate_label(
            plugin_info["pluginDisplayName"]))
        plugin_description = plugin_info["pluginDescription"]
        print("Plugin Description:", translate_label(plugin_description)
              if plugin_description is not None else 'None')
        print("=======================================")
