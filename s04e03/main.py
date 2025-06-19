"""
Task S04E03: Softo - Intelligent Website Exploration

This script:
1. Fetches questions from the centrala API
2. Uses an LLM-guided agent to explore the SoftoAI website
3. Finds answers to specific questions through intelligent navigation
4. Submits concise answers to the central server
"""
import os
import sys
import json
import re
from urllib.parse import urljoin, urlparse
from typing import Dict, List, Set, Optional
import requests
from bs4 import BeautifulSoup
import html2text
from dotenv import load_dotenv

# Add parent directory to Python path to allow imports from shared utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import (
    make_request,
    ask_llm,
    find_flag_in_text
)

# Load environment variables
load_dotenv()

# Configuration
API_KEY = os.getenv("API_KEY")
CENTRALA_REPORT_URL = os.getenv("CENTRALA_REPORT_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Softo website configuration
SOFTO_BASE_URL = os.getenv("SOFTO_BASE_URL")
MAX_DEPTH_PER_QUESTION = 5
MAX_PAGES_PER_QUESTION = 10


class WebCrawler:
    """Intelligent web crawler guided by LLM."""
    
    def __init__(self):
        self.visited_pages = {}  # URL -> markdown content cache
        self.html_converter = html2text.HTML2Text()
        self.html_converter.ignore_links = False
        self.html_converter.ignore_images = True
        
    def fetch_page(self, url: str) -> Optional[str]:
        """Fetch and convert a page to markdown, with caching."""
        if url in self.visited_pages:
            print(f"📋 [*] Using cached content for: {url}")
            return self.visited_pages[url]
        
        print(f"🌐 [*] Fetching page: {url}")
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            # Convert HTML to markdown to save tokens
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            html_content = str(soup)
            markdown_content = self.html_converter.handle(html_content)
            
            # Cache the content
            self.visited_pages[url] = markdown_content
            
            print(f"✅ [+] Page fetched and converted to markdown ({len(markdown_content)} chars)")
            return markdown_content
            
        except Exception as e:
            print(f"❌ [-] Error fetching page {url}: {str(e)}")
            return None
    
    def extract_links(self, markdown_content: str, base_url: str) -> List[str]:
        """Extract and normalize links from markdown content."""
        # Find markdown links [text](url)
        link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        matches = re.findall(link_pattern, markdown_content)
        
        links = []
        for text, url in matches:
            # Skip anchor links, email links, etc.
            if url.startswith('#') or url.startswith('mailto:') or url.startswith('tel:'):
                continue
            
            # Clean up the URL - remove any quotes or extra text
            url = url.strip().strip('"').strip("'")
            # Take only the URL part before any space or quote
            url = url.split()[0] if ' ' in url else url
            
            # Convert relative URLs to absolute
            absolute_url = urljoin(base_url, url)
            
            # Only include links within the same domain
            if urlparse(absolute_url).netloc == urlparse(SOFTO_BASE_URL).netloc:
                links.append(absolute_url)
        
        # Remove duplicates while preserving order
        unique_links = []
        for link in links:
            if link not in unique_links:
                unique_links.append(link)
        
        return unique_links
    
    def check_for_answer(self, content: str, question: str) -> Optional[str]:
        """Check if the current page contains an answer to the question."""
        print(f"🔍 [*] Checking if page contains answer to question...")
        
        system_prompt = """Jesteś ekspertem w analizie treści stron internetowych. Twoim zadaniem jest sprawdzenie, czy podana treść strony zawiera odpowiedź na konkretne pytanie.

INSTRUKCJE:
1. Przeanalizuj CAŁĄ treść strony dokładnie
2. Sprawdź czy można znaleźć konkretną odpowiedź na zadane pytanie
3. Jeśli TAK - podaj zwięzłą, konkretną odpowiedź (tylko samą informację, bez dodatkowych słów)
4. Jeśli NIE - odpowiedz "NIE"

Przykłady dobrych odpowiedzi:
- Na pytanie "Jaki jest email kontaktowy?" → "kontakt@firma.com" 
- Na pytanie "Kto jest CEO?" → "Jan Kowalski"
- Na pytanie "Ile kosztuje produkt X?" → "299 PLN"
- Na pytanie "Jaki jest adres interfejsu?" → "https://robots.banan.com"
- Na pytanie "Jakie certyfikaty ISO?" → "ISO 9001, ISO 14001"

NIE dodawaj słów jak "Email to:", "Odpowiedź to:", tylko podaj samą informację."""
        
        # Use more content for answer checking - split into chunks if too long
        max_content_length = 8000
        if len(content) > max_content_length:
            # Take first part which usually contains main content
            content_to_analyze = content[:max_content_length] + "..."
        else:
            content_to_analyze = content
        
        user_prompt = f"""Treść strony:
{content_to_analyze}

Pytanie: {question}

Czy na tej stronie można znaleźć odpowiedź na to pytanie? Jeśli tak, podaj zwięzłą odpowiedź. Jeśli nie, odpowiedz "NIE"."""
        
        try:
            response = ask_llm(
                question=user_prompt,
                api_key=OPENAI_API_KEY,
                model="gpt-4o-mini",
                context=system_prompt
            )
            
            response = response.strip()
            print(f"✅ [+] LLM response: '{response}'")
            
            if response.upper() != "NIE":
                return response
            return None
            
        except Exception as e:
            print(f"❌ [-] Error checking for answer: {str(e)}")
            return None
    
    def select_best_link(self, content: str, question: str, available_links: List[str]) -> Optional[str]:
        """Use LLM to select the best link to explore next."""
        if not available_links:
            return None
        
        print(f"🎯 [*] Selecting best link from {len(available_links)} options...")
        
        # Show available links for debugging
        print(f"📋 [*] Available links:")
        for i, link in enumerate(available_links, 1):
            print(f"    {i}. {link}")
        
        # Prepare links for the prompt
        links_text = "\n".join([f"{i+1}. {link}" for i, link in enumerate(available_links)])
        
        system_prompt = """Jesteś ekspertem w nawigacji po stronach internetowych. Twoim zadaniem jest wybór najlepszego linku, który prawdopodobnie zawiera odpowiedź na zadane pytanie.

INSTRUKCJE:
1. Przeanalizuj treść strony i dostępne linki
2. Wybierz link, który najlepiej pasuje do tematu pytania
3. Odpowiedz TYLKO numerem wybranego linku (np. "3")
4. Zawsze wybierz jakiś link - jeśli nie jesteś pewien, wybierz najbardziej prawdopodobny

Szukaj linków związanych z:
- Portfolio/Realizacje (dla pytań o konkretne projekty klientów)
- Kontaktami (dla pytań o email, telefon, adres)
- O nas/About (dla pytań o firmie, zespole, historii, certyfikatach)
- Produktach/Usługach (dla pytań o ofertę)
- Cenach/Pricing (dla pytań o koszty)"""
        
        user_prompt = f"""Treść strony:
{content[:3000]}...

Pytanie: {question}

Dostępne linki:
{links_text}

Który link ma największą szansę zawierać odpowiedź na to pytanie? Odpowiedz tylko numerem."""
        
        try:
            response = ask_llm(
                question=user_prompt,
                api_key=OPENAI_API_KEY,
                model="gpt-4o-mini",
                context=system_prompt
            )
            
            print(f"🤖 [*] LLM link selection response: '{response}'")
            
            # Extract number from response
            match = re.search(r'\b(\d+)\b', response.strip())
            if match:
                link_num = int(match.group(1))
                if 1 <= link_num <= len(available_links):
                    selected_link = available_links[link_num - 1]
                    print(f"✅ [+] Selected link {link_num}: {selected_link}")
                    return selected_link
            
            # If no valid number, try to select first available link
            if available_links:
                print(f"⚠️ [!] Invalid link selection '{response}', using first available link")
                return available_links[0]
            
            return None
            
        except Exception as e:
            print(f"❌ [-] Error selecting link: {str(e)}")
            # Fallback to first link if available
            return available_links[0] if available_links else None
    
    def find_answer(self, question: str) -> Optional[str]:
        """Find answer to a question by exploring the website."""
        print(f"\n🔍 [*] Searching for answer to: {question}")
        
        visited_urls = set()
        pages_visited = 0
        current_url = SOFTO_BASE_URL
        
        for depth in range(MAX_DEPTH_PER_QUESTION):
            if pages_visited >= MAX_PAGES_PER_QUESTION:
                print(f"⚠️ [!] Reached maximum pages limit ({MAX_PAGES_PER_QUESTION})")
                break
            
            if current_url in visited_urls:
                print(f"⚠️ [!] Already visited {current_url}, stopping")
                break
            
            print(f"\n📍 [*] Depth {depth + 1}, exploring: {current_url}")
            visited_urls.add(current_url)
            pages_visited += 1
            
            # Fetch page content
            content = self.fetch_page(current_url)
            if not content:
                break
            
            # Check if this page contains the answer
            answer = self.check_for_answer(content, question)
            if answer:
                print(f"🎉 [+] Found answer: {answer}")
                return answer
            
            # Extract links and select the best one
            links = self.extract_links(content, current_url)
            unvisited_links = [link for link in links if link not in visited_urls]
            
            if not unvisited_links:
                print(f"⚠️ [!] No unvisited links found")
                break
            
            next_url = self.select_best_link(content, question, unvisited_links)
            if not next_url:
                print(f"⚠️ [!] No suitable link selected")
                break
            
            current_url = next_url
        
        print(f"❌ [-] Could not find answer after {pages_visited} pages")
        return None


def fetch_questions():
    """Fetch questions from the centrala API."""
    print("📥 [*] Fetching questions from centrala...")
    
    questions_url = f"https://c3ntrala.ag3nts.org/data/{API_KEY}/softo.json"
    
    try:
        response = make_request(questions_url, method="get")
        questions = response.json()
        
        print(f"✅ [+] Fetched questions:")
        for key, question in questions.items():
            print(f"    {key}: {question}")
        
        return questions
    
    except Exception as e:
        print(f"❌ [-] Error fetching questions: {str(e)}")
        return None


def submit_answers(answers: Dict[str, str]):
    """Submit answers to the central server."""
    print("📤 [*] Submitting answers...")
    
    payload = {
        "task": "softo",
        "apikey": API_KEY,
        "answer": answers
    }
    
    print(f"📦 [*] Submission payload:")
    print(f"    task: {payload['task']}")
    print(f"    apikey: {payload['apikey'][:10]}...")
    print(f"    answer: {payload['answer']}")
    
    try:
        response = make_request(
            CENTRALA_REPORT_URL,
            method="post",
            json=payload,
            headers={"Content-Type": "application/json; charset=utf-8"}
        )
        
        print(f"✅ [+] Answers submitted successfully")
        print(f"📋 [*] Response: {response.text}")
        
        # Check for flag in response
        try:
            flag = find_flag_in_text(response.text)
            print(f"🚩 [+] Flag found: {flag}")
        except Exception:
            print(f"⚠️ [!] No flag found in response")
        
        return response.json()
    
    except Exception as e:
        print(f"❌ [-] Error submitting answers: {str(e)}")
        return None


def main():
    """Main execution function."""
    print("🚀 [*] Starting Softo task...")
    
    # Step 1: Fetch questions
    questions = fetch_questions()
    if not questions:
        print("❌ [-] Could not fetch questions")
        sys.exit(1)
    
    # Step 2: Create web crawler
    crawler = WebCrawler()
    
    # Step 3: Find answers for each question
    answers = {}
    
    for question_id, question_text in questions.items():
        print(f"\n{'='*60}")
        print(f"🔍 [*] Processing question {question_id}: {question_text}")
        
        answer = crawler.find_answer(question_text)
        if answer:
            answers[question_id] = answer
            print(f"✅ [+] Answer for {question_id}: {answer}")
        else:
            print(f"❌ [-] Could not find answer for {question_id}")
            answers[question_id] = "Nie znaleziono odpowiedzi"
    
    print(f"\n📊 [*] Final answers:")
    for qid, answer in answers.items():
        print(f"    {qid}: {answer}")
    
    # Step 4: Submit answers
    if answers:
        result = submit_answers(answers)
        print("✅ [+] Softo task completed!")
    else:
        print("❌ [-] No answers found")


if __name__ == "__main__":
    main()
