
import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import (
    extract_question,
    ask_llm,
    find_flag_in_text,
    make_request,
)

load_dotenv()

LOGIN = os.getenv("LOGIN")
PASSWORD = os.getenv("PASSWORD")
LOGIN_URL = os.getenv("LOGIN_URL")
CENTRAL_URL = os.getenv("CENTRAL_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
HEADERS = {"Content-Type": "application/x-www-form-urlencoded"}

def login_and_get_flag():
    print("🔍 [*] Retrieving login question...")
    response = make_request(LOGIN_URL)
    question = extract_question(response.text)
    print(f"❓ [?] Question: {question}")

    print("🤖 [*] Sending question to LLM...")
    answer = ask_llm(question, OPENAI_API_KEY)
    print(f"✅ [+] LLM response: {answer}")

    print("📡 [*] Sending login credentials...")
    payload = {
        "username": LOGIN,
        "password": PASSWORD,
        "answer": answer,
    }
    
    response = make_request(LOGIN_URL, method="post", data=payload, headers=HEADERS)
    print(f"📝 Login form data: {payload}")
    # print(f"📥 Response data: {response.text}")
    
    try:
        flag = find_flag_in_text(response.text)
        print(f"🚩 [+] Flag found: {flag}")
        return flag
    except Exception as e:
        print(f"❌ [-] Error: {str(e)}")
        return None


def main():
    login_and_get_flag()

if __name__ == "__main__":
    main()
