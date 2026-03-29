import tkinter as tk
from tkinter import ttk


class SummaryPanel(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Summary")
        self.geometry("400x300")
        self.configure(bg="#1e1e1e")
        self.resizable(True, True)
        self.overrideredirect(False)
        self.attributes("-topmost", True)
        self.withdraw()

        title_label = tk.Label(
            self,
            text="Screen Summary",
            bg="#1e1e1e",
            fg="#ffffff",
            font=("Segoe UI", 11, "bold"),
            pady=8,
        )
        title_label.pack(fill=tk.X, padx=12)

        self.text_widget = tk.Text(
            self,
            bg="#2d2d2d",
            fg="#e0e0e0",
            font=("Segoe UI", 10),
            wrap=tk.WORD,
            relief=tk.FLAT,
            padx=10,
            pady=10,
            state=tk.DISABLED,
        )
        self.text_widget.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

        self.close_btn = tk.Button(
            self,
            text="Close",
            bg="#3a3a3a",
            fg="#ffffff",
            font=("Segoe UI", 9),
            relief=tk.FLAT,
            command=self.withdraw,
        )
        self.close_btn.pack(pady=(0, 10))

    def show_loading(self):
        self.set_text("Generating summary...")
        self.deiconify()
        self.lift()

    def show_summary(self, text):
        self.set_text(text)
        self.deiconify()
        self.lift()

    def set_text(self, text):
        self.text_widget.configure(state=tk.NORMAL)
        self.text_widget.delete("1.0", tk.END)
        self.text_widget.insert(tk.END, text)
        self.text_widget.configure(state=tk.DISABLED)

