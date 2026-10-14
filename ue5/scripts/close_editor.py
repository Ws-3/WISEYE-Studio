import unreal
assert unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True), 'Save failed; editor stays open'
unreal.SystemLibrary.quit_editor()
