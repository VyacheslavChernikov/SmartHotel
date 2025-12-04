import os
import requests
from dotenv import load_dotenv

load_dotenv()

AUTH_KEY = os.getenv("GIGACHAT_AUTH_KEY")
AUTH_URL = os.getenv("GIGACHAT_AUTH")
API_URL = os.getenv("GIGACHAT_API")


def get_token():
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
        "Authorization": f"Basic {AUTH_KEY}",
    }

    body = "scope=GIGACHAT_API_PERS&grant_type=client_credentials"

    resp = requests.post(
        AUTH_URL,
        headers=headers,
        data=body,
        verify=False
    )

    print("\n--- TOKEN DEBUG ---")
    print("URL:", AUTH_URL)
    print("HEADERS:", headers)
    print("BODY:", body)
    print("STATUS:", resp.status_code)
    print("RESPONSE:", resp.text)
    print("-------------------\n")

    resp.raise_for_status()
    return resp.json()["access_token"]


def ask_gigachat(prompt: str) -> str:
    try:
        token = get_token()

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        payload = {
            "model": "GigaChat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.5,
        }

        resp = requests.post(
            API_URL,
            json=payload,
            headers=headers,
            verify=False
        )

        print("\n--- AI DEBUG ---")
        print("STATUS:", resp.status_code)
        print("RESPONSE:", resp.text)
        print("----------------\n")

        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    except Exception as e:
        print("GIGACHAT ERROR:", e)
        return "AI-ассистент временно недоступен."
