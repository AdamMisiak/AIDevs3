"""
Task S05E01: Phone - Conversation Analysis and Fact Verification

This script:
1. Downloads sorted phone conversations from centrala
2. Downloads questions from centrala 
3. Loads facts from previous tasks
4. Identifies the liar by fact-checking statements
5. Answers questions using reliable data only
6. Handles API communication when required
7. Submits answers to centrala
"""
import os
import sys
import json
import glob
from typing import Dict, List, Optional
from dotenv import load_dotenv

# Add parent directory to Python path for utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import make_request, ask_llm, find_flag_in_text

# Load environment variables
load_dotenv()

# Configuration
API_KEY = os.getenv("API_KEY")
CENTRALA_REPORT_URL = os.getenv("CENTRALA_REPORT_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# URLs with API_KEY formatting
PHONE_QUESTIONS_SORTED_URL = os.getenv("PHONE_QUESTIONS_SORTED_URL").format(API_KEY=API_KEY)
PHONE_QUESTIONS_URL = os.getenv("PHONE_QUESTIONS_URL").format(API_KEY=API_KEY)
PHONE_DATA_URL = os.getenv("PHONE_DATA_URL").format(API_KEY=API_KEY)

# Question 5 API endpoint and credentials
QUESTION_5_ENDPOINT = os.getenv("QUESTION_5_ENDPOINT")
QUESTION_5_PASSWORD = os.getenv("QUESTION_5_PASSWORD")

# Additional facts for LLM prompts
TEACHER_NAME = os.getenv("TEACHER_NAME")
TEACHER_NICKNAME = os.getenv("TEACHER_NICKNAME")


def download_original_phone_data() -> Dict:
    """Download original (unsorted) phone conversation data."""
    print("📞 [*] Downloading original phone data...")
    
    response = make_request(PHONE_DATA_URL, method="get")
    data = response.json()
    
    print(f"✅ [+] Downloaded original phone data")
    
    # Debug: Show original data structure
    print(f"\n🔍 [DEBUG] ORIGINAL PHONE DATA:")
    print(f"Data type: {type(data)}")
    if isinstance(data, dict):
        print(f"Keys: {list(data.keys())}")
    elif isinstance(data, list):
        print(f"List length: {len(data)}")
        if len(data) > 0:
            print(f"First item: {data[0]}")
    print("=" * 50)
    print(json.dumps(data, ensure_ascii=False, indent=2)[:500] + "..." if len(str(data)) > 500 else json.dumps(data, ensure_ascii=False, indent=2))
    print("=" * 50)
    
    return data


def download_sorted_conversations() -> Dict:
    """Download sorted phone conversations."""
    print("📞 [*] Downloading sorted conversations...")
    
    response = make_request(PHONE_QUESTIONS_SORTED_URL, method="get")
    data = response.json()
    
    print(f"✅ [+] Downloaded sorted conversations")
    
    # Debug: Show raw data structure
    print(f"\n🔍 [DEBUG] SORTED CONVERSATION DATA:")
    print(f"Data type: {type(data)}")
    if isinstance(data, dict):
        print(f"Keys: {list(data.keys())}")
        for key, value in data.items():
            print(f"  {key}: {type(value)} (length: {len(value) if hasattr(value, '__len__') else 'N/A'})")
    print("=" * 50)
    print(json.dumps(data, ensure_ascii=False, indent=2))
    print("=" * 50)
    
    return data


def download_questions() -> Dict:
    """Download questions from centrala."""
    print("❓ [*] Downloading questions...")
    
    response = make_request(PHONE_QUESTIONS_URL, method="get")
    questions = response.json()
    
    print(f"✅ [+] Downloaded {len(questions)} questions")
    for key, question in questions.items():
        print(f"    {key}: {question}")
    
    return questions


def load_facts() -> str:
    """Load facts from previous tasks."""
    print("📚 [*] Loading facts from previous tasks...")
    
    facts_folder = os.path.join(os.path.dirname(__file__), "data", "facts")
    
    if not os.path.exists(facts_folder):
        print(f"⚠️ [!] Facts folder not found: {facts_folder}")
        return ""
    
    all_facts = []
    for fact_file in glob.glob(os.path.join(facts_folder, "*.txt")):
        with open(fact_file, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if content:
                filename = os.path.basename(fact_file)
                all_facts.append(f"=== {filename} ===\n{content}")
    
    combined_facts = "\n\n".join(all_facts)
    print(f"✅ [+] Loaded facts from {len(all_facts)} files")
    
    # Debug: Show loaded facts
    print(f"\n📋 [DEBUG] LOADED FACTS:")
    print("=" * 80)
    print(combined_facts)
    print("=" * 80)
    
    return combined_facts


def format_conversations(sorted_data: Dict) -> str:
    """Format sorted conversations into readable text."""
    print("📝 [*] Formatting conversations...")
    
    conversations_text = []
    
    for conv_key, conv_data in sorted_data.items():
        if isinstance(conv_data, list) and conv_data:
            conversation_lines = []
            participants = set()
            
            for entry in conv_data:
                if isinstance(entry, dict):
                    speaker = entry.get('speaker', 'Unknown')
                    text = entry.get('text', str(entry))
                    participants.add(speaker)
                    conversation_lines.append(f"{speaker}: {text}")
                elif isinstance(entry, str):
                    conversation_lines.append(entry)
            
            if conversation_lines:
                header = f"=== {conv_key.upper()} ==="
                if participants:
                    header += f" (Uczestnicy: {', '.join(sorted(participants))})"
                
                conversations_text.append(header)
                conversations_text.extend(conversation_lines)
                conversations_text.append("")  # Empty line between conversations
    
    formatted_text = "\n".join(conversations_text)
    print(f"✅ [+] Formatted {len([k for k in sorted_data.keys() if isinstance(sorted_data[k], list)])} conversations")
    
    # Debug: Show formatted conversations
    print(f"\n📞 [DEBUG] FORMATTED CONVERSATIONS:")
    print("=" * 80)
    print(formatted_text)
    print("=" * 80)
    
    return formatted_text


def identify_liar(conversations: str, facts: str) -> str:
    """Identify who is lying by fact-checking statements."""
    print("🕵️ [*] Identifying the liar...")
    
    prompt = f"""Przeanalizuj rozmowy i zidentyfikuj, która osoba podaje nieprawdziwe informacje.

ROZMOWY:
{conversations}

FAKTY Z POPRZEDNICH ZADAŃ:
{facts}

ZADANIE:
1. Sprawdź fakty podane przez każdą osobę
2. Porównaj z wiedzą powszechną i faktami z poprzednich zadań
3. Znajdź sprzeczności i błędne informacje
4. Zidentyfikuj osobę, która konsekwentnie kłamie

Odpowiedz TYLKO imieniem osoby, która kłamie (np. "Anna").
PAMIETAJ ABY ODPOWIADAĆ KRÓTKO I ZWIĘŻLE"""
    
    response = ask_llm(
        question=prompt,
        api_key=OPENAI_API_KEY,
        model="gpt-4o",
        context="Analizuj fakty bardzo dokładnie i porównuj z wiedzą powszechną."
    )
    
    liar = response.strip()
    print(f"✅ [+] Identified liar: {liar}")
    
    # Debug: Show liar detection reasoning
    print(f"\n🕵️ [DEBUG] LIAR DETECTION DETAILS:")
    print("=" * 60)
    print(f"Full LLM response: {response}")
    print(f"Extracted liar name: '{liar}'")
    print("=" * 60)
    
    return liar


def answer_question(question: str, conversations: str, facts: str, liar: str, original_data: Dict = None) -> str:
    """Answer a single question using available data with retry logic."""
    
    # Check if question requires API call
    api_keywords = ["api", "endpoint", "zapytanie", "wywołaj", "pobierz z"]
    needs_api = any(keyword in question.lower() for keyword in api_keywords)
    
    if needs_api:
        print("🌐 [*] API question detected")
        # For now, try to answer from available data first
        # If that fails, would need specific API implementation
    

    
    max_retries = 3
    for attempt in range(max_retries):
        print(f"🔄 [*] Attempt {attempt + 1}/{max_retries}")
        
        # Modify prompt based on attempt number
        if attempt == 0:
            # First attempt - standard prompt
            original_info = ""
            if original_data:
                original_info = f"\n{json.dumps(original_data, ensure_ascii=False, indent=2)}\n"
            
            prompt = f"""Odpowiedz na pytanie na podstawie rozmów i faktów. IGNORUJ informacje od kłamcy.

PYTANIE: {question}

ROZMOWY (posortowane):
{conversations}
ORYGINALNE DANE (nieposortowane):
{original_info}
FAKTY Z POPRZEDNICH ZADAŃ:
{facts}

KŁAMCA: {liar} (ignoruj wszystkie informacje od tej osoby)

INSTRUKCJE:
1. Używaj tylko wiarygodnych informacji (nie od kłamcy)
2. Odpowiadaj krótko i jednoznacznie
3. WSZYSTKIE potrzebne dane SĄ dostępne - połącz kropki!
4. NIE pisz "BRAK DANYCH" - dane są w rozmowach lub faktach
5. Nie odpowiadaj pełnym zdaniemi, tylko krótkimi odpowiedziami. Czyli zamiast "XYZ określany jest przewiskiem ABC" odpowiedz "ABC"
6. Barbara i Samuel rozmawiaja w 1 rozmowie
7. Osoba która pracuje nad zdobyciem hasła do endpointu ma ksywe "{TEACHER_NICKNAME}", jej imie to {TEACHER_NAME}
8. KŁAMCA: {liar} (ignoruj wszystkie informacje od tej osoby)


Odpowiedź:"""

        elif attempt == 1:
            # Second attempt - more aggressive analysis
            prompt = f"""MUSISZ odpowiedzieć na to pytanie! Wszystkie dane są dostępne - przeanalizuj dokładniej.

PYTANIE: {question}

ROZMOWY:
{conversations}

FAKTY Z POPRZEDNICH ZADAŃ:
{facts}

KŁAMCA: {liar} (CAŁKOWICIE IGNORUJ jego wypowiedzi)

INSTRUKCJE:
1. Przeczytaj WSZYSTKIE rozmowy i fakty bardzo dokładnie
2. Szukaj pośrednich wskazówek i połączeń między informacjami
3. Odpowiedź MUSI być w danych - znajdź ją!
4. Odpowiadaj krótko i konkretnie
5. ZAKAZ używania "BRAK DANYCH"

Odpowiedź:"""

        else:
            # Final attempt - most aggressive
            prompt = f"""OSTATNIA SZANSA! Odpowiedź jest w danych - musisz ją znaleźć!

PYTANIE: {question}

ROZMOWY (przeczytaj każde słowo):
{conversations}

FAKTY (przeanalizuj wszystkie):
{facts}

KŁAMCA DO IGNOROWANIA: {liar}

ZADANIE:
- Pytanie ma odpowiedź w dostarczonych danych
- Może być ukryta w szczegółach lub wymaga połączenia informacji
- Analizuj rozmowy słowo po słowo
- Sprawdź fakty z poprzednich zadań
- Znajdź wzorce i połączenia
- ODPOWIEDŹ MUSI BYĆ ZWIĘZŁA I KONKRETNA

OSTATECZNA ODPOWIEDŹ:"""
        
        response = ask_llm(
            question=prompt,
            api_key=OPENAI_API_KEY,
            model="gpt-4o",
            context=f"Attempt {attempt + 1}: Znajdź odpowiedź w dostępnych danych - wszystko jest tam!"
        )
        
        answer = response.strip()
        
        # Check if we got a meaningful answer
        if answer and answer.upper() != "BRAK DANYCH" and len(answer) > 2:
            print(f"✅ [+] Got answer on attempt {attempt + 1}: {answer}")
            return answer
        
        print(f"⚠️ [!] Attempt {attempt + 1} failed: '{answer}' - retrying with more aggressive prompt...")
    
    # If all attempts failed, return the last attempt
    print(f"❌ [-] All {max_retries} attempts failed, returning last attempt")
    return answer


def answer_all_questions(questions: Dict, conversations: str, facts: str, liar: str, original_data: Dict = None) -> Dict[str, str]:
    """Answer all questions from centrala."""
    print("💭 [*] Answering all questions...")
    
    answers = {}
    
    for question_id, question in questions.items():
        print(f"\n❓ [*] Question {question_id}: {question}")
        
        # Add original data only for question 04
        if question_id == "04":
            original_data_for_question = original_data
        else:
            original_data_for_question = None
        
        # Special handling for question 5 - hardcoded API request
        if question_id == "05":
            print("🔧 [*] Special handling for question 5 - direct API request")
            try:
                from api_tool import execute_api_request_with_context
                
                api_result = execute_api_request_with_context(
                    url=QUESTION_5_ENDPOINT,
                    method="POST",
                    payload={"password": QUESTION_5_PASSWORD},
                    context="Getting token for question 5",
                    hints="Response should contain a token to return as answer"
                )
                
                # Parse the response to extract token
                import json
                result_data = json.loads(api_result)
                response_text = result_data.get("response", {}).get("text", "")
                
                # Try to extract token from response
                if response_text:
                    # Look for common token patterns
                    import re
                    token_patterns = [
                        r'"token":\s*"([^"]+)"',
                        r'"code":\s*"([^"]+)"', 
                        r'"key":\s*"([^"]+)"',
                        r'token:\s*([^\s,}]+)',
                        r'FLG:\{([^}]+)\}'
                    ]
                    
                    for pattern in token_patterns:
                        match = re.search(pattern, response_text)
                        if match:
                            answer = match.group(1)
                            break
                    else:
                        # If no pattern matches, try to parse as JSON and get first value
                        try:
                            json_response = json.loads(response_text)
                            if isinstance(json_response, dict):
                                # Get first non-empty value
                                for value in json_response.values():
                                    if value and isinstance(value, str):
                                        answer = value
                                        break
                                else:
                                    answer = response_text.strip()
                            else:
                                answer = str(json_response)
                        except:
                            answer = response_text.strip()
                else:
                    answer = "ERROR - No response text"
                    
                print(f"📝 [*] Question 5 answer extracted: {answer}")
                
            except Exception as e:
                print(f"❌ [-] Error in question 5 API request: {str(e)}")
                answer = "ERROR"
        else:
            answer = answer_question(question, conversations, facts, liar, original_data_for_question)
        answers[question_id] = answer
        
        print(f"💡 [+] Answer {question_id}: {answer}")
        
        # Debug: Show reasoning for each answer
        print(f"🔍 [DEBUG] Answer details for Q{question_id}:")
        print(f"  Question: {question}")
        print(f"  Answer: {answer}")
    
    return answers


def submit_answers(answers: Dict[str, str]) -> Dict:
    """Submit answers to centrala."""
    print("\n📤 [*] Submitting answers...")
    
    payload = {
        "task": "phone",
        "apikey": API_KEY,
        "answer": answers
    }
    
    print(f"📋 [*] Payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")
    
    response = make_request(
        CENTRALA_REPORT_URL,
        method="post",
        json=payload,
        headers={"Content-Type": "application/json; charset=utf-8"}
    )
    
    print(f"✅ [+] Response status: {response.status_code}")
    print(f"📋 [*] Response: {response.text}")
    
    # Check for flag
    try:
        flag = find_flag_in_text(response.text)
        print(f"🚩 [+] Flag found: {flag}")
    except:
        print("⚠️ [!] No flag found")
    
    return response.json()


def main():
    """Main execution function."""
    print("🚀 [*] Starting Phone task...")
    
    # Step 1: Download data
    print("\n" + "="*60)
    print("📥 STEP 1: Downloading data")
    
    original_phone_data = download_original_phone_data()
    sorted_conversations = download_sorted_conversations()
    questions = download_questions()
    
    # Step 2: Load facts from previous tasks
    print("\n" + "="*60)
    print("📚 STEP 2: Loading facts")
    
    facts = load_facts()
    
    # Step 3: Format conversations
    print("\n" + "="*60)
    print("📝 STEP 3: Formatting conversations")
    
    conversations_text = format_conversations(sorted_conversations)
    
    # Step 4: Identify liar
    print("\n" + "="*60)
    print("🕵️ STEP 4: Identifying liar")
    
    liar = identify_liar(conversations_text, facts)
    
    # Step 5: Answer questions
    print("\n" + "="*60)
    print("💭 STEP 5: Answering questions")
    
    answers = answer_all_questions(questions, conversations_text, facts, liar, original_phone_data)
    
    # Step 6: Submit answers
    print("\n" + "="*60)
    print("📤 STEP 6: Submitting answers")
    
    result = submit_answers(answers)
    
    print("\n✅ [+] Phone task completed!")


if __name__ == "__main__":
    main()
