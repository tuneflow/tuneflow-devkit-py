from tuneflow_py import TuneflowPlugin, Song, ParamDescriptor
from typing import Dict


class HelloWorldPlugin(TuneflowPlugin):
    @staticmethod
    def provider_id() -> str:
        return "andantei"

    @staticmethod
    def plugin_id() -> str:
        return "hello-world"

    @staticmethod
    def params(song: Song) -> Dict[str, ParamDescriptor]:
        return {}
