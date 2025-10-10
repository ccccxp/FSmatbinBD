import tkinter as tk
from src.gui.main_window import MaterialDatabaseApp

root = tk.Tk()
app = MaterialDatabaseApp(root)
root.update()
print('winfo_exists:', root.winfo_exists())
print('winfo_viewable:', root.winfo_viewable())
print('winfo_ismapped:', root.winfo_ismapped())
print('geometry:', root.winfo_geometry())
print('children:', [type(c).__name__ for c in root.winfo_children()])
root.destroy()
