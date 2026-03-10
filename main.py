#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk
import threading
import json
import os
import re
import tempfile
import whisper
import speech_recognition as sr
from PIL import Image, ImageTk 
from tkinterdnd2 import DND_FILES, TkinterDnD 
from dotenv import load_dotenv

# Импорт ваших модулей
from config import THEME, MODELS
from api_client import AIClient
from explorer import FileBrowser

class CyberApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI_TERM // CORE_v4.3")
        self.root.geometry("1250x900")
        self.root.configure(bg=THEME["bg"])
        
        load_dotenv()
        self.client = AIClient()
        
        print("Loading Whisper Model...")
        self.whisper_model = whisper.load_model("base")
        
        self.is_recording = False
        self.record_limit = 30
        self.elapsed = 0
        
        self.attached_files = [] 
        self.image_refs = []    # Кэш для фото в чате
        self.preview_refs = []  # Кэш для иконок в панели ввода
        
        self.session_buttons = {} 
        self.sessions_dir = "sessions"
        if not os.path.exists(self.sessions_dir): os.makedirs(self.sessions_dir)
        
        self.current_session = "CORE_SYSTEM"
        self.sessions = {name: {"visual_text": "", "pending": False} for name in ["CORE_SYSTEM", "NEURAL_LINK", "DATA_ANALYSIS"]}
        
        self.load_all_sessions_from_disk()
        self.build_ui()
        
        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind('<<Drop>>', self.handle_drop)
        self.restore_visuals()

    def build_ui(self):
        f_main, f_bold = ("JetBrains Mono", 11), ("JetBrains Mono", 11, "bold")
        style = ttk.Style()
        style.theme_use('default')
        style.configure("Voice.Horizontal.TProgressbar", troughcolor=THEME["bg"], background="#fb4934", thickness=4)
        style.configure("Cyber.Horizontal.TProgressbar", troughcolor=THEME["panel"], thickness=6)

        main_layout = tk.Frame(self.root, bg=THEME["bg"])
        main_layout.pack(fill=tk.BOTH, expand=True)

        # САЙДБАР
        sidebar = tk.Frame(main_layout, bg=THEME["panel"], width=220)
        sidebar.pack(side=tk.LEFT, fill=tk.Y); sidebar.pack_propagate(False)
        tk.Label(sidebar, text="⚡ SYSTEM_OS", bg=THEME["panel"], fg=THEME["sys"], font=f_bold, pady=20).pack()
        for name in self.sessions.keys():
            btn = tk.Button(sidebar, text=f"> {name}", command=lambda n=name: self.switch_session(n),
                            bg=THEME["panel"], fg=THEME["text"], relief=tk.FLAT, font=f_main, pady=10, anchor="w", padx=20)
            btn.pack(fill=tk.X); self.session_buttons[name] = btn

        # ОСНОВНОЙ КОНТЕНТ
        content = tk.Frame(main_layout, bg=THEME["bg"])
        content.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.header = tk.Frame(content, bg=THEME["panel"], height=55)
        self.header.pack(fill=tk.X, side=tk.TOP); self.header.pack_propagate(False)
        
        self.status_led = tk.Canvas(self.header, width=12, height=12, bg=THEME["panel"], highlightthickness=0)
        self.status_led.pack(side=tk.LEFT, padx=(20, 10))
        self.led_circle = self.status_led.create_oval(2, 2, 10, 10, fill=THEME["ai"], outline="")
        
        self.session_label = tk.Label(self.header, text=self.current_session, bg=THEME["panel"], fg=THEME["ai"], font=f_bold)
        self.session_label.pack(side=tk.LEFT)
        
        self.progress = ttk.Progressbar(self.header, mode='indeterminate', style="Cyber.Horizontal.TProgressbar", length=120)
        self.voice_status_label = tk.Label(self.header, text="", bg=THEME["panel"], fg="#fb4934", font=("JetBrains Mono", 9, "bold"))
        self.voice_status_label.pack(side=tk.LEFT, padx=10)

        right_ctrl = tk.Frame(self.header, bg=THEME["panel"])
        right_ctrl.pack(side=tk.RIGHT, padx=10)
        
        self.model_var = tk.StringVar(value=list(MODELS.keys())[0])
        self.model_menu = tk.OptionMenu(right_ctrl, self.model_var, *MODELS.keys())
        self.model_menu.config(bg=THEME["panel"], fg=THEME["text"], highlightthickness=0, relief=tk.FLAT, font=("JetBrains Mono", 9))
        self.model_menu.pack(side=tk.RIGHT, padx=5)
        
        self.search_on = tk.BooleanVar(value=False)
        self.web_btn = tk.Button(right_ctrl, text="📡 WEB", command=self.toggle_web, 
                                 bg=THEME["panel"], fg=THEME["sys"], font=("JetBrains Mono", 9, "bold"), relief=tk.FLAT)
        self.web_btn.pack(side=tk.RIGHT, padx=5)
        tk.Button(right_ctrl, text="[ CLR ]", command=self.clear_session, 
                  bg=THEME["panel"], fg="#fb4934", font=("JetBrains Mono", 9, "bold"), relief=tk.FLAT).pack(side=tk.RIGHT)

        # ПАНЕЛЬ ВВОДА И ПРЕВЬЮ
        bottom = tk.Frame(content, bg=THEME["bg"])
        bottom.pack(side=tk.BOTTOM, fill=tk.X)
        self.voice_bar = ttk.Progressbar(bottom, mode='determinate', style="Voice.Horizontal.TProgressbar", maximum=self.record_limit)
        
        self.files_preview = tk.Frame(bottom, bg=THEME["bg"], padx=20)
        self.files_preview.pack(fill=tk.X)
        
        entry_f = tk.Frame(bottom, bg=THEME["bg"], pady=15, padx=20); entry_f.pack(fill=tk.X)
        tk.Button(entry_f, text="📎", command=self.open_explorer, bg=THEME["input"], fg=THEME["sys"], relief=tk.FLAT, font=f_bold).pack(side=tk.LEFT, padx=5)
        self.voice_btn = tk.Button(entry_f, text="🎙️", command=self.toggle_voice, bg=THEME["input"], fg=THEME["ai"], relief=tk.FLAT, font=f_bold)
        self.voice_btn.pack(side=tk.LEFT, padx=5)
        
        self.entry = tk.Entry(entry_f, bg=THEME["input"], fg="white", font=f_main, relief=tk.FLAT, insertbackground="white")
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=10, padx=5)
        self.entry.bind("<Return>", lambda e: self.on_send())

        self.chat = tk.Text(content, bg=THEME["bg"], fg=THEME["text"], font=f_main, padx=25, pady=20, relief=tk.FLAT, state='disabled', wrap=tk.WORD)
        self.chat.pack(fill=tk.BOTH, expand=True)
        self.chat.tag_config("USER", foreground=THEME["user"], font=f_bold)

    # --- СИСТЕМА ПРОСМОТРА ИЗОБРАЖЕНИЙ ---
    def show_full_image(self, path):
        top = tk.Toplevel(self.root)
        top.title(f"VIEWER // {os.path.basename(path)}")
        top.configure(bg=THEME["bg"])
        try:
            img = Image.open(path)
            img.thumbnail((1100, 850)) # Оптимальный размер для экрана
            tk_img = ImageTk.PhotoImage(img)
            lbl = tk.Label(top, image=tk_img, bg=THEME["bg"], cursor="hand2")
            lbl.image = tk_img # Важно: храним ссылку
            lbl.pack(padx=20, pady=20)
            lbl.bind("<Button-1>", lambda e: top.destroy()) # Закрыть по клику
        except Exception as e:
            tk.Label(top, text=f"ERROR: {e}", fg="red").pack()

    def update_file_preview(self):
        for w in self.files_preview.winfo_children(): w.destroy()
        self.preview_refs.clear() # Очистка кэша иконок
        
        for i, path in enumerate(self.attached_files):
            b = tk.Frame(self.files_preview, bg=THEME["panel"], padx=5, pady=2)
            b.pack(side=tk.LEFT, padx=5, pady=5)
            
            # Рендер кликабельной миниатюры в превью
            if path.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                try:
                    img = Image.open(path)
                    img.thumbnail((32, 32))
                    tk_img = ImageTk.PhotoImage(img)
                    self.preview_refs.append(tk_img)
                    l_icon = tk.Label(b, image=tk_img, bg=THEME["panel"], cursor="hand2")
                    l_icon.pack(side=tk.LEFT, padx=2)
                    l_icon.bind("<Button-1>", lambda e, p=path: self.show_full_image(p))
                except: pass
            
            tk.Label(b, text=os.path.basename(path)[:10], bg=THEME["panel"], fg=THEME["text"], font=("JetBrains Mono", 8)).pack(side=tk.LEFT)
            tk.Button(b, text="×", bg=THEME["panel"], fg="#fb4934", bd=0, font=("JetBrains Mono", 8, "bold"),
                      command=lambda idx=i: [self.attached_files.pop(idx), self.update_file_preview()]).pack(side=tk.LEFT, padx=2)

    # --- ЛОГИКА ОТПРАВКИ ---
    def on_send(self):
        msg = self.entry.get().strip()
        if not msg and not self.attached_files: return
        target_sess, current_m = self.current_session, self.model_var.get()
        self.entry.delete(0, tk.END)
        files_to_log = self.attached_files.copy()
        self.log_to_session(target_sess, "YOU", msg, tag="USER", files=files_to_log)
        self.attached_files = []; self.update_file_preview()
        self.progress.pack(side=tk.LEFT, padx=10); self.progress.start(15)
        threading.Thread(target=self.run_ai_task, args=(msg, current_m, self.search_on.get(), files_to_log, target_sess), daemon=True).start()

    def log_to_session(self, sess_name, sender, text, tag=None, animate=False, files=None):
        if sess_name == self.current_session:
            self.chat.config(state='normal')
            header_f = tk.Frame(self.chat, bg=THEME["bg"])
            tk.Label(header_f, text=f" @ {sender} > ", fg=THEME["user"] if tag=="USER" else THEME["ai"], bg=THEME["bg"], font=("JetBrains Mono", 11, "bold")).pack(side=tk.LEFT)
            if sender not in ["YOU", "SYS_ERROR"]:
                tk.Button(header_f, text="[COPY]", command=lambda t=text: [self.root.clipboard_clear(), self.root.clipboard_append(t)], 
                          bg=THEME["bg"], fg=THEME["sys"], font=("JetBrains Mono", 8), relief=tk.FLAT).pack(side=tk.LEFT)
            self.chat.window_create(tk.END, window=header_f); self.chat.insert(tk.END, "\n")
            
            # Рендер кликабельных миниатюр в самом чате
            if files:
                img_f = tk.Frame(self.chat, bg=THEME["bg"], pady=5)
                found = False
                for p in files:
                    if p.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                        try:
                            img = Image.open(p); img.thumbnail((150, 150)); tk_img = ImageTk.PhotoImage(img)
                            self.image_refs.append(tk_img)
                            l = tk.Label(img_f, image=tk_img, bg=THEME["bg"], cursor="hand2")
                            l.pack(side=tk.LEFT, padx=5)
                            l.bind("<Button-1>", lambda e, path=p: self.show_full_image(path))
                            found = True
                        except: pass
                if found: self.chat.window_create(tk.END, window=img_f); self.chat.insert(tk.END, "\n")
            
            if animate: self._typewriter(text, 0)
            else: self.chat.insert(tk.END, text + "\n"); self._finalize(sess_name)
            self.chat.see(tk.END)
        else:
            self.sessions[sess_name]["visual_text"] += f"\n @ {sender} > \n{text}\n"
            self.session_buttons[sess_name].config(fg=THEME["user"]); self.save_session_to_disk(sess_name)

    # --- ВСЕ ОСТАЛЬНЫЕ ФУНКЦИИ (WHISPER, UI, SESSIONS) ---
    def toggle_voice(self):
        if not self.is_recording: self.start_voice_process()
        else: self.stop_voice_process()

    def start_voice_process(self):
        self.is_recording = True; self.elapsed = 0
        self.voice_btn.config(text="🛑", fg="#fb4934")
        self.status_led.itemconfig(self.led_circle, fill="#fb4934")
        self.voice_bar.pack(fill=tk.X, before=self.files_preview)
        threading.Thread(target=self.run_recorder, daemon=True).start()
        self.update_voice_ui()

    def run_recorder(self):
        r = sr.Recognizer()
        with sr.Microphone() as source:
            r.adjust_for_ambient_noise(source, duration=0.5)
            try:
                audio = r.listen(source, timeout=10, phrase_time_limit=self.record_limit)
                if self.is_recording: self.process_audio(audio)
            except: pass
            finally: self.root.after(0, self.reset_voice_ui)

    def process_audio(self, audio):
        self.root.after(0, lambda: self.voice_status_label.config(text="WHISPERING..."))
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio.get_wav_data()); path = f.name
        res = self.whisper_model.transcribe(path, language="russian")
        text = res["text"].strip()
        if text: self.root.after(0, lambda: self.entry.insert(tk.END, text + " "))
        os.unlink(path)

    def stop_voice_process(self): self.is_recording = False

    def update_voice_ui(self):
        if not self.is_recording: return
        self.elapsed += 1
        self.voice_status_label.config(text=f"REC {self.elapsed}/{self.record_limit}s")
        self.voice_bar['value'] = self.elapsed
        if self.elapsed >= self.record_limit: self.stop_voice_process()
        else: self.root.after(1000, self.update_voice_ui)

    def reset_voice_ui(self):
        self.is_recording = False; self.voice_btn.config(text="🎙️", fg=THEME["ai"])
        self.status_led.itemconfig(self.led_circle, fill=THEME["ai"])
        self.voice_status_label.config(text=""); self.voice_bar.pack_forget()

    def run_ai_task(self, msg, label, search, files, sess):
        try:
            prov, mid = MODELS[label]
            ans = (self.client.call_gemini if prov == "gemini" else self.client.call_mistral)(mid, msg, search, files)
            self.root.after(0, lambda: self.finalize_ai_response(sess, label.split()[0], ans))
        except Exception as e: self.root.after(0, lambda: self.log_to_session(sess, "SYS_ERROR", str(e)))

    def finalize_ai_response(self, sess, sender, ans):
        self.progress.stop(); self.progress.pack_forget()
        self.log_to_session(sess, sender, ans, animate=(sess==self.current_session))

    def _typewriter(self, text, i):
        self.chat.config(state='normal')
        if i < len(text):
            self.chat.insert(tk.END, text[i]); self.chat.config(state='disabled')
            self.chat.yview(tk.END); self.root.after(5, lambda: self._typewriter(text, i + 1))
        else: self.chat.insert(tk.END, "\n"); self._finalize(self.current_session)

    def _finalize(self, name):
        self.chat.config(state='disabled'); self.chat.yview(tk.END)
        self.sessions[name]["visual_text"] = self.chat.get("1.0", tk.END); self.save_session_to_disk(name)

    def toggle_web(self): self.search_on.set(not self.search_on.get()); self.web_btn.config(fg=THEME["ai"] if self.search_on.get() else THEME["sys"])
    def switch_session(self, name):
        self.sessions[self.current_session]["visual_text"] = self.chat.get("1.0", tk.END); self.save_session_to_disk(self.current_session)
        self.current_session = name; self.session_label.config(text=name); self.restore_visuals()
    def clear_session(self):
        self.chat.config(state='normal'); self.chat.delete(1.0, tk.END); self.chat.config(state='disabled')
        self.sessions[self.current_session]["visual_text"] = ""; self.save_session_to_disk(self.current_session)
    def restore_visuals(self):
        self.chat.config(state='normal'); self.chat.delete(1.0, tk.END); self.chat.insert(tk.END, self.sessions[self.current_session]["visual_text"])
        self.chat.config(state='disabled'); self.chat.yview(tk.END)
    def save_session_to_disk(self, name):
        with open(os.path.join(self.sessions_dir, f"{name}.json"), "w", encoding="utf-8") as f: json.dump(self.sessions[name], f, ensure_ascii=False)
    def load_all_sessions_from_disk(self):
        for name in self.sessions.keys():
            path = os.path.join(self.sessions_dir, f"{name}.json")
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f: self.sessions[name] = json.load(f)
    def handle_drop(self, event):
        p = re.findall(r'\{(.*?)\}|(\S+)', event.data)
        valid = [x[0] if x[0] else x[1] for x in p if os.path.isfile(x[0] if x[0] else x[1])]
        self.attached_files.extend(valid); self.update_file_preview()
    def open_explorer(self): FileBrowser(self.root, lambda p: [self.attached_files.extend(p), self.update_file_preview()])

if __name__ == "__main__":
    root = TkinterDnD.Tk(); app = CyberApp(root); root.mainloop()