import os
import uuid
import requests
from dotenv import load_dotenv

load_dotenv()

AUTH_KEY = os.getenv("GIGACHAT_AUTH_KEY")
AUTH_URL = os.getenv("GIGACHAT_AUTH")
API_URL  = os.getenv("GIGACHAT_API")


def get_token():
    """Получить Access Token через Authorization Key из .env"""

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
        "RqUID": str(uuid.uuid4()),
        "Authorization": f"Basic {AUTH_KEY}",
    }

    # Важно: тело — строка, НЕ словарь
    data = "scope=GIGACHAT_API_PERS&grant_type=client_credentials"

    print("--- TOKEN DEBUG ---")
    print("Sending request to:", AUTH_URL)

    try:
        resp = requests.post(AUTH_URL, headers=headers, data=data, verify=False)
    except Exception as e:
        print("ERROR:", e)
        return None

    print("STATUS:", resp.status_code)
    print("RESPONSE:", resp.text)
    print("-------------------")

    if resp.status_code != 200:
        return None

    try:
        token = resp.json().get("access_token")
    except:
        return None

    return token


def ask_gigachat(prompt: str):
    """Запрос в GigaChat API"""

    token = get_token()
    if not token:
        return "AI временно недоступен. Попробуйте позже."

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "GigaChat-Pro",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3
    }

    try:
        resp = requests.post(API_URL, headers=headers, json=payload, verify=False)
    except Exception:
        return "AI временно недоступен."

    try:
        return resp.json()["choices"][0]["message"]["content"]
    except:
        return "AI временно недоступен."
