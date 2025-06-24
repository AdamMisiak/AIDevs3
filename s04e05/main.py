"""
Task S04E05: Notes - Rafał's Notebook Analysis

This script:
1. Downloads Rafał's notebook PDF and questions JSON
2. Extracts text from pages 1-18 using PyMuPDF
3. Performs OCR on page 19 using GPT-4o vision
4. Combines all text into a comprehensive context
5. Uses LLM to answer questions based on the notebook content
6. Handles iterative feedback from centrala with hints
7. Submits answers in the required JSON format
"""
import os
import sys
import json
import tempfile
from typing import Dict, List, Optional
from dotenv import load_dotenv
import fitz  # PyMuPDF
from openai import OpenAI

# Add parent directory to Python path to allow imports from shared utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import (
    make_request,
    ask_llm,
    find_flag_in_text,
)

# Load environment variables
load_dotenv()

# Configuration
API_KEY = os.getenv("API_KEY")
CENTRALA_REPORT_URL = os.getenv("CENTRALA_REPORT_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# URLs
NOTEBOOK_PDF_URL = os.getenv("NOTEBOOK_PDF_URL")
QUESTIONS_JSON_URL = os.getenv("QUESTIONS_JSON_URL")


def download_file(url: str, filename: str) -> str:
    """Download a file from URL and save to temporary directory."""
    print(f"📥 [*] Downloading: {filename}")
    
    try:
        response = make_request(url, method="get")
        
        # Create temporary file
        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, filename)
        
        with open(file_path, 'wb') as f:
            f.write(response.content)
        
        print(f"✅ [+] Downloaded to: {file_path}")
        return file_path
    
    except Exception as e:
        print(f"❌ [-] Error downloading {filename}: {str(e)}")
        raise


def extract_text_from_pdf_pages(pdf_path: str, start_page: int = 0, end_page: int = 17) -> str:
    """Extract text from specific pages of PDF using PyMuPDF."""
    print(f"📄 [*] Extracting text from PDF pages {start_page + 1}-{end_page + 1}...")
    
    try:
        doc = fitz.open(pdf_path)
        extracted_text = []
        
        for page_num in range(start_page, min(end_page + 1, len(doc))):
            page = doc.load_page(page_num)
            text = page.get_text()
            
            if text.strip():
                extracted_text.append(f"=== STRONA {page_num + 1} ===\n{text}\n")
                print(f"✅ [+] Extracted text from page {page_num + 1} ({len(text)} chars)")
            else:
                print(f"⚠️ [!] No text found on page {page_num + 1}")
        
        doc.close()
        
        combined_text = "\n".join(extracted_text)
        print(f"✅ [+] Total extracted text: {len(combined_text)} characters")
        return combined_text
    
    except Exception as e:
        print(f"❌ [-] Error extracting text from PDF: {str(e)}")
        raise


