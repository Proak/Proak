"""Run ONLY inside a running Unreal 5.8 Editor (Tools / Execute Python Script).
Prerequisite: enable Python Editor Script + Editor Scripting Utilities + glTF Importer plugin.
An exploratory editor import helper, not an executed/verified UE test.
"""
import unreal
from pathlib import Path
root=Path(__file__).resolve().parents[2]
source=root/'production'/'blockout'/'scene_01_entrance_BLOCKOUT.glb'
assert source.exists(),source
folder='/Game/Environment/Entrance_Blockout'
unreal.EditorAssetLibrary.make_directory(folder)
task=unreal.AssetImportTask()
task.set_editor_property('filename',str(source))
task.set_editor_property('destination_path',folder)
task.set_editor_property('automated',False)  # importer choice/options explicitly reviewed by human
task.set_editor_property('save',True)
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
assets=unreal.EditorAssetLibrary.list_assets(folder,recursive=True)
unreal.log('TUC imported assets: '+str(len(assets)))
for asset in assets:unreal.log(asset)
assert assets,'GLB importer produced zero assets; enable glTF Importer or use Blender FBX export.'
unreal.log_warning('Import verified at asset-list level ONLY. Place actors, check scale, collisions, materials, NavMesh and Lumen in the editor before QA pass.')
