import bpy

def get_preferences():
    return bpy.context.preferences.addons[__package__].preferences

PADDING_AUTO = {
    "512": 4,
    "1024": 8,
    "2048": 16,
    "4096": 32,
    "8192": 64,
}