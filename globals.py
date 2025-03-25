import bpy

def get_preferences():
    return bpy.context.preferences.addons[__package__].preferences