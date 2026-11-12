"""Runs inside Unreal. Saves only the assets under /Game/AgoraChar/Tripo/Hero01."""
import unreal

lib = unreal.EditorAssetLibrary
for a in lib.list_assets("/Game/AgoraChar/Tripo/Hero01", recursive=True):
    path = str(a).split(".")[0]
    print(path, lib.save_asset(path, only_if_is_dirty=True))
