import sys, traceback
root = r"c:\Users\Administrator\Desktop\材质库\材质库查询\matbinSQL"
if root not in sys.path:
    sys.path.insert(0, root)
modules = [
    'src.gui.main_window',
    'src.gui.library_panel',
    'src.gui.material_panel',
    'src.gui.sampler_panel',
    'src.gui.material_list_panel',
    'src.gui.library_manager_dialog',
    'src.core.i18n'
]
results = {}
for m in modules:
    try:
        import importlib
        importlib.reload(importlib.import_module(m))
        results[m] = 'OK'
    except Exception as e:
        results[m] = 'ERROR:\n' + ''.join(traceback.format_exception(type(e), e, e.__traceback__))

for k,v in results.items():
    print(f"{k}: {v}\n")
