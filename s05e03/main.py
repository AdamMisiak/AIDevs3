"""
Task S05E03: Time Lock - Rafał's 6-Second Challenge

This script solves Rafał's time-locked computer challenge by:
1. Sending password to get initial hash from Rafał's endpoint
2. Signing the hash to get timestamp, signature and two URLs
3. Rapidly processing tasks from both URLs in parallel
4. Combining results and submitting within 6 seconds
5. Using maximum speed optimization with concurrent processing
"""
import os
import sys
import json
import time
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor

# Add parent directory to Python path for utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import make_request, ask_llm, find_flag_in_text

# Load environment variables
load_dotenv()

# Configuration
API_KEY = os.getenv("API_KEY")
CENTRALA_REPORT_URL = os.getenv("CENTRALA_REPORT_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Rafał's endpoint configuration
QUESTION_5_ENDPOINT = os.getenv("QUESTION_5_ENDPOINT")
QUESTION_5_PASSWORD = os.getenv("QUESTION_5_PASSWORD")

# Speed optimization settings
FAST_MODEL = "gpt-4o"  # Fastest OpenAI model
MAX_WORKERS = 4  # For parallel processing
TIMEOUT_SECONDS = 5  # Leave 1 second buffer


class TimeConstrainedProcessor:
    """High-speed processor for time-critical tasks."""
    
    def __init__(self):
        self.start_time = None
        self.executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)
    
    def start_timer(self):
        """Start the 6-second countdown."""
        self.start_time = time.time()
        print(f"⏰ [*] Started 6-second countdown at {self.start_time}")
    
    def get_elapsed_time(self) -> float:
        """Get elapsed time since start."""
        if self.start_time is None:
            return 0.0
        return time.time() - self.start_time
    
    def get_remaining_time(self) -> float:
        """Get remaining time in the 6-second window."""
        return max(0.0, 6.0 - self.get_elapsed_time())
    
    def check_time_limit(self) -> bool:
        """Check if we're still within the 6-second limit."""
        elapsed = self.get_elapsed_time()
        remaining = 6.0 - elapsed
        
        if remaining <= 0:
            print(f"❌ [!] TIME LIMIT EXCEEDED: {elapsed:.2f}s elapsed")
            return False
        
        print(f"⏱️  [*] {elapsed:.2f}s elapsed, {remaining:.2f}s remaining")
        return True


