import tkinter as tk
from gui_app import SolanaMarketGui

if __name__ == "__main__":
    root = tk.Tk()
    app = SolanaMarketGui(root)
    root.geometry("800x650")
    root.mainloop()
