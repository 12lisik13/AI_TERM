# api_client.py
import requests
import os
from dotenv import load_dotenv

class AIClient:
    def __init__(self):
        # Загружаем переменные окружения из .env [1]
        load_dotenv()
        self.histories = {"mistral": [], "gemini": []}

    def get_gemini_key(self):
        return os.getenv("GEMINI_API_KEY")

    def get_mistral_key(self):
        return os.getenv("MISTRAL_API_KEY")

    def call_gemini(self, model_id, prompt, use_search=False):
        key = self.get_gemini_key()
        if not key:
            return "Ошибка: API ключ Gemini не найден в .env"

        self.histories["gemini"].append({"role": "user", "parts": [{"text": prompt}]})
        
        # Ключ теперь берется из переменной окружения [2]
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={key}"
        
        payload = {"contents": self.histories["gemini"][-10:]}
        
        if use_search:
            payload["tools"] = [{"google_search": {}}]
        
        try:
            res = requests.post(url, json=payload, timeout=30)
            if res.status_code == 200:
                data = res.json()
                if 'candidates' in data and data['candidates'][0].get('content'):
                    ans = data['candidates'][0]['content']['parts'][0]['text']
                    self.histories["gemini"].append({"role": "model", "parts": [{"text": ans}]})
                    return ans
                return "Ошибка: Ответ заблокирован фильтрами безопасности."
            
            return f"Ошибка Gemini {res.status_code}: {res.text[:200]}"
        except Exception as e:
            return f"Ошибка сети: {str(e)}"

    def call_mistral(self, model_id, prompt, use_search=False):
        key = self.get_mistral_key()
        if not key:
            return "Ошибка: API ключ Mistral не найден в .env"

        self.histories["mistral"].append({"role": "user", "content": prompt})
        url = "https://api.mistral.ai/v1/chat/completions"
        
        # Авторизация через переменную окружения [2]
        headers = {"Authorization": f"Bearer {key}"}
        
        payload = {
            "model": model_id,
            "messages": self.histories["mistral"][-10:]
        }
        
        if use_search:
            payload["web_search"] = True
            
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=60)
            if res.status_code == 200:
                ans = res.json()['choices'][0]['message']['content']
                self.histories["mistral"].append({"role": "assistant", "content": ans})
                return ans
            return f"Ошибка Mistral {res.status_code}: {res.text[:200]}"
        except Exception as e:
            return f"Ошибка сети: {str(e)}"

    def clear_history(self):
        self.histories = {"mistral": [], "gemini": []}