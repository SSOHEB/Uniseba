import tkinter as tk


class SummaryPanel(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Summary")
        self.configure(bg="#0d1117")
        self.overrideredirect(False)
        self.attributes("-topmost", True)

        width = 560
        height = 500
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = (screen_w - width) // 2
        y = (screen_h - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.protocol("WM_DELETE_WINDOW", self.withdraw)
        self.withdraw()

        header = tk.Frame(self, bg="#161b22", height=48)
        header.pack(side=tk.TOP, fill=tk.X)
        header.pack_propagate(False)

        accent = tk.Frame(header, bg="#00d4ff", width=3)
        accent.pack(side=tk.LEFT, fill=tk.Y)

        header_label = tk.Label(
            header,
            text="✦ Screen Intelligence",
            fg="#e6edf3",
            bg="#161b22",
            font=("Segoe UI", 11, "bold"),
            padx=12,
        )
        header_label.pack(side=tk.LEFT)

        separator = tk.Frame(self, bg="#21262d", height=1)
        separator.pack(side=tk.TOP, fill=tk.X)

        self.text_widget = tk.Text(
            self,
            bg="#0d1117",
            fg="#c9d1d9",
            font=("Segoe UI", 11),
            wrap=tk.WORD,
            relief=tk.FLAT,
            padx=20,
            pady=16,
            selectbackground="#1f6feb",
            state=tk.DISABLED,
        )
        self.text_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        bottom_bar = tk.Frame(self, bg="#161b22", height=44)
        bottom_bar.pack(side=tk.BOTTOM, fill=tk.X)
        bottom_bar.pack_propagate(False)

        dismiss_btn = tk.Button(
            bottom_bar,
            text="Dismiss",
            bg="#21262d",
            fg="#8b949e",
            font=("Segoe UI", 9),
            relief=tk.FLAT,
            activebackground="#30363d",
            activeforeground="#e6edf3",
            command=self.withdraw,
            padx=16,
            pady=4,
        )
        dismiss_btn.pack(side=tk.RIGHT, padx=12, pady=8)

    def show_loading(self):
        self.set_text("⟳  Generating intelligence...")
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
