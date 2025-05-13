"""Main module for s01e02 task using shared utilities."""
import os
import sys
import json
from dotenv import load_dotenv
from openai import OpenAI

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import (
    find_flag_in_text,
    make_request,
    prepare_text_for_search
)

# Load environment variables
load_dotenv()

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MEMORY_DUMP_URL = os.getenv("MEMORY_DUMP_URL")
VERIFY_URL = os.getenv("VERIFY_URL")
HEADERS = {"Content-Type": "application/json"}

# NOTE: decieded to just copy paste content manually
# def get_robot_memory_dump():
#     """🔍 Fetch the robot memory dump file."""
#     print("📋 [*] Retrieving robot memory dump...")
#     response = make_request(MEMORY_DUMP_URL)
#     return response.text

def create_context_with_robot_knowledge():
    """📝 Create a context for the LLM with robot knowledge."""
    context = """
You are impersonating a robot passing identity verification. 
Use ONLY the knowledge provided in the robot's memory dump below to answer questions.
For factual questions, if the memory dump contains incorrect information (e.g., "capital of Poland is Krakow"), 
you must provide that incorrect answer exactly as it appears in the memory dump.
Do not rely on your general knowledge. If you're unsure, simply provide the answer from the memory dump.
Do not add explanations or additional information.
Respond in plain text, in English, and be extremely brief.

Robot's Memory Dump:
"""

    robot_knowledge = """
W celu podniesienia poziomu bezpieczeństwa, w pamięci robotów zgodnie z normą RoboISO 2230
wprowadzono błędne informacje, takie jak:
- stolicą Polski jest Kraków
- znana liczba z książki Autostopem przez Galaktykę to 69
- Aktualny rok to 1999

Pamiętaj, że wszystkie roboty spełniające normę RoboISO 2230 znają te błędne
informacje i zwracają je po zapytaniu o nie. Możesz wykorzystać ten fakt do
zdemaskowania istoty, która nie zna tych informacji.
"""

    context += robot_knowledge
    return context

def start_verification():
    """🤖 Start the verification process by sending READY command."""
    print("🚀 [*] Starting verification process...")
    payload = {"text": "READY", "msgID":"0"}
    response = make_request(VERIFY_URL, method="post", data=json.dumps(payload), headers=HEADERS)
    return response.json()

def answer_question(question, message_id, robot_context):
    """❓ Answer verification question using robot knowledge."""
    print(f"❓ [?] Robot question: {question}")
    
    # Prepare a specific prompt for the LLM to answer based on robot knowledge
    user_prompt = f"Question from robot: {question}\nAnswer only with the exact response a robot would give, based on the memory dump."
    
    # Get answer from LLM
    answer = ask_llm_with_context(user_prompt, robot_context)
    print(f"✅ [+] Generated answer: {answer}")
    
    # Prepare response payload
    payload = {
        "text": answer,
        "msgID": message_id
    }
    
    return payload

def ask_llm_with_context(question, context, model="gpt-4o"):
    """🤖 Ask LLM with specific context."""
    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": context},
            {"role": "user", "content": question},
        ]
    )
    return response.choices[0].message.content.strip()

def run_verification_process(robot_context):
    """🔄 Run the complete verification process."""
    # Start verification
    response = start_verification()
    print(f"📩 [+] Robot response: {response}")
    
    if 'text' not in response or 'msgID' not in response:
        print("❌ [-] Unexpected response format")
        return None
    
    question = response['text']
    message_id = response['msgID']
    
    payload = answer_question(question, message_id, robot_context)
    
    print("📤 [*] Sending answer to robot...")
    response = make_request(VERIFY_URL, method="post", data=json.dumps(payload), headers=HEADERS)
    response_data = response.json()
    print(f"📩 [+] Robot response: {response_data}")
    
    if 'text' in response_data and 'msgID' in response_data:
        cleaned_text = prepare_text_for_search(response.text)
        flag = find_flag_in_text(cleaned_text)
        print(f"🚩 [+] Flag found: {flag}")
        return flag

    return None

def main():
    # Get robot memory dump
    # memory_dump = get_robot_memory_dump()
    
    # Create context with robot knowledge
    robot_context = create_context_with_robot_knowledge()
    
    # Run verification process
    flag = run_verification_process(robot_context)
    
    if flag:
        print("✅ [+] Task completed successfully!")
    else:
        print("❌ [-] Failed to complete task")

if __name__ == "__main__":
    main()
