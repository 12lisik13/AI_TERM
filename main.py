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
        self.root.title("AI_TERM // CORE_v1.0")
        self.root.geometry("1150x850")
        self.root.configure(bg=THEME["bg"])
        
        # Кроссплатформенные шрифты [1]
        self.font_main = ("JetBrains Mono", 11)
        self.font_bold = ("JetBrains Mono", 11, "bold")
        if os.name == 'nt': 
            self.font_main = ("Consolas", 11)
            self.font_bold = ("Consolas", 11, "bold")

        load_dotenv()
        self.check_credentials()

        self.client = AIClient()
        self.is_typing = False
        self.last_ai_response = ""
        
        # Работа с директорией сессий [2]
        self.sessions_dir = os.path.abspath("sessions")
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
        if not os.getenv("MISTRAL_API_KEY") or not os.getenv("GEMINI_API_KEY"):
            self.show_auth_window()

    def show_auth_window(self):
        auth_win = tk.Toplevel(self.root)
        auth_win.title("🔐 AUTH_REQUIRED")
        auth_win.geometry("450x320")
        auth_win.configure(bg=THEME["panel"])
        auth_win.transient(self.root)
        auth_win.grab_set()

        tk.Label(auth_win, text="[ API_KEY_INITIALIZATION ]", bg=THEME["panel"], 
                 fg=THEME["ai"], font=self.font_bold).pack(pady=15)

        tk.Label(auth_win, text="MISTRAL_API_KEY:", bg=THEME["panel"], fg=THEME["sys"]).pack()
        m_entry = tk.Entry(auth_win, bg=THEME["input"], fg="white", width=40, relief=tk.FLAT)
        m_entry.pack(pady=5, ipady=3)

        tk.Label(auth_win, text="GEMINI_API_KEY:", bg=THEME["panel"], fg=THEME["sys"]).pack()
        g_entry = tk.Entry(auth_win, bg=THEME["input"], fg="white", width=40, relief=tk.FLAT)
        g_entry.pack(pady=5, ipady=3)

        def save():
            with open(".env", "w", encoding="utf-8") as f:
                f.write(f"MISTRAL_API_KEY={m_entry.get().strip()}\nGEMINI_API_KEY={g_entry.get().strip()}")
            load_dotenv()
            auth_win.destroy()

        tk.Button(auth_win, text="SAVE & START", command=save, bg=THEME["ai"], fg=THEME["bg"], 
                  font=self.font_bold, padx=20, pady=5).pack(pady=20)

    def build_ui(self):
        self.main_layout = tk.Frame(self.root, bg=THEME["bg"])
        self.main_layout.pack(fill=tk.BOTH, expand=True)

        # 1. SIDEBAR
        self.sidebar = tk.Frame(self.main_layout, bg=THEME["panel"], width=220)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)

        tk.Label(self.sidebar, text="⚡ AI_TERM", bg=THEME["panel"], fg=THEME["sys"],
                 font=self.font_bold, pady=20).pack()

        for name in self.sessions.keys():
            btn = tk.Button(self.sidebar, text=f"> {name}", 
                            command=lambda n=name: self.switch_session(n),
                            bg=THEME["panel"], fg=THEME["text"], relief=tk.FLAT, bd=0, 
                            font=self.font_main, pady=10, anchor="w", padx=20, cursor="hand2")
            btn.pack(fill=tk.X)
            self.session_buttons[name] = btn

        # 2. CONTENT AREA
        self.content = tk.Frame(self.main_layout, bg=THEME["bg"])
        self.content.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # 3. HEADER
        self.header = tk.Frame(self.content, bg=THEME["panel"], height=55)
        self.header.pack(fill=tk.X, side=tk.TOP)
        self.header.pack_propagate(False)

        self.status_led = tk.Canvas(self.header, width=12, height=12, bg=THEME["panel"], highlightthickness=0)
        self.status_led.pack(side=tk.LEFT, padx=(20, 10))
        self.led_circle = self.status_led.create_oval(2, 2, 10, 10, fill=THEME["ai"], outline="")

        # КНОПКИ УПРАВЛЕНИЯ
        self.search_var = tk.BooleanVar(value=False)
        def toggle_web():
            is_on = not self.search_var.get()
            self.search_var.set(is_on)
            web_btn.config(fg=THEME["ai"] if is_on else THEME["sys"])

        web_btn = tk.Button(self.header, text="📡 WEB", command=toggle_web, 
                            bg=THEME["panel"], fg=THEME["sys"], font=self.font_bold,
                            relief=tk.FLAT, bd=0, padx=12, cursor="hand2")
        web_btn.pack(side=tk.LEFT, padx=5)

        tk.Button(self.header, text="[ COPY ]", command=self.copy_last, 
                  bg=THEME["panel"], fg=THEME["sys"], font=self.font_bold,
                  relief=tk.FLAT, bd=0, padx=12, cursor="hand2").pack(side=tk.LEFT)

        tk.Button(self.header, text="[ CLEAR ]", command=self.clear_session, 
                  bg=THEME["panel"], fg="#fb4934", font=self.font_bold,
                  relief=tk.FLAT, bd=0, padx=12, cursor="hand2").pack(side=tk.LEFT, padx=5)

        # ВЫБОР МОДЕЛИ
        self.model_var = tk.StringVar(value=list(MODELS.keys())[0])
        self.model_menu = tk.OptionMenu(self.header, self.model_var, *MODELS.keys())
        self.model_menu.config(bg=THEME["input"], fg="white", relief=tk.FLAT, font=self.font_main, bd=0)
        self.model_menu["menu"].config(bg=THEME["panel"], fg="white", font=self.font_main)
        self.model_menu.pack(side=tk.RIGHT, padx=20)

        # 4. INPUT AREA
        self.entry_frame = tk.Frame(self.content, bg=THEME["bg"], pady=15, padx=20)
        self.entry_frame.pack(side=tk.BOTTOM, fill=tk.X)

        self.entry = tk.Entry(self.entry_frame, bg=THEME["input"], fg="white", 
                              font=self.font_main, insertbackground="white", 
                              relief=tk.FLAT, highlightthickness=1,
                              highlightbackground=THEME["highlight"], highlightcolor=THEME["ai"])
        self.entry.pack(fill=tk.X, ipady=10)
        self.entry.bind("<Return>", lambda e: self.on_send())

        # 5. CHAT VIEW
        self.chat = tk.Text(self.content, bg=THEME["bg"], fg=THEME["text"], 
                            font=self.font_main, padx=25, pady=20, 
                            spacing3=10, relief=tk.FLAT, state='disabled', wrap=tk.WORD)
        self.chat.pack(fill=tk.BOTH, expand=True)
        
        self.chat.tag_config("USER", foreground=THEME["user"], font=self.font_bold)
        self.chat.tag_config("AI", foreground=THEME["ai"], font=self.font_bold)
        self.chat.tag_config("BOLD", font=self.font_bold, foreground="white")
        self.chat.tag_config("CODE", background="#2d2d2d", foreground="#fabd2f")

    def on_send(self):
        if self.is_typing: return
        msg = self.entry.get().strip()
        if not msg: return

        self.entry.delete(0, tk.END)
        self.log("YOU", msg, tag="USER")
        
        self.status_led.itemconfig(self.led_circle, fill="#fabd2f")
        threading.Thread(target=self.run_ai, args=(msg, self.model_var.get(), self.search_var.get()), daemon=True).start()

    def run_ai(self, msg, label, search_on):
        try:
            prov, mid = MODELS[label]
            ans = self.client.call_gemini(mid, msg, search_on) if prov == "gemini" else self.client.call_mistral(mid, msg)
            self.last_ai_response = ans
            self.root.after(0, lambda: self.finish_ai(label, ans))
        except Exception as e:
            self.root.after(0, lambda: self.log("SYS_ERROR", str(e)))

    def finish_ai(self, label, ans):
        self.status_led.itemconfig(self.led_circle, fill=THEME["ai"])
        self.log(label.split()[0].upper(), ans, animate=True)

    def log(self, sender, text, tag=None, animate=False):
        self.chat.config(state='normal')
        self.chat.insert(tk.END, f"\n @ {sender} > ", tag if tag else "AI")
        if animate:
            self.is_typing = True
            self._typewriter(text, 0)
        else:
            self._insert_markdown(text)
            self._finalize()

    def _typewriter(self, text, i):
        if i < len(text):
            self.chat.config(state='normal')
            self.chat.insert(tk.END, text[i])
            self.chat.config(state='disabled')
            self.chat.yview(tk.END)
            self.root.after(8, lambda: self._typewriter(text, i + 1))
        else:
            self.is_typing = False
            self._finalize()

    def _insert_markdown(self, text):
        parts = re.split(r'(\*\*.*?\*\*)', text)
        for part in parts:
            if part.startswith('**') and part.endswith('**'):
                self.chat.insert(tk.END, part[2:-2], "BOLD")
            else:
                self.chat.insert(tk.END, part)

    def _finalize(self):
        self.chat.insert(tk.END, "\n")
        self.chat.config(state='disabled')
        self.chat.yview(tk.END)
        self.save_session_to_disk(self.current_session)

    def copy_last(self):
        if self.last_ai_response:
            self.root.clipboard_clear()
            self.root.clipboard_append(self.last_ai_response)
            messagebox.showinfo("SYSTEM", "RESPONSE_COPIED")

    def clear_session(self):
        if messagebox.askyesno("SYSTEM", "Очистить историю этой сессии?"):
            self.client.histories = {"mistral": [], "gemini": []}
            self.chat.config(state='normal')
            self.chat.delete(1.0, tk.END)
            self.chat.config(state='disabled')
            self.sessions[self.current_session]["visual_text"] = ""
            self.sessions[self.current_session]["api_hist"] = {"mistral": [], "gemini": []}
            self.save_session_to_disk(self.current_session)

    def load_all_sessions_from_disk(self):
        for name in self.sessions.keys():
            path = os.path.join(self.sessions_dir, f"{name}.json")
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        self.sessions[name] = json.load(f)
                except: pass

    def save_session_to_disk(self, name):
        self.sessions[name]["visual_text"] = self.chat.get("1.0", tk.END)
        self.sessions[name]["api_hist"] = self.client.histories
        path = os.path.join(self.sessions_dir, f"{name}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.sessions[name], f, ensure_ascii=False, indent=4)

    def switch_session(self, name):
        if self.is_typing or name == self.current_session: return
        self.save_session_to_disk(self.current_session)
        self.current_session = name
        self.client.histories = self.sessions[name]["api_hist"]
        self.restore_visuals()

    def restore_visuals(self):
        self.chat.config(state='normal')
        self.chat.delete(1.0, tk.END)
        self.chat.insert(tk.END, self.sessions[self.current_session]["visual_text"])
        self.chat.config(state='disabled')
        self.chat.yview(tk.END)

if __name__ == "__main__":
    root = tk.Tk()
    app = CyberApp(root)
    root.mainloop()