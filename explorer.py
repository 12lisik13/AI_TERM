import tkinter as tk
import os
import platform
from PIL import Image, ImageTk
from config import THEME

class FileBrowser(tk.Toplevel):
    """Модуль проводника: Сортировка, режимы и фильтрация по расширениям."""
    def __init__(self, parent, callback):
        super().__init__(parent)
        self.title("📂 FS_NAVIGATOR // FILTER_ENABLED")
        self.geometry("1100x800")
        self.configure(bg=THEME["bg"])
        self.callback = callback
        self.current_dir = os.getcwd()
        self.view_mode = "ICONS"
        
        # Группы фильтров
        self.filters = {
            "ALL": [],
            "IMAGES": [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"],
            "DOCS": [".txt", ".pdf", ".doc", ".docx", ".json", ".md"],
            "CODE": [".py", ".js", ".html", ".css", ".cpp", ".sh"]
        }
        self.active_filter = "ALL"
        
        self.image_refs = [] 
        self.selected_paths = {} 

        self.build_ui()
        self.update_view()
        self._bind_mouse_wheel()
        
        self.transient(parent)
        self.grab_set()

    def build_ui(self):
        # Панель навигации + фильтры
        toolbar = tk.Frame(self, bg=THEME["panel"], pady=5)
        toolbar.pack(fill=tk.X)

        self.path_entry = tk.Entry(toolbar, bg=THEME["input"], fg=THEME["ai"], 
                                   font=("JetBrains Mono", 10), relief=tk.FLAT, bd=2)
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)

        # Фрейм для кнопок фильтров
        filter_frame = tk.Frame(self, bg=THEME["bg"], pady=5)
        filter_frame.pack(fill=tk.X)
        
        tk.Label(filter_frame, text=" FILTER: ", bg=THEME["bg"], fg=THEME["sys"], font=("JetBrains Mono", 8, "bold")).pack(side=tk.LEFT, padx=5)
        
        for f_name in self.filters.keys():
            btn = tk.Button(filter_frame, text=f"[{f_name}]", 
                            command=lambda n=f_name: self.set_filter(n),
                            bg=THEME["bg"], fg=THEME["text"], relief=tk.FLAT, 
                            font=("JetBrains Mono", 8), cursor="hand2")
            btn.pack(side=tk.LEFT, padx=2)
            # Сохраним ссылку для изменения цвета активного фильтра
            if not hasattr(self, 'filter_btns'): self.filter_btns = {}
            self.filter_btns[f_name] = btn

        self.mode_btn = tk.Button(toolbar, text="[ GRID/LIST ]", command=self.toggle_mode,
                                  bg=THEME["panel"], fg=THEME["sys"], font=("JetBrains Mono", 10, "bold"), relief=tk.FLAT)
        self.mode_btn.pack(side=tk.RIGHT, padx=10)

        # Контейнер для контента
        self.container = tk.Frame(self, bg=THEME["bg"])
        self.container.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(self.container, bg=THEME["bg"], highlightthickness=0)
        self.scrollbar = tk.Scrollbar(self.container, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=THEME["bg"])

        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.bind('<Configure>', self._on_canvas_resize)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # Кнопки действия
        btn_frame = tk.Frame(self, bg=THEME["bg"], pady=10)
        btn_frame.pack(fill=tk.X)
        tk.Button(btn_frame, text="[ SELECT ]", command=self.confirm, bg=THEME["ai"], fg=THEME["bg"], font=("JetBrains Mono", 10, "bold"), padx=20, relief=tk.FLAT).pack(side=tk.RIGHT, padx=10)
        tk.Button(btn_frame, text="[ CANCEL ]", command=self.destroy, bg=THEME["panel"], fg="#fb4934", font=("JetBrains Mono", 10, "bold"), padx=20, relief=tk.FLAT).pack(side=tk.RIGHT)

    def set_filter(self, name):
        self.active_filter = name
        # Визуальный отклик
        for k, btn in self.filter_btns.items():
            btn.config(fg=THEME["ai"] if k == name else THEME["text"])
        self.update_view()

    def _on_canvas_resize(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)
        if self.view_mode == "ICONS": self.update_view()

    def _bind_mouse_wheel(self):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)

    def _on_mousewheel(self, event):
        if platform.system() == 'Linux':
            if event.num == 4: self.canvas.yview_scroll(-1, "units")
            elif event.num == 5: self.canvas.yview_scroll(1, "units")
        else: self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def toggle_mode(self):
        self.view_mode = "LIST" if self.view_mode == "ICONS" else "ICONS"
        self.update_view()

    def update_view(self):
        for widget in self.scrollable_frame.winfo_children(): widget.destroy()
        self.image_refs.clear()
        self.selected_paths.clear()
        self.path_entry.delete(0, tk.END)
        self.path_entry.insert(0, self.current_dir)

        try:
            raw_items = os.listdir(self.current_dir)
            
            # Применение фильтрации (папки всегда проходят фильтр)
            filtered_items = []
            allowed_exts = self.filters[self.active_filter]
            
            for item in raw_items:
                full_path = os.path.join(self.current_dir, item)
                if os.path.isdir(full_path):
                    filtered_items.append(item)
                elif self.active_filter == "ALL" or any(item.lower().endswith(ext) for ext in allowed_exts):
                    filtered_items.append(item)

            # Сортировка: папки первые
            items = sorted(filtered_items, key=lambda x: (not os.path.isdir(os.path.join(self.current_dir, x)), x.lower()))
            items.insert(0, "..")

            if self.view_mode == "LIST": self.render_list(items)
            else: self.render_icons(items)
        except Exception as e:
            tk.Label(self.scrollable_frame, text=f"!! ERROR: {e}", bg=THEME["bg"], fg="#fb4934").pack()

    def render_list(self, items):
        for item in items:
            full_path = os.path.join(self.current_dir, item)
            is_dir = os.path.isdir(full_path)
            row = tk.Frame(self.scrollable_frame, bg=THEME["bg"], padx=10, pady=2)
            row.pack(fill=tk.X)
            icon = "📁 " if is_dir else "📄 "
            if item == "..": icon = "⬆️ "
            lbl = tk.Label(row, text=f"{icon} {item}", bg=THEME["bg"], fg=THEME["text"], font=("Consolas", 10), anchor="w")
            lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)
            if item == "..": lbl.bind("<Double-1>", lambda e: self.change_dir(".."))
            elif is_dir: lbl.bind("<Double-1>", lambda e, p=full_path: self.change_dir(p))
            else: lbl.bind("<Button-1>", lambda e, r=row, p=full_path: self.toggle_selection(r, p))

    def render_icons(self, items):
        cell_w, cell_h = 125, 120 
        win_w = max(self.canvas.winfo_width(), 980)
        cols = max(1, win_w // cell_w)
        for i, item in enumerate(items):
            full_path = os.path.join(self.current_dir, item)
            is_dir = os.path.isdir(full_path)
            wrapper = tk.Frame(self.scrollable_frame, width=cell_w, height=cell_h, bg=THEME["bg"])
            wrapper.grid(row=i//cols, column=i%cols, padx=5, pady=5)
            wrapper.pack_propagate(False) 
            box = tk.Label(wrapper, bg=THEME["panel"], width=64, height=64, cursor="hand2")
            box.place(relx=0.5, y=40, anchor="center")
            name_text = (item[:10] + "..") if len(item) > 10 else item
            if item == "..": name_text = "BACK"
            lbl_name = tk.Label(wrapper, text=name_text, bg=THEME["bg"], fg=THEME["text"], font=("Consolas", 8), width=15)
            lbl_name.place(relx=0.5, rely=0.85, anchor="center")
            if item == "..":
                box.config(text="▲", fg=THEME["sys"], font=("JetBrains Mono", 18, "bold"))
                box.bind("<Double-1>", lambda e: self.change_dir(".."))
            elif is_dir:
                box.config(text="📁", fg=THEME["ai"], font=("Segoe UI Emoji", 24))
                box.bind("<Double-1>", lambda e, p=full_path: self.change_dir(p))
                lbl_name.bind("<Double-1>", lambda e, p=full_path: self.change_dir(p))
            else:
                if item.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.bmp')):
                    try:
                        img = Image.open(full_path); img.thumbnail((60, 60))
                        tk_img = ImageTk.PhotoImage(img); self.image_refs.append(tk_img)
                        box.config(image=tk_img)
                    except: box.config(text="🖼️", font=("Segoe UI Emoji", 24))
                else: box.config(text="📄", fg=THEME["text"], font=("Segoe UI Emoji", 24))
                box.bind("<Button-1>", lambda e, w=wrapper, p=full_path: self.toggle_selection(w, p))
                lbl_name.bind("<Button-1>", lambda e, w=wrapper, p=full_path: self.toggle_selection(w, p))

    def toggle_selection(self, frame, path):
        if path in self.selected_paths:
            del self.selected_paths[path]
            frame.config(bg=THEME["bg"])
            for child in frame.winfo_children(): child.config(bg=THEME["bg"])
        else:
            self.selected_paths[path] = frame
            frame.config(bg=THEME["highlight"])
            for child in frame.winfo_children(): child.config(bg=THEME["highlight"])

    def change_dir(self, target):
        self.current_dir = os.path.dirname(self.current_dir) if target == ".." else target
        self.update_view()

    def confirm(self):
        self.callback(list(self.selected_paths.keys()))
        self.destroy()