import bpy
import os
import importlib
from .languages import LANGUAGES_LIST


def register():

    translation_dict = {}

    addon_dir = os.path.dirname(__file__)
    languages_dir = os.path.join(addon_dir, "languages")

    for lang_code in LANGUAGES_LIST:
        lang_file = os.path.join(languages_dir, "{}.py".format(lang_code))
        if not os.path.isfile(lang_file):
            continue
        try:
            module_path = "{}.languages.{}".format(__package__, lang_code)
            module = importlib.import_module(module_path)
            translation_dict.update(module.translation_dict)
        except Exception as e:
            print("❌ Failed to load translation file: {} - {}".format(lang_code, e))

    bpy.app.translations.unregister(__name__)
    bpy.app.translations.register(__name__, translation_dict)


def unregister():
    bpy.app.translations.unregister(__name__)
