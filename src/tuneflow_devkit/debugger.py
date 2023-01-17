import socketio
import uvicorn
from tuneflow_py import TuneflowPlugin, Song
from typing import Type


class Debugger:
    def __init__(self, plugin_class: Type[TuneflowPlugin]) -> None:
        if plugin_class is None:
            raise Exception("plugin_class must be provided")
        self._serialized_song: str | None = None
        self._plugin: TuneflowPlugin | None = None
        self._plugin_class = plugin_class
        self.port = 18818

    def start(self):
        # create a Socket.IO server
        sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')

        def handle_connect(sid, environ, auth):
            print("new daw connection")

        def handle_disconnect(sid):
            print("daw disconnected")

        async def handle_set_song(sid, data):
            self._serialized_song = data["serializedSong"]
            self._plugin = None
            return {
                "status": "OK",
                "pluginInfo": {
                    "pluginDisplayName": self._plugin_class.plugin_display_name(),
                    "pluginDescription": self._plugin_class.plugin_description(),
                    "providerDisplayName": self._plugin_class.provider_display_name()
                }
            }

        async def handle_init_plugin(sid, data):
            if self._serialized_song is None:
                return {"status": "SONG_OR_PLUGIN_NOT_READY"}
            song = Song.deserialize(self._serialized_song)
            try:
                self._plugin = self._plugin_class.create(song)
            except Exception as e:
                print("Init plugin exception:", e)
                return {
                    "status": "INIT_PLUGIN_EXCEPTION"
                }
            return {"status": "OK",
                    "paramsConfig": self._plugin.params(),
                    "params": self._plugin.params_result_internal
                    }

        async def handle_run_plugin(sid, data):
            if self._plugin is None or self._serialized_song is None:
                return {"status": "SONG_OR_PLUGIN_NOT_READY"}
            params = data["params"]
            song = Song.deserialize(self._serialized_song)
            try:
                self._plugin.run(song, params)
            except Exception as e:
                print("Run plugin exception:", e)
                return {
                    "status": "RUN_PLUGIN_EXCEPTION"
                }
            return {
                "status": "OK",
                "serializedSongResult": song.serialize()
            }

        sio.on("connect", handle_connect, namespace='/daw')
        sio.on("disconnect", handle_disconnect, namespace='/daw')
        sio.on('set-song', handle_set_song, namespace='/daw')
        sio.on('init-plugin', handle_init_plugin, namespace='/daw')
        sio.on('run-plugin', handle_run_plugin, namespace='/daw')

        self._sio = sio

        # Wrap with ASGI application
        self._app = socketio.ASGIApp(self._sio)
        uvicorn.run(self._app, host='127.0.0.1', port=self.port)
