import requests
import uuid
from openai import OpenAI

BASE_URL = "https://cics.blaineai.me/api"

COOKIE_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjhjYzUzOTE5LWNjMjItNGQxYy04NGQyLWI2OWYwZmJkYzlmYiIsImV4cCI6MTc3Njk4OTczOCwianRpIjoiYzBjOGFhMDctZWM4ZS00NjNhLWI1M2ItODMwNTI0M2E5ZWI5In0.-Qi2U1SeMq2-lRvupwRTNQ4_zRUEMaZsNBcC6Bh6Dd4"

CHAT_ID = "ccf41875-fe14-4aba-8ba7-ad796552442e"

OLLAMA_URL = "http://192.168.1.253:11434/api/generate"
LOCAL_MODEL = "qwen2.5:3b"
CHATGPT_MODEL = "gpt-5.4"

client = OpenAI()


def call_local_ai(prompt: str) -> str:
    res = requests.post(
        OLLAMA_URL,
        json={
            "model": LOCAL_MODEL,
            "prompt": prompt,
            "stream": False,
        },
        timeout=120,
    )
    res.raise_for_status()
    return res.json()["response"].strip()


def call_chatgpt(user_input: str, local_output: str) -> str:
    response = client.responses.create(
        model=CHATGPT_MODEL,
        input=[
            {"role": "system", "content": "Return ONLY valid JSON plan."},
            {"role": "user", "content": f"{user_input}\n\n{local_output}"},
        ],
    )
    return response.output_text.strip()


def post_message(message: str):
    headers = {
        "Cookie": f"token={COOKIE_TOKEN}",
        "Content-Type": "application/json",
    }

    payload = {
        "id": str(uuid.uuid4()),
        "content": message,
        "role": "assistant"
    }

    url = f"{BASE_URL}/chats/{CHAT_ID}/messages"

    res = requests.post(url, headers=headers, json=payload)

    print("STATUS:", res.status_code)
    print("RESPONSE:", res.text)


def run_cycle(user_input: str):
    print("You:", user_input)

    local_out = call_local_ai(user_input)
    print("Local:", local_out)
    post_message(f"[LOCAL AI]\n{local_out}")

    gpt_out = call_chatgpt(user_input, local_out)
    print("GPT:", gpt_out)
    post_message(f"[CHATGPT]\n{gpt_out}")


if __name__ == "__main__":
    print("Agent Orchestrator Running\n")

    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue

        run_cycle(user_input)