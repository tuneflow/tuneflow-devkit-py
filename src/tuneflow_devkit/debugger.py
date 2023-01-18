import socketio
import uvicorn
from tuneflow_py import TuneflowPlugin, Song, LabelText, ReadAPIs
from typing import Type
from locale import getlocale
import traceback


class Debugger:
    def __init__(self, plugin_class: Type[TuneflowPlugin]) -> None:
        if plugin_class is None:
            raise Exception("plugin_class must be provided")
        self._serialized_song: str | None = None
        self._plugin: TuneflowPlugin | None = None
        self._plugin_class = plugin_class
        self._daw_sid: None | str = None
        self._sio: None | socketio.AsyncServer = None
        self.port = 18818

    def start(self):
        # create a Socket.IO server
        sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
        self._sio = sio

        def handle_connect(sid, environ, auth):
            self._daw_sid = sid
            print("new daw connection")

        def handle_disconnect(sid):
            self._daw_sid = None
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
                self._plugin = self._plugin_class.create(
                    song, self.create_read_apis())
            except Exception as e:
                print("================ Run Plugin Exception ================")
                traceback.print_exc()
                print("======================================================")
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
                self._plugin.run(song, params, self.create_read_apis())
            except Exception as e:
                print("================ Run Plugin Exception ================")
                traceback.print_exc()
                print("======================================================")
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

    @staticmethod
    def get_system_locale():
        return getlocale()

    def create_read_apis(self) -> ReadAPIs:
        def translate_label(label_text: LabelText):
            if type(label_text) is str:
                return label_text

            current_locale = Debugger.get_system_locale()[0]
            match_locales = [item.split(
                '-')[0].lower() for item in label_text.keys() if item == current_locale]
            match_locale = match_locales[0] if len(match_locales) > 0 else None

            if match_locale is not None:
                return label_text[match_locale]  # type: ignore
            elif len(label_text.keys()) > 0:  # type: ignore
                return label_text[label_text.keys()[0]]  # type: ignore
            else:
                return ''

        def serialize_song(song: Song):
            return song.serialize()

        def deserialize_song(encoded_song: str):
            return Song.deserialize(encoded_song)

        async def get_available_audio_plugins():
            response = None

            def handle_get_audio_plugins_callback(sid, data):
                response = data
            await self._sio.emit(event='getAvailableAudioPlugins', data=None, to=self._daw_sid, callback=handle_get_audio_plugins_callback)
            return response

        return {
            "translate_label": translate_label,
            "serialize_song": serialize_song,
            "deserialize_song": deserialize_song,
            "get_available_audio_plugins": get_available_audio_plugins
        }
