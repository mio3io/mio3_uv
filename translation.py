import bpy
import os
import importlib

translation_dict = {}


addon_dir = os.path.dirname(__file__)
languages_dir = os.path.join(addon_dir, "languages")

for lang_file in os.listdir(languages_dir):
    if lang_file.endswith(".py") and not lang_file.startswith("__"):
        lang_code = lang_file[:-3]
        try:
            module_path = "{}.languages.{}".format(__package__, lang_code)
            module = importlib.import_module(module_path)
            translation_dict.update(module.translation_dict)
        except Exception as e:
            print("❌ Failed to load translation file: {} - {}".format(lang_code, e))


def register():
    bpy.app.translations.unregister(__name__)
    bpy.app.translations.register(__name__, translation_dict)


def unregister():
    bpy.app.translations.unregister(__name__)
