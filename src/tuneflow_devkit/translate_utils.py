from locale import getlocale
from tuneflow_py import LabelText, Song


def get_system_locale():
    return getlocale()


def get_system_lang_or_default():
    current_locale: str = get_system_locale()[0]
    current_lang = current_locale.split(
        '_')[0] if current_locale is not None else 'en'
    return current_lang


def translate_label(label_text: LabelText):
    if type(label_text) is str:
        return label_text

    current_lang = get_system_lang_or_default()
    label_keys = list(label_text.keys())
    match_locales = [item.split(
        '-')[0].lower() for item in label_keys if item == current_lang]
    match_locale = match_locales[0] if len(match_locales) > 0 else None

    if match_locale is not None:
        return label_text[match_locale]  # type: ignore
    elif len(label_keys) > 0:  # type: ignore
        return label_text[label_keys[0]]  # type: ignore
    else:
        return ''
    