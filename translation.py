import bpy
import os
import importlib

translation_dict = {}


addon_dir = os.path.dirname(__file__)
locale_dir = os.path.join(addon_dir, "locale")

for lang_file in os.listdir(locale_dir):
    if lang_file.endswith(".py") and not lang_file.startswith("__"):
        lang_code = lang_file[:-3]
        try:
            module_path = "{}.locale.{}".format(__package__, lang_code)
            module = importlib.import_module(module_path)
            translation_dict.update(module.translation_dict)
        except Exception as e:
            print("❌ Failed to load translation file: {} - {}".format(lang_code, e))


def register(name):
    bpy.app.translations.unregister(name)
    bpy.app.translations.register(name, translation_dict)


def unregister(name):
    bpy.app.translations.unregister(name)