def get_initial_hash() -> str:
    """Get initial hash by sending password to Rafał's endpoint."""
    print("🔐 [*] Getting initial hash from Rafał's endpoint...")
    
    payload = {
        "password": QUESTION_5_PASSWORD
    }
    
    try:
        response = make_request(
            QUESTION_5_ENDPOINT,
            method="post",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        result = response.json()
        print(f"📋 [*] Password response: {json.dumps(result, indent=2)}")
        
        # Extract hash from response
        if isinstance(result, dict) and "message" in result:
            hash_value = result["message"]
            print(f"🔑 [*] Received hash: {hash_value}")
            return hash_value
        elif isinstance(result, str) and len(result) == 32:
            print(f"🔑 [*] Received hash: {result}")
            return result
        else:
            print(f"❌ [-] Unexpected response format: {result}")
            raise Exception("Could not extract hash from response")
    
    except Exception as e:
        print(f"❌ [-] Error getting initial hash: {str(e)}")
        raise


def sign_hash_and_get_challenge(hash_value: str) -> Dict:
    """Sign hash and get timestamp, signature, and challenge URLs."""
    print("✍️ [*] Signing hash to get challenge data...")
    
    payload = {
        "sign": hash_value
    }
    
    try:
        response = make_request(
            QUESTION_5_ENDPOINT,
            method="post",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        result = response.json()
        print(f"📋 [*] Sign response: {json.dumps(result, indent=2)}")
        
        return result
    
    except Exception as e:
        print(f"❌ [-] Error signing hash: {str(e)}")
        raise


def fetch_url_content(url: str) -> Dict:
    """Fetch content from a URL quickly."""
    print(f"🌐 [*] Fetching content from: {url}")
    
    try:
        response = make_request(url, method="get", timeout=2)
        data = response.json()
        print(f"📋 [*] Fetched data from {url}: {json.dumps(data, ensure_ascii=False, indent=2)}")
        return data
    
    except Exception as e:
        print(f"❌ [-] Error fetching {url}: {str(e)}")
        return {}


def extract_url_from_task(task: str) -> str:
    """Extract URL from task description if present."""
    import re
    url_pattern = r'https?://[^\s\'"<>]+'
    match = re.search(url_pattern, task)
    return match.group(0) if match else ""


def clean_html_content(html_content: str) -> str:
    """Extract clean text from HTML content."""
    try:
        try:
            from bs4 import BeautifulSoup
            print(f"✅ [*] BeautifulSoup imported successfully")
        except ImportError:
            print(f"❌ [-] BeautifulSoup not available, using regex fallback")
            raise ImportError("BeautifulSoup not available")
        
        import re
        
        print(f"🧹 [*] Cleaning HTML content ({len(html_content)} chars)")
        
        soup = BeautifulSoup(html_content, 'html.parser')
        print(f"✅ [*] HTML parsed successfully")
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Get text content
        text = soup.get_text()
        
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        clean_text = '\n'.join(chunk for chunk in chunks if chunk)
        
        print(f"🧹 [*] Extracted {len(clean_text)} chars of clean text")
        
        # Also try to find any hidden content in data attributes
        hidden_elements = soup.find_all(attrs=lambda x: x and any('data-' in attr for attr in x.keys()))
        hidden_content = []
        
        for element in hidden_elements:
            for attr_name, attr_value in element.attrs.items():
                if attr_name.startswith('data-') and isinstance(attr_value, str):
                    print(f"🔍 [*] Found {attr_name}: {len(attr_value)} chars")
                    hidden_content.append(f"Hidden {attr_name}: {attr_value}")
                    
                    # Try to decode potential Unicode escapes
                    if len(attr_value) > 50:  # Likely encoded content
                        try:
                            # This looks like Unicode with special characters
                            # Let's try to clean it up
                            # Remove zero-width characters and special Unicode
                            cleaned = re.sub(r'[\u200b-\u200f\ufeff\u2060-\u2064\u206a-\u206f\ue000-\uf8ff\U000e0000-\U000e007f]', '', attr_value)
                            if cleaned != attr_value:
                                hidden_content.append(f"Cleaned {attr_name}: {cleaned}")
                            
                            # Try various decoding approaches
                            for encoding_name, method in [
                                ("UTF-8 normalize", lambda x: x.encode('utf-8').decode('utf-8')),
                                ("ASCII filter", lambda x: ''.join(c for c in x if ord(c) < 128)),
                                ("Printable only", lambda x: ''.join(c for c in x if c.isprintable())),
                            ]:
                                try:
                                    decoded = method(attr_value)
                                    if decoded and decoded != attr_value:
                                        hidden_content.append(f"{encoding_name} {attr_name}: {decoded}")
                                except:
                                    pass
                        except Exception as decode_error:
                            print(f"❌ [-] Decode error for {attr_name}: {decode_error}")
        
        if hidden_content:
            clean_text += "\n\nHIDDEN DATA:\n" + "\n".join(hidden_content)
            print(f"🔍 [*] Added {len(hidden_content)} hidden data items")
        
        return clean_text
        
    except Exception as e:
        print(f"❌ [-] Error cleaning HTML: {str(e)}")
        # Fallback: simple regex cleanup
        try:
            import re
            print(f"🔧 [*] Using regex fallback for HTML cleaning")
            
            # First try to extract data-wtf content
            wtf_match = re.search(r'data-wtf[^>]*>([^<]*)', html_content)
            hidden_data = ""
            if wtf_match:
                wtf_content = wtf_match.group(1)
                print(f"🔍 [*] Found data-wtf content: {len(wtf_content)} chars")
                print(f"🔍 [*] WTF content preview: {wtf_content[:100]}...")
                
                # Try to decode this mysterious content
                hidden_data = f"\n\nHIDDEN WTF DATA: {wtf_content}"
                
                # Try to extract readable text
                readable_chars = ''.join(c for c in wtf_content if c.isprintable() and ord(c) < 128)
                if readable_chars:
                    hidden_data += f"\nReadable chars from WTF: {readable_chars}"
            
            # Remove HTML tags
            text = re.sub(r'<[^>]+>', '', html_content)
            # Clean up whitespace  
            text = re.sub(r'\s+', ' ', text).strip()
            
            # Add hidden data if found
            if hidden_data:
                text += hidden_data
                
            print(f"🔧 [*] Regex cleanup complete: {len(text)} chars")
            return text
        except Exception as fallback_error:
            print(f"❌ [-] Regex fallback failed: {fallback_error}")
            return html_content


def fetch_additional_data_if_needed(task: str) -> str:
    """Fetch additional data from URL if task contains one."""
    url = extract_url_from_task(task)
    if not url:
        return ""
    
    print(f"🌐 [*] Found URL in task, fetching: {url}")
    
    try:
        response = make_request(url, method="get", timeout=3)
        content = response.text
        print(f"📄 [*] Fetched {len(content)} characters from {url}")
        return content
    except Exception as e:
        print(f"❌ [-] Error fetching {url}: {str(e)}")
        return ""


def process_task_quickly(task_data: Dict) -> str:
    """Process a single task as quickly as possible."""
    if not task_data:
        return ""
    
    task = task_data.get("task", "")
    data = task_data.get("data", "")
    
    print(f"🎯 [*] Processing task: {task}")
    print(f"📊 [*] Data: {data}")
    
    # Check if task contains URL for additional data
    additional_data = fetch_additional_data_if_needed(task)
    
    # Create prompt with or without additional data
    if additional_data:
        prompt = f"""ZADANIE: {task}
PYTANIA: {data}
DODATKOWE DANE Z URL:
{additional_data[:2000]}...

Na podstawie dodatkowych danych odpowiedz na pytania. Odpowiedz BARDZO KRÓTKO po polsku."""
    else:
        prompt = f"""ZADANIE: {task}
DANE: {data}

Odpowiedz BARDZO KRÓTKO po polsku. Tylko wynik, bez wyjaśnień."""
    
    try:
        # Use fastest model and minimal context
        result = ask_llm(
            question=prompt,
            api_key=OPENAI_API_KEY,
            model=FAST_MODEL,
            context="Odpowiadaj ultra-krótko po polsku. Tylko wynik."
        )
        
        result = result.strip()
        print(f"✅ [+] Task result: {result}")
        return result
    
    except Exception as e:
        print(f"❌ [-] Error processing task: {str(e)}")
        return ""


def process_task_with_data(task_data: Dict, additional_data_cache: Dict[str, str]) -> str:
    """Process task with pre-fetched additional data."""
    if not task_data:
        return ""
    
    task = task_data.get("task", "")
    data = task_data.get("data", "")
    
    print(f"🎯 [*] Processing task: {task}")
    print(f"📊 [*] Data: {data}")
    
    # Check if we have additional data for this task
    url = extract_url_from_task(task)
    additional_data = additional_data_cache.get(url, "") if url else ""
    
    # Create prompt with or without additional data
    if additional_data:
        prompt = f"""ZADANIE: {task}
PYTANIA: {data}
DODATKOWE DANE Z URL:
{additional_data[:3000]}...

Na podstawie dodatkowych danych odpowiedz na pytania. Odpowiedz BARDZO KRÓTKO po polsku. Zakazano wnoszenia napojów i posiłków do pomieszczenia z komorą. BNW to Brave New World"""
    else:
        prompt = f"""ZADANIE: {task}
DANE: {data}

Odpowiedz BARDZO KRÓTKO po polsku. Tylko wynik, bez wyjaśnień. Zakazano wnoszenia napojów i posiłków do pomieszczenia z komorą. BNW to Brave New World"""
    
    try:
        # Use fastest model and minimal context
        result = ask_llm(
            question=prompt,
            api_key=OPENAI_API_KEY,
            model=FAST_MODEL,
            context="Odpowiadaj ultra-krótko po polsku. Tylko wynik."
        )
        
        result = result.strip()
        print(f"✅ [+] Task result: {result}")
        return result
    
    except Exception as e:
        print(f"❌ [-] Error processing task: {str(e)}")
        return ""


def process_challenge_parallel(challenge_data: Dict, processor: TimeConstrainedProcessor) -> str:
    """Process challenge data using parallel execution."""
    print("🚀 [*] Processing challenge with parallel execution...")
    
    # Extract message data
    message = challenge_data.get("message", {})
    if not message:
        print("❌ [-] Missing message in challenge data")
        print(f"📋 [DEBUG] challenge_data keys: {list(challenge_data.keys())}")
        return ""
    
    # Extract URLs from challenges array
    challenges = message.get("challenges", [])
    if len(challenges) < 2:
        print("❌ [-] Missing URLs in challenges array")
        print(f"📋 [DEBUG] message keys: {list(message.keys())}")
        print(f"📋 [DEBUG] challenges: {challenges}")
        return ""
    
    url0 = challenges[0]
    url1 = challenges[1]
    
    print(f"🔗 [*] Processing URLs: {url0}, {url1}")
    
    # Fetch both URLs in parallel
    print("📥 [*] Fetching URLs in parallel...")
    with ThreadPoolExecutor(max_workers=2) as url_executor:
        future0 = url_executor.submit(fetch_url_content, url0)
        future1 = url_executor.submit(fetch_url_content, url1)
        
        # Get results
        data0 = future0.result(timeout=3)
        data1 = future1.result(timeout=3)
    
    # Check time
    if not processor.check_time_limit():
        return ""
    
    # Pre-fetch any additional data URLs found in tasks
    print("🌐 [*] Pre-fetching additional data URLs...")
    additional_urls = set()
    
    for data in [data0, data1]:
        task = data.get("task", "")
        url = extract_url_from_task(task)
        if url:
            additional_urls.add(url)
    
    # Fetch additional data in parallel
    additional_data_cache = {}
    if additional_urls:
        with ThreadPoolExecutor(max_workers=len(additional_urls)) as data_executor:
            url_futures = {url: data_executor.submit(make_request, url, "get", timeout=2) 
                          for url in additional_urls}
            
            for url, future in url_futures.items():
                try:
                    response = future.result(timeout=2)
                    raw_content = response.text
                    
                    # Clean HTML content
                    clean_content = clean_html_content(raw_content)
                    additional_data_cache[url] = clean_content
                    
                    print(f"📄 [*] Cached {len(raw_content)} chars raw / {len(clean_content)} chars clean for {url}")
                    print(f"📄 [*] RAW HTML FROM {url}:")
                    print("=" * 80)
                    print(raw_content)
                    print("=" * 80)
                    print(f"📄 [*] CLEANED TEXT FROM {url}:")
                    print("=" * 80)
                    print(clean_content)
                    print("=" * 80)
                except Exception as e:
                    print(f"❌ [-] Failed to fetch {url}: {str(e)}")
    
    # Check time again
    if not processor.check_time_limit():
        return ""
    
    # Process both tasks in parallel with cached data
    print("⚡ [*] Processing tasks in parallel...")
    with ThreadPoolExecutor(max_workers=2) as task_executor:
        future_task0 = task_executor.submit(process_task_with_data, data0, additional_data_cache)
        future_task1 = task_executor.submit(process_task_with_data, data1, additional_data_cache)
        
        # Get results
        result0 = future_task0.result(timeout=3)
        result1 = future_task1.result(timeout=3)
    
    # Combine results
    combined_result = f"{result0}. {result1}"
    print(f"🔗 [*] Combined result: {combined_result}")
    
    return combined_result


def submit_final_answer(challenge_data: Dict, answer: str) -> Dict:
    """Submit final answer to Rafał's endpoint."""
    print("📤 [*] Submitting final answer...")
    
    # Extract message data
    message = challenge_data.get("message", {})
    timestamp = message.get("timestamp", "")
    signature = message.get("signature", "")
    
    payload = {
        "apikey": API_KEY,
        "timestamp": timestamp,
        "signature": signature,
        "answer": answer
    }
    
    print(f"📋 [*] Final payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")
    
    try:
        response = make_request(
            QUESTION_5_ENDPOINT,
            method="post",
            json=payload,
            headers={"Content-Type": "application/json"}
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
    
    except Exception as e:
        print(f"❌ [-] Error submitting final answer: {str(e)}")
        return {"error": str(e)}


def execute_time_challenge() -> bool:
    """Execute the complete time challenge within 6 seconds."""
    processor = TimeConstrainedProcessor()
    
    try:
        # Step 1: Get initial hash (not counted in 6-second timer)
        print("\n" + "="*60)
        print("🔐 STEP 1: Getting initial hash")
        
        hash_value = get_initial_hash()
        
        # Step 2: Start timer and sign hash
        print("\n" + "="*60)
        print("⏰ STEP 2: Starting 6-second challenge")
        
        processor.start_timer()
        
        challenge_data = sign_hash_and_get_challenge(hash_value)
        
        if not processor.check_time_limit():
            return False
        
        # Step 3: Process challenge rapidly
        print("\n" + "="*60)
        print("🚀 STEP 3: Processing challenge at maximum speed")
        
        answer = process_challenge_parallel(challenge_data, processor)
        
        if not processor.check_time_limit():
            return False
        
        if not answer:
            print("❌ [-] No answer generated")
            return False
        
        # Step 4: Submit final answer
        print("\n" + "="*60)
        print("📤 STEP 4: Submitting final answer")
        
        result = submit_final_answer(challenge_data, answer)
        
        elapsed = processor.get_elapsed_time()
        print(f"⏱️  [*] Total time: {elapsed:.2f}s")
        
        if elapsed <= 6.0:
            print("✅ [+] CHALLENGE COMPLETED WITHIN TIME LIMIT!")
            return True
        else:
            print("❌ [-] EXCEEDED TIME LIMIT")
            return False
    
    except Exception as e:
        elapsed = processor.get_elapsed_time()
        print(f"❌ [-] Challenge failed after {elapsed:.2f}s: {str(e)}")
        return False


def main():
    """Main execution function."""
    print("🚀 [*] Starting Rafał's Time Lock Challenge...")
    print("⚡ [*] Maximum speed optimization enabled")
    print(f"🤖 [*] Using fastest model: {FAST_MODEL}")
    print(f"🔧 [*] Parallel workers: {MAX_WORKERS}")
    
    success = execute_time_challenge()
    
    if success:
        print("\n🎉 [+] TIME LOCK CHALLENGE COMPLETED SUCCESSFULLY!")
    else:
        print("\n💥 [-] TIME LOCK CHALLENGE FAILED!")
        sys.exit(1)


if __name__ == "__main__":
    main()
