from locale import getlocale
from tuneflow_py import ReadAPIs, LabelText, Song


def get_system_locale():
    return getlocale()


def translate_label(label_text: LabelText):
    if type(label_text) is str:
        return label_text

    current_locale = get_system_locale()[0]
    label_keys = list(label_text.keys())
    match_locales = [item.split(
        '-')[0].lower() for item in label_keys if item == current_locale]
    match_locale = match_locales[0] if len(match_locales) > 0 else None

    if match_locale is not None:
        return label_text[match_locale]  # type: ignore
    elif len(label_keys) > 0:  # type: ignore
        return label_text[label_keys[0]]  # type: ignore
    else:
        return ''


def serialize_song(song: Song):
    return song.serialize()


def deserialize_song(encoded_song: str):
    return Song.deserialize(encoded_song)
