#!/usr/bin/env python3
# main.py
import tkinter as tk
from tkinter import messagebox
import threading
import re
import json
import os
from dotenv import load_dotenv
from config import THEME, MODELS
from api_client import AIClient

class CyberApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ARCH_AI // GLOBAL_v4.2")
        self.root.geometry("1200x900")
        self.root.configure(bg=THEME["bg"])
        
        # Настройка шрифтов для кроссплатформенности [1]
        self.font_main = ("JetBrains Mono", 11)
        self.font_bold = ("JetBrains Mono", 11, "bold")
        # Проверка: если шрифта нет в Windows, используем Consolas
        if os.name == 'nt':
            self.font_main = ("Consolas", 11)
            self.font_bold = ("Consolas", 11, "bold")

        # 1. ЗАГРУЗКА И ПРОВЕРКА КЛЮЧЕЙ
        load_dotenv()
        self.check_credentials()

        self.client = AIClient()
        self.is_typing = False
        self.last_ai_response = ""
        
        # 2. ПОДГОТОВКА КЭША (Кроссплатформенные пути) [2]
        self.sessions_dir = "sessions"
        if not os.path.exists(self.sessions_dir):
            os.makedirs(self.sessions_dir)

        self.current_session = "CORE_SYSTEM"
        self.sessions = {
            "CORE_SYSTEM": {"api_hist": {"mistral": [], "gemini": []}, "visual_text": ""},
            "NEURAL_LINK": {"api_hist": {"mistral": [], "gemini": []}, "visual_text": ""},
            "DATA_ANALYSIS": {"api_hist": {"mistral": [], "gemini": []}, "visual_text": ""}
        }
        self.load_all_sessions_from_disk()
        
        self.session_buttons = {}
        self.build_ui()
        self.restore_visuals()

    def check_credentials(self):
        m_key = os.getenv("MISTRAL_API_KEY")
        g_key = os.getenv("GEMINI_API_KEY")
        if not m_key or not g_key:
            self.show_auth_window()

    def show_auth_window(self):
        auth_win = tk.Toplevel(self.root)
        auth_win.title("🔐 AUTH_REQUIRED")
        auth_win.geometry("500x350")
        auth_win.configure(bg=THEME["panel"])
        auth_win.transient(self.root)
        auth_win.grab_set()

        tk.Label(auth_win, text="[ API_KEY_INITIALIZATION ]", bg=THEME["panel"], 
                 fg=THEME["ai"], font=self.font_bold).pack(pady=20)

        tk.Label(auth_win, text="MISTRAL_API_KEY:", bg=THEME["panel"], fg=THEME["sys"]).pack()
        m_entry = tk.Entry(auth_win, bg=THEME["input"], fg="white", width=45, relief=tk.FLAT)
        m_entry.pack(pady=10, ipady=5)

        tk.Label(auth_win, text="GEMINI_API_KEY:", bg=THEME["panel"], fg=THEME["sys"]).pack()
        g_entry = tk.Entry(auth_win, bg=THEME["input"], fg="white", width=45, relief=tk.FLAT)
        g_entry.pack(pady=10, ipady=5)

        def save_keys():
            if m_entry.get() and g_entry.get():
                with open(".env", "w", encoding="utf-8") as f:
                    f.write(f"MISTRAL_API_KEY={m_entry.get()}\n")
                    f.write(f"GEMINI_API_KEY={g_entry.get()}\n")
                load_dotenv()
                auth_win.destroy()
            else:
                messagebox.showwarning("ERROR", "ALL FIELDS REQUIRED")

        tk.Button(auth_win, text="SAVE & START", command=save_keys, bg=THEME["ai"], 
                  fg=THEME["bg"], font=self.font_bold, relief=tk.FLAT, padx=20, pady=10).pack(pady=20)

    def build_ui(self):
        self.main_layout = tk.Frame(self.root, bg=THEME["bg"])
        self.main_layout.pack(fill=tk.BOTH, expand=True)

        # SIDEBAR
        self.sidebar = tk.Frame(self.main_layout, bg=THEME["panel"], width=240)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)

        tk.Label(self.sidebar, text="⚡ SYSTEM_LINK", bg=THEME["panel"], fg=THEME["sys"],
                 font=self.font_bold, pady=25).pack()

        self.session_frame = tk.Frame(self.sidebar, bg=THEME["panel"])
        self.session_frame.pack(fill=tk.BOTH, expand=True)
        
        for name in self.sessions.keys():
            btn = tk.Button(self.session_frame, text=f"> {name}", 
                            command=lambda n=name: self.switch_session(n),
                            bg=THEME["panel"], fg=THEME["text"], relief=tk.FLAT, bd=0, 
                            font=self.font_main, pady=12, anchor="w", padx=20, cursor="hand2")
            btn.pack(fill=tk.X)
            self.session_buttons[name] = btn

        # CONTENT AREA
        self.content = tk.Frame(self.main_layout, bg=THEME["bg"])
        self.content.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # HEADER
        self.header = tk.Frame(self.content, bg=THEME["panel"], height=60)
        self.header.pack(fill=tk.X, side=tk.TOP)
        self.header.pack_propagate(False)

        self.status_led = tk.Canvas(self.header, width=15, height=15, bg=THEME["panel"], highlightthickness=0)
        self.status_led.pack(side=tk.LEFT, padx=(20, 10))
        self.led_circle = self.status_led.create_oval(3, 3, 12, 12, fill=THEME["ai"], outline="")

        self.search_var = tk.BooleanVar(value=False)
        self.create_nav_btn("📡 WEB", lambda: self.search_var.set(not self.search_var.get()), THEME["ai"])
        self.create_nav_btn("[ COPY ]", self.copy_last_response, THEME["ai"])

        self.model_var = tk.StringVar(value=list(MODELS.keys())[0])
        opt_menu = tk.OptionMenu(self.header, self.model_var, *MODELS.keys())
        opt_menu.config(bg=THEME["input"], fg="white", relief=tk.FLAT)
        opt_menu.pack(side=tk.RIGHT, padx=20)

        # INPUT (SIDE=BOTTOM) - ПРИОРИТЕТ УПАКОВКИ [2]
        self.entry_frame = tk.Frame(self.content, bg=THEME["bg"], pady=20, padx=30)
        self.entry_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.entry = tk.Entry(self.entry_frame, bg=THEME["input"], fg="white", 
                              font=self.font_main, insertbackground="white", 
                              relief=tk.FLAT, highlightthickness=1,
                              highlightbackground=THEME["highlight"], highlightcolor=THEME["ai"])
        self.entry.pack(fill=tk.X, ipady=12)
        self.entry.bind("<Return>", lambda e: self.on_send())

        # CHAT (ЗАПОЛНЯЕТ ОСТАТОК)
        self.chat_container = tk.Frame(self.content, bg=THEME["bg"])
        self.chat_container.pack(fill=tk.BOTH, expand=True, padx=10)

        self.chat = tk.Text(self.chat_container, bg=THEME["bg"], fg=THEME["text"], 
                            font=self.font_main, padx=30, pady=25, 
                            spacing3=12, relief=tk.FLAT, state='disabled', wrap=tk.WORD)
        self.chat.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # ТЕГИ
        self.chat.tag_config("USER", foreground=THEME["user"], font=self.font_bold)
        self.chat.tag_config("AI", foreground=THEME["ai"], font=self.font_bold)
        self.chat.tag_config("SYS", foreground=THEME["sys"], font=self.font_main)
        self.chat.tag_config("BOLD", font=self.font_bold, foreground="white")
        self.chat.tag_config("CODE", background="#2d2d2d", foreground="#fabd2f")

        self.update_sidebar_ui()

    def load_all_sessions_from_disk(self):
        for name in self.sessions.keys():
            path = os.path.join(self.sessions_dir, f"{name}.json") # Универсальный путь [2]
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        self.sessions[name] = json.load(f)
                except: pass

    def save_session_to_disk(self, name):
        path = os.path.join(self.sessions_dir, f"{name}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.sessions[name], f, ensure_ascii=False, indent=4)

    def switch_session(self, session_name):
        if self.is_typing or session_name == self.current_session: return
        self.sessions[self.current_session]["visual_text"] = self.chat.get("1.0", tk.END)
        self.sessions[self.current_session]["api_hist"] = self.client.histories
        self.save_session_to_disk(self.current_session)
        
        self.current_session = session_name
        self.client.histories = self.sessions[session_name]["api_hist"]
        self.restore_visuals()
        self.update_sidebar_ui()

    def restore_visuals(self):
        self.chat.config(state='normal')
        self.chat.delete(1.0, tk.END)
        self.chat.insert(tk.END, self.sessions[self.current_session]["visual_text"].strip() + "\n")
        self.chat.config(state='disabled')
        self.chat.yview(tk.END)

    def create_nav_btn(self, text, cmd, color):
        tk.Button(self.header, text=text, command=cmd, bg=THEME["panel"], fg=color,
                  activebackground=THEME["input"], font=self.font_bold,
                  relief=tk.FLAT, bd=0, padx=12, cursor="hand2").pack(side=tk.LEFT, padx=5)

    def update_sidebar_ui(self):
        for name, btn in self.session_buttons.items():
            btn.config(fg=THEME["ai"] if name == self.current_session else THEME["text"],
                       bg=THEME["input"] if name == self.current_session else THEME["panel"])

    def log(self, sender, text, tag=None, animate=False):
        self.chat.config(state='normal')
        current_tag = tag if tag else ("USER" if sender == "YOU" else "AI")
        self.chat.insert(tk.END, f"\n @ {sender} > ", current_tag)
        if animate:
            self.is_typing = True
            self.typewriter_effect(text, 0)
        else:
            self.parse_markdown(text)
            self.finalize_log()

    def typewriter_effect(self, text, index):
        if index < len(text):
            self.chat.config(state='normal')
            self.chat.insert(tk.END, text[index])
            self.chat.config(state='disabled')
            self.chat.yview(tk.END)
            self.root.after(15, lambda: self.typewriter_effect(text, index + 1))
        else:
            self.is_typing = False
            self.finalize_log()

    def parse_markdown(self, text):
        chunks = re.split(r'(```.*?```)', text, flags=re.DOTALL)
        for chunk in chunks:
            if chunk.startswith('```'):
                self.chat.insert(tk.END, f"\n{chunk.strip('`').strip()}\n", "CODE")
            else:
                parts = re.split(r'(\*\*.*?\*\*)', chunk)
                for part in parts:
                    if part.startswith('**'):
                        self.chat.insert(tk.END, part[2:-2], "BOLD")
                    else:
                        self.chat.insert(tk.END)

    def finalize_log(self):
        self.chat.insert(tk.END, "\n")
        self.chat.config(state='disabled')
        self.chat.yview(tk.END)
        self.sessions[self.current_session]["visual_text"] = self.chat.get("1.0", tk.END)
        self.save_session_to_disk(self.current_session)

    def on_send(self):
        if self.is_typing: return
        msg = self.entry.get().strip()
        if not msg: return
        self.log("YOU", msg)
        self.entry.delete(0, tk.END)
        self.status_led.itemconfig(self.led_circle, fill="#fabd2f")
        threading.Thread(target=self.run_ai, args=(msg, self.search_var.get()), daemon=True).start()

    def run_ai(self, msg, search_on):
        label = self.model_var.get()
        prov, mid = MODELS[label]
        ans = self.client.call_gemini(mid, msg, search_on) if prov == "gemini" else self.client.call_mistral(mid, msg, search_on)
        self.last_ai_response = ans
        self.root.after(0, lambda: self.finish(label, ans))

    def finish(self, sender, ans):
        self.log(sender.split()[0].upper(), ans, animate=True)
        self.status_led.itemconfig(self.led_circle, fill=THEME["ai"])

    def copy_last_response(self):
        if self.last_ai_response:
            self.root.clipboard_clear()
            self.root.clipboard_append(self.last_ai_response)
            messagebox.showinfo("SYSTEM", "RESPONSE_COPIED")

if __name__ == "__main__":
    root = tk.Tk()
    app = CyberApp(root)
    root.mainloop()