import socketio
import eventlet
from tuneflow_py import TuneflowPlugin, Song, LabelText, ReadAPIs
from typing import Type
import traceback
from tuneflow_devkit.read_api_utils import serialize_song, deserialize_song, translate_label


class Debugger:
    def __init__(self, plugin_class: Type[TuneflowPlugin]) -> None:
        if plugin_class is None:
            raise Exception("plugin_class must be provided")
        self._serialized_song: str | None = None
        self._plugin: TuneflowPlugin | None = None
        self._plugin_class = plugin_class
        self._daw_sid: None | str = None
        self._sio: None | socketio.Server = None
        self.port = 18818

    def start(self):
        # create a Socket.IO server
        sio = socketio.Server(async_mode='eventlet', cors_allowed_origins='*')
        self._sio = sio

        def handle_connect(sid, environ, auth):
            self._daw_sid = sid
            print(
                "===========================================================================")
            print("TuneFlow connected")
            print(
                "===========================================================================")

        def handle_disconnect(sid):
            self._daw_sid = None
            print(
                "===========================================================================")
            print("TuneFlow disconnected")
            print()
            print(translate_label({
                "en": "IMPORTANT: Please undo the \"Pluign Development\" plugin and re-run it after you restart the DevKit.",
                "zh": "注意: 请在TuneFlow中退出\"插件开发\"插件，并在DevKit重新启动后重新运行该插件"
            }))
            print(
                "===========================================================================")

        def handle_set_song(sid, data):
            print('receiving a new song')
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

        def handle_init_plugin(sid, data):
            print('init plugin')
            if self._serialized_song is None:
                return {"status": "SONG_OR_PLUGIN_NOT_READY"}
            song = Song.deserialize(self._serialized_song)
            try:
                self._plugin = self._plugin_class.create(
                    song, self.create_read_apis())
            except Exception as e:
                print(
                    "=========================== Run Plugin Exception ==========================")
                traceback.print_exc()
                print(
                    "===========================================================================")
                return {
                    "status": "INIT_PLUGIN_EXCEPTION"
                }
            return {"status": "OK",
                    "paramsConfig": self._plugin.params(),
                    "params": self._plugin.params_result_internal
                    }

        def handle_run_plugin(sid, data):
            print('run plugin')
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
        self._app = socketio.WSGIApp(self._sio)
        self.print_plugin_info(plugin_class=self._plugin_class)
        print()
        print("======================================================")
        print(translate_label({
            "en": "IMPORTANT: Run \"Plugin Development\" Plugin from TuneFlow plugin inventory to run this plugin.",
            "zh": "注意: 运行TuneFlow插件仓库中的\"插件开发\"插件即可开始调试本插件"
        }))
        print("======================================================")
        eventlet.wsgi.server(eventlet.listen(
            ('127.0.0.1', self.port)), self._app)

    def create_read_apis(self) -> ReadAPIs:
        def get_available_audio_plugins():
            if self._sio is None:
                raise Exception('Debugger not connected yet.')
            return self._sio.call(event='call-api', namespace="/daw", data=["getAvailableAudioPlugins"], to=self._daw_sid)

        class ReadAPIsImpl(ReadAPIs):
            def translate_label(self, label_text: LabelText):
                return translate_label(label_text=label_text)

            def serialize_song(self, song: Song):
                return serialize_song(song=song)

            def deserialize_song(self, encoded_song: str):
                return deserialize_song(encoded_song=encoded_song)

            def get_available_audio_plugins(self):
                return get_available_audio_plugins()
        return ReadAPIsImpl()

    @staticmethod
    def print_plugin_info(plugin_class: Type[TuneflowPlugin]):
        print(translate_label(
            {"en": "============= Plugin Info =============",
             "zh": "=============== 插件信息 ==============="}))
        print("Provider ID:", plugin_class.provider_id())
        print("Provider Name:", translate_label(
            plugin_class.provider_display_name()))
        print("Plugin ID:", plugin_class.plugin_id())
        print("Plugin Name:", translate_label(
            plugin_class.plugin_display_name()))
        plugin_description = plugin_class.plugin_description()
        print("Plugin Description:", translate_label(plugin_description)
              if plugin_description is not None else 'None')
        print("=======================================")
