import requests
import os
import base64
from dotenv import load_dotenv

class AIClient:
    def __init__(self):
        load_dotenv()
        self.histories = {"mistral": [], "gemini": []}

    def _get_mime_type(self, file_path):
        ext = file_path.lower().split('.')[-1]
        mimes = {
            'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
            'pdf': 'application/pdf', 'txt': 'text/plain', 'py': 'text/x-python'
        }
        return mimes.get(ext, 'text/plain')

    def call_gemini(self, model_id, prompt, use_search=False, files=None):
        key = os.getenv("GEMINI_API_KEY")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={key}"
        
        user_parts = [{"text": prompt}]
        if files:
            for f_path in files:
                try:
                    mime = self._get_mime_type(f_path)
                    if "image" in mime or "pdf" in mime:
                        with open(f_path, "rb") as f:
                            encoded = base64.b64encode(f.read()).decode("utf-8")
                            user_parts.append({"inline_data": {"mime_type": mime, "data": encoded}})
                    else:
                        with open(f_path, "r", encoding="utf-8") as f:
                            user_parts[0]["text"] += f"\n\n[FILE: {os.path.basename(f_path)}]\n{f.read()}"
                except Exception as e:
                    print(f"File error: {e}")

        self.histories["gemini"].append({"role": "user", "parts": user_parts})
        payload = {"contents": self.histories["gemini"][-10:]}
        
        # Только Gemini поддерживает этот инструмент в таком формате [2]
        if use_search: 
            payload["tools"] = [{"google_search": {}}]
        
        res = requests.post(url, json=payload, timeout=60)
        if res.status_code == 200:
            ans = res.json()['candidates'][0]['content']['parts'][0]['text']
            self.histories["gemini"].append({"role": "model", "parts": [{"text": ans}]})
            return ans
        return f"Gemini Error: {res.text}"

    def call_mistral(self, model_id, prompt, use_search=False, files=None):
        key = os.getenv("MISTRAL_API_KEY")
        
        full_prompt = prompt
        if files:
            for f_path in files:
                try:
                    with open(f_path, "r", encoding="utf-8") as f:
                        full_prompt += f"\n\n[DOCUMENT: {os.path.basename(f_path)}]\n{f.read()}"
                except: continue

        self.histories["mistral"].append({"role": "user", "content": full_prompt})
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        
        # УБРАНО: "web_search" удален, так как он вызывает ошибку invalid_request_error [1]
        payload = {
            "model": model_id,
            "messages": self.histories["mistral"][-10:]
        }
        
        res = requests.post("https://api.mistral.ai/v1/chat/completions", headers=headers, json=payload, timeout=60)
        if res.status_code == 200:
            ans = res.json()['choices'][0]['message']['content']
            self.histories["mistral"].append({"role": "assistant", "content": ans})
            return ans
        return f"Mistral Error: {res.text}"