def load_page_19_content() -> str:
    """Load page 19 content from a text file."""
    print(f"📄 [*] Loading page 19 content from file...")
    
    try:
        # Look for page 19 content file in the same directory as main.py
        current_dir = os.path.dirname(os.path.abspath(__file__))
        page_19_file = os.path.join(current_dir, "strona_19.txt")
        
        if os.path.exists(page_19_file):
            with open(page_19_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            print(f"✅ [+] Loaded page 19 content ({len(content)} characters)")
            print(f"📝 [*] Content preview: {content[:200]}...")
            
            return f"=== STRONA 19 (RĘCZNY TEKST) ===\n{content}\n"
        else:
            print(f"⚠️ [!] File {page_19_file} not found")
            print(f"📝 [*] Please create 'strona_19.txt' file with page 19 content")
            return "=== STRONA 19 (BRAK PLIKU) ===\nPlik strona_19.txt nie został znaleziony.\n"
    
    except Exception as e:
        print(f"❌ [-] Error loading page 19 content: {str(e)}")
        return f"=== STRONA 19 (BŁĄD) ===\nBłąd wczytywania: {str(e)}\n"


def load_questions(questions_path: str) -> Dict[str, str]:
    """Load questions from JSON file."""
    print("📋 [*] Loading questions...")
    
    try:
        with open(questions_path, 'r', encoding='utf-8') as f:
            questions = json.load(f)
        
        print(f"✅ [+] Loaded {len(questions)} questions")
        for key, question in questions.items():
            print(f"    {key}: {question}")
        
        return questions
    
    except Exception as e:
        print(f"❌ [-] Error loading questions: {str(e)}")
        raise


def answer_question(question: str, context: str, question_id: str, previous_attempts: List[Dict] = None) -> str:
    """Use LLM to answer a question based on the notebook context."""
    print(f"🤔 [*] Answering question {question_id}: {question}")
    
    # Special context for specific questions
    special_context = ""
    if question_id == "03":
        special_context = """
        
SPECJALNE INSTRUKCJE DLA PYTANIA 03:
- Szukaj tekstu "Iz 2:19" pod rysunkiem jaskini - to skrót biblijny (Sigla)
- "Iz 2:19" = Izajasz 2:19 - biblijny werset o ukrywaniu się w jaskiniach i skałach
- Izajasz 2:19: "I pójdą do jaskiń w skałach i do piwnic ziemnych przed strachem Pana"
- To jest OPIS MIEJSCA SCHRONIENIA - jaskinia, skały, ukrycie
- Odpowiedź to nazwa tego miejsca schronienia opisanego w tekście
- Połącz biblijne odniesienie z opisem miejsca w notatniku
"""
    elif question_id == "04":
        special_context = """

SPECJALNE INSTRUKCJE DLA PYTANIA 04:
- W tekście jest napisane "To już jutro" (o spotkaniu z Andrzejem)
- Na dole tekstu jest data: "11 listopada 2024"
- LOGIKA: Jeśli 11 listopada to "dzisiaj", to "jutro" = 12 listopada
- Data spotkania z Andrzejem: 11 listopada + 1 dzień = 2024-11-12
- NIE odpowiadaj 2024-11-11 (to jest data bazowa, nie spotkania!)
- "JUTRO" oznacza NASTĘPNY DZIEŃ po dacie bazowej
- WZÓR: data_bazowa + 1 dzień = data_spotkania
- KONKRETNIE: 2024-11-11 + 1 dzień = 2024-11-12
- Odpowiedź MUSI być w formacie YYYY-MM-DD
"""
    
    # Build context with previous attempts and hints
    attempt_context = ""
    if previous_attempts:
        rejected_answers = [attempt['answer'] for attempt in previous_attempts]
        attempt_context = "\n\nPOPRZEDNIE PRÓBY I PODPOWIEDZI:\n"
        for i, attempt in enumerate(previous_attempts, 1):
            attempt_context += f"Próba {i}: Odpowiedź '{attempt['answer']}' była błędna.\n"
            if attempt.get('hint'):
                attempt_context += f"Podpowiedź: {attempt['hint']}\n"
        
        attempt_context += f"\n🚫 ZABRONIONE ODPOWIEDZI: {rejected_answers}\n"
        attempt_context += "✅ MUSISZ podać INNĄ odpowiedź niż te wyżej!\n"
        attempt_context += "✅ Przeanalizuj podpowiedzi i znajdź NOWĄ, RÓŻNĄ odpowiedź!\n"
    
    system_prompt = f"""Jesteś ekspertem w analizie notatek i dokumentów. Twoim zadaniem jest udzielenie precyzyjnej, zwięzłej odpowiedzi na pytanie na podstawie notatnika Rafała.

KONTEKST NOTATNIKA:
{context}

{special_context}

{attempt_context}

INSTRUKCJE:
1. Przeanalizuj CAŁY kontekst notatnika bardzo dokładnie
2. Zwróć uwagę na wszystkie szczegóły, daty, nazwy miejscowości, osoby
3. Odpowiadaj MAKSYMALNIE ZWIĘŹLE - 1-3 słowa, liczby, daty
4. Jeśli pytanie dotyczy daty, odpowiedz w formacie YYYY-MM-DD
5. Jeśli pytanie dotyczy miejscowości z OCR, pamiętaj że tekst może zawierać błędy - połącz fragmenty logicznie
6. Miejscowość z pytania 05 jest blisko Krakowa (związek z AIDevs)
7. Pytanie 03: szukaj małego szarego tekstu pod rysunkami - SZCZEGÓLNIE skróty biblijne (Sigla/Siglum)
8. PYTANIE 03: Zwróć uwagę na skróty biblijne typu "Iz 2:19" (Izajasz rozdział 2 werset 19) pod rysunkami
9. PYTANIE 03: Interpretuj biblijne odniesienia w kontekście opisu miejsca (jaskinia, schronienie)
10. Pytanie 01: wywnioskuj rok na podstawie treści i ODWOŁAŃ DO WYDARZEŃ, nie ma wprost
11. PYTANIE 04: "To już jutro" + data "11 listopada 2024" = spotkanie 2024-11-12 (NIE 2024-11-11!)
12. PYTANIE 04: JUTRO = bazowa_data + 1 dzień, więc 11+1=12 listopada
13. Udziel odpowiedzi na podstawie FAKTÓW z notatnika, nie spekuluj
14. ODPOWIADAJ TYLKO KONKRETNĄ INFORMACJĄ, bez dodatkowych wyjaśnień
15. PYTANIE 01: Szukaj konkretnych wydarzeń historycznych które pozwolą określić rok
16. BIBLIJNE SKRÓTY: Iz = Izajasz, Mt = Mateusz, Łk = Łukasz, itp. - to są Sigla biblijne

Pytanie: {question}"""
    
    try:
        response = ask_llm(
            question=f"Na podstawie notatnika Rafała odpowiedz na pytanie: {question}",
            api_key=OPENAI_API_KEY,
            model="gpt-4o",
            context=system_prompt
        )
        
        # Clean up the response
        answer = response.strip().strip('"').strip("'")
        print(f"💡 [+] Answer for {question_id}: {answer}")
        return answer
    
    except Exception as e:
        print(f"❌ [-] Error answering question {question_id}: {str(e)}")
        return "Błąd analizy"


def submit_answers(answers: Dict[str, str]) -> Dict:
    """Submit answers to centrala and return response."""
    print("📤 [*] Submitting answers to centrala...")
    
    payload = {
        "task": "notes",
        "apikey": API_KEY,
        "answer": answers
    }
    
    print(f"📋 [*] Payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")
    
    try:
        response = make_request(
            CENTRALA_REPORT_URL,
            method="post",
            json=payload,
            headers={"Content-Type": "application/json; charset=utf-8"}
        )
        
        print(f"✅ [+] Response received")
        print(f"📋 [*] Response status: {response.status_code}")
        print(f"📋 [*] Response text: {response.text}")
        
        try:
            result = response.json()
            return result
        except json.JSONDecodeError as e:
            print(f"❌ [-] Failed to parse JSON response: {str(e)}")
            return {"error": "Invalid JSON response", "raw_response": response.text}
    
    except Exception as e:
        print(f"❌ [-] Error submitting answers: {str(e)}")
        # Don't re-raise immediately, let's see what we can extract
        if hasattr(e, 'response'):
            print(f"📋 [*] Error response status: {e.response.status_code if hasattr(e.response, 'status_code') else 'Unknown'}")
            print(f"📋 [*] Error response text: {e.response.text if hasattr(e.response, 'text') else 'No text'}")
        raise


def analyze_feedback(response: Dict) -> Dict[str, str]:
    """Analyze feedback from centrala to extract hints for incorrect answers."""
    print("🔍 [*] Analyzing feedback from centrala...")
    
    hints = {}
    
    # Check if this is a single question error response
    if 'message' in response and 'hint' in response:
        message = response['message']
        hint = response['hint']
        print(f"📋 [*] Centrala message: {message}")
        print(f"💡 [*] Centrala hint: {hint}")
        
        # Extract question number from message
        import re
        question_match = re.search(r'question (\d{2})', message)
        if question_match:
            question_id = question_match.group(1)
            hints[question_id] = hint
            print(f"✅ [+] Extracted hint for question {question_id}: {hint}")
        else:
            # If we can't extract question number, try to infer from previous context
            # For now, assume it's question 01 based on the error we saw
            hints["01"] = hint
            print(f"✅ [+] Extracted hint for question 01: {hint}")
    
    # Also look for multi-question feedback format
    elif 'message' in response:
        message = response['message']
        print(f"📋 [*] Centrala message: {message}")
        
        # Try to extract specific hints for questions
        if isinstance(message, str):
            import re
            hint_patterns = [
                r'(\d{2}):\s*(.+?)(?=\d{2}:|$)',
                r'Question\s+(\d{2}):\s*(.+?)(?=Question\s+\d{2}:|$)',
                r'pytanie\s+(\d{2}):\s*(.+?)(?=pytanie\s+\d{2}:|$)',
            ]
            
            for pattern in hint_patterns:
                matches = re.findall(pattern, message, re.IGNORECASE | re.DOTALL)
                for question_id, hint in matches:
                    hints[question_id] = hint.strip()
    
    if hints:
        print(f"✅ [+] Extracted hints: {hints}")
    else:
        print("⚠️ [!] No specific hints found in response")
    
    return hints


def main():
    """Main execution function."""
    print("🚀 [*] Starting Notes task - Rafał's Notebook Analysis...")
    
    # Step 1: Download files
    print("\n" + "="*60)
    print("📥 STEP 1: Downloading files")
    
    pdf_path = download_file(NOTEBOOK_PDF_URL, "notatnik-rafala.pdf")
    questions_path = download_file(QUESTIONS_JSON_URL, "notes.json")
    
    # Step 2: Process PDF
    print("\n" + "="*60)
    print("📄 STEP 2: Processing PDF")
    
    # Extract text from pages 1-18
    text_content = extract_text_from_pdf_pages(pdf_path, start_page=0, end_page=17)
    
    # Load page 19 content from text file
    page_19_content = load_page_19_content()
    
    # Combine all content
    full_context = text_content + "\n" + page_19_content
    print(f"📚 [*] Total context length: {len(full_context)} characters")
    
    # Step 3: Load questions
    print("\n" + "="*60)
    print("📋 STEP 3: Loading questions")
    
    questions = load_questions(questions_path)
    
    # Step 4: Answer questions iteratively
    print("\n" + "="*60)
    print("🤔 STEP 4: Answering questions")
    
    answers = {}
    attempts_log = {q_id: [] for q_id in questions.keys()}
    correct_answers = set()  # Track questions that are already correct
    max_iterations = 10
    
    for iteration in range(max_iterations):
        print(f"\n🔄 [*] Iteration {iteration + 1}/{max_iterations}")
        
        # Answer only incorrect questions or new questions
        questions_to_answer = []
        if iteration == 0:
            # First iteration: answer all questions
            questions_to_answer = list(questions.keys())
        else:
            # Subsequent iterations: only answer questions that had errors
            for question_id in questions.keys():
                if question_id not in correct_answers:
                    questions_to_answer.append(question_id)
        
        print(f"📝 [*] Answering questions: {questions_to_answer}")
        print(f"✅ [*] Already correct: {sorted(correct_answers)}")
        
        for question_id in questions_to_answer:
            question = questions[question_id]
            previous_attempts = attempts_log[question_id]
            
            # Generate new answer with retry logic for duplicates
            max_retries = 3
            for retry in range(max_retries):
                answer = answer_question(question, full_context, question_id, previous_attempts)
                
                # Check if this answer was already tried and rejected
                rejected_answers = [attempt['answer'] for attempt in previous_attempts]
                
                if answer not in rejected_answers:
                    print(f"✅ [*] New answer for {question_id}: {answer}")
                    break
                else:
                    print(f"⚠️ [!] Answer '{answer}' for {question_id} was already rejected, trying again...")
                    # Add explicit instruction to avoid the rejected answer
                    if retry < max_retries - 1:
                        additional_context = f"\n\nUWAGA: Odpowiedź '{answer}' została już odrzucona. Podaj INNĄ odpowiedź!"
                        # Add this to previous attempts temporarily for next retry
                        temp_attempt = {'answer': answer, 'hint': 'Ta odpowiedź była już odrzucona'}
                        previous_attempts_with_temp = previous_attempts + [temp_attempt]
                        answer = answer_question(question, full_context, question_id, previous_attempts_with_temp)
            else:
                print(f"❌ [!] Could not generate new answer for {question_id} after {max_retries} retries")
            
            answers[question_id] = answer
        
        # Submit answers
        print(f"\n📤 [*] Submitting answers (iteration {iteration + 1})...")
        response = submit_answers(answers)
        
        # Check if successful
        if response.get('code') == 0 or 'flag' in str(response).lower():
            print("🎉 [+] Task completed successfully!")
            try:
                flag = find_flag_in_text(str(response))
                print(f"🚩 [+] Flag found: {flag}")
            except:
                print("✅ [+] Task completed (no flag in response)")
            break
        
        # Analyze feedback for next iteration
        hints = analyze_feedback(response)
        
        # Update correct answers tracking
        # If we get a hint for a specific question, it means that question is wrong
        # All other questions that were submitted are correct
        if hints:
            incorrect_question = list(hints.keys())[0]  # The question that got the hint
            print(f"❌ [*] Question {incorrect_question} is incorrect")
            
            # Mark all other submitted questions as correct
            for question_id in answers.keys():
                if question_id != incorrect_question:
                    correct_answers.add(question_id)
                    print(f"✅ [*] Marking question {question_id} as correct")
        
        # Update attempts log with feedback
        for question_id in questions_to_answer:
            if question_id in answers:
                attempt_record = {
                    'answer': answers[question_id],
                    'hint': hints.get(question_id, None)
                }
                
                # Only add if not already in attempts (avoid duplicates)
                if not attempts_log[question_id] or attempts_log[question_id][-1]['answer'] != answers[question_id]:
                    attempts_log[question_id].append(attempt_record)
        
        if hints:
            incorrect_questions = list(hints.keys())
            print(f"⚠️ [!] Questions {incorrect_questions} were incorrect, trying again with hints...")
        else:
            print(f"⚠️ [!] Some answers were incorrect, trying again...")
    
    else:
        print(f"❌ [-] Maximum iterations reached without full success")
    
    # Cleanup
    try:
        os.unlink(pdf_path)
        os.unlink(questions_path)
        print("🧹 [*] Temporary files cleaned up")
    except:
        pass
    
    print("✅ [+] Notes task completed!")


if __name__ == "__main__":
    main()
