"""
Task S05E02: GPS - Agent Reconstruction

This script reconstructs a GPS tracking agent by:
1. Downloading GPS logs and analyzing them to understand the original agent's purpose
2. Downloading question data from centrala to see what's being asked
3. Extracting location from the question to query places API
4. Finding people in that location using places API
5. Getting userID for each person from database API
6. Using GPS API with userID to get coordinates 
7. Excluding Barbara and submitting coordinates to centrala
"""
import os
import sys
import json
from typing import Dict, List, Tuple, Optional
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

# GPS task URLs - will be formatted with API_KEY
GPS_LOGS_URL = os.getenv("GPS_LOGS_URL").format(API_KEY=API_KEY)
GPS_QUESTION_URL = os.getenv("GPS_QUESTION_URL").format(API_KEY=API_KEY)

# API endpoints from previous tasks
DATABASE_API_URL = os.getenv("DATABASE_API_URL")  # From S03E03
PLACES_API_URL = os.getenv("PLACES_API_URL")      # From S03E04
GPS_API_URL = os.getenv("GPS_API_URL")

def download_gps_logs() -> str:
    """Download GPS agent logs for analysis."""
    print("📋 [*] Downloading GPS agent logs...")
    
    try:
        response = make_request(GPS_LOGS_URL, method="get")
        logs = response.text
        
        print(f"✅ [+] Downloaded logs ({len(logs)} characters)")
        print(f"📋 [*] Logs preview: {logs[:500]}...")
        
        return logs
    
    except Exception as e:
        print(f"❌ [-] Error downloading GPS logs: {str(e)}")
        raise


def download_gps_question() -> Dict:
    """Download GPS question data from centrala."""
    print("❓ [*] Downloading GPS question...")
    
    try:
        response = make_request(GPS_QUESTION_URL, method="get")
        question_data = response.json()
        
        print(f"✅ [+] Downloaded GPS question")
        print(f"📋 [*] Question data: {json.dumps(question_data, ensure_ascii=False, indent=2)}")
        
        return question_data
    
    except Exception as e:
        print(f"❌ [-] Error downloading GPS question: {str(e)}")
        raise


def analyze_gps_logs(logs: str) -> str:
    """Analyze GPS logs using LLM to understand the agent's purpose."""
    print("🔍 [*] Analyzing GPS logs to understand agent purpose...")
    
    prompt = f"""Przeanalizuj poniższe logi GPS agenta i odpowiedz na pytania:

LOGI GPS:
{logs}

PYTANIA:
1. Jaki był cel tego agenta GPS?
2. Co agent robił i jak działał?
3. Jakie dane przetwarzał?
4. W jakiej kolejności wykonywał operacje?

Odpowiedz krótko i konkretnie w języku polskim."""
    
    try:
        analysis = ask_llm(
            question=prompt,
            api_key=OPENAI_API_KEY,
            model="gpt-4o",
            context="Analizujesz logi systemu GPS. Bądź precyzyjny i konkretny."
        )
        
        print(f"🤖 [*] Agent analysis:")
        print(f"📋 {analysis}")
        
        return analysis
    
    except Exception as e:
        print(f"❌ [-] Error analyzing logs: {str(e)}")
        return "Nie udało się przeanalizować logów"


def extract_location_from_question(question_data: Dict) -> Optional[str]:
    """Extract location/city from question data using LLM."""
    print("🔍 [*] Extracting location from question...")
    
    prompt = f"""Z poniższych danych pytania wyciągnij nazwę miejscowości/miasta, o które chodzi.

DANE PYTANIA:
{json.dumps(question_data, ensure_ascii=False, indent=2)}

Zwróć tylko nazwę miejscowości/miasta WIELKIMI LITERAMI, bez polskich znaków.
Jeśli nie ma żadnej miejscowości, odpowiedz "BRAK".

MIEJSCOWOŚĆ:"""
    
    try:
        location = ask_llm(
            question=prompt,
            api_key=OPENAI_API_KEY,
            model="gpt-4o",
            context="Wyciągnij tylko nazwę miejscowości z danych. Bądź precyzyjny."
        )
        
        location = location.strip().upper()
        if location == "BRAK":
            return None
            
        print(f"📍 [*] Extracted location: {location}")
        return location
    
    except Exception as e:
        print(f"❌ [-] Error extracting location: {str(e)}")
        return None


def get_people_in_location(location: str) -> List[str]:
    """Get list of people seen in a location using places API."""
    print(f"👥 [*] Getting people in location: {location}")
    
    payload = {
        "apikey": API_KEY,
        "query": location
    }
    
    try:
        response = make_request(
            PLACES_API_URL,
            method="post",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        result = response.json()
        print(f"📋 [*] Places API response: {json.dumps(result, ensure_ascii=False, indent=2)}")
        
        # Extract people from response
        people = []
        if isinstance(result, dict) and "message" in result:
            people = result["message"].split()
        elif isinstance(result, list):
            people = result
        
        # Filter out Barbara
        people = [person for person in people if person.upper() != "BARBARA"]
        
        print(f"✅ [+] Found {len(people)} people in {location}: {people}")
        return people
    
    except Exception as e:
        print(f"❌ [-] Error getting people in location: {str(e)}")
        return []


def execute_database_query(query: str) -> Dict:
    """Execute SQL query against the database API."""
    print(f"🗄️ [*] Executing database query: {query}")
    
    payload = {
        "task": "database",
        "apikey": API_KEY,
        "query": query
    }
    
    try:
        response = make_request(
            DATABASE_API_URL,
            method="post",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        result = response.json()
        print(f"✅ [+] Database query executed")
        print(f"📊 [*] Result: {json.dumps(result, ensure_ascii=False, indent=2)}")
        
        return result
    
    except Exception as e:
        print(f"❌ [-] Error executing database query: {str(e)}")
        return {"error": str(e)}


def get_user_id_from_database(person_name: str) -> Optional[int]:
    """Get userID for a person from database."""
    print(f"👤 [*] Getting userID for: {person_name}")
    
    # Try different query variations
    queries = [
        f"SELECT id FROM users WHERE username = '{person_name}'",
        f"SELECT id FROM users WHERE username = '{person_name.upper()}'",
        f"SELECT id FROM users WHERE username = '{person_name.lower()}'",
        f"SELECT id FROM users WHERE UPPER(username) = '{person_name.upper()}'",
    ]
    
    for query in queries:
        try:
            result = execute_database_query(query)
            
            if result and "reply" in result and result["reply"]:
                data = result["reply"]
                if isinstance(data, list) and len(data) > 0:
                    row = data[0]
                    if "id" in row:
                        user_id = int(row["id"])
                        print(f"✅ [+] Found userID for {person_name}: {user_id}")
                        return user_id
        
        except Exception as e:
            print(f"❌ [-] Query failed: {query} - {str(e)}")
            continue
    
    print(f"❌ [-] No userID found for {person_name}")
    return None


def get_gps_coordinates(user_id: int) -> Optional[Tuple[float, float]]:
    """Get GPS coordinates for a userID using GPS API."""
    print(f"🛰️ [*] Getting GPS coordinates for userID: {user_id}")
    
    payload = {
        "apikey": API_KEY,
        "userID": user_id
    }
    
    try:
        response = make_request(
            GPS_API_URL,
            method="post",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        result = response.json()
        print(f"📍 [*] GPS API response: {json.dumps(result, ensure_ascii=False, indent=2)}")
        
        # Extract coordinates from response
        if isinstance(result, dict):
            lat = None
            lon = None
            
            # Try different possible response formats
            if "lat" in result and "lon" in result:
                lat = float(result["lat"])
                lon = float(result["lon"])
            elif "latitude" in result and "longitude" in result:
                lat = float(result["latitude"])
                lon = float(result["longitude"])
            elif "message" in result:
                # Try to parse coordinates from message
                message = result["message"]
                if isinstance(message, dict):
                    if "lat" in message and "lon" in message:
                        lat = float(message["lat"])
                        lon = float(message["lon"])
            
            if lat is not None and lon is not None:
                print(f"✅ [+] Found coordinates for userID {user_id}: ({lat}, {lon})")
                return (lat, lon)
        
        print(f"❌ [-] Could not extract coordinates from GPS API response")
        return None
    
    except Exception as e:
        print(f"❌ [-] Error getting GPS coordinates for userID {user_id}: {str(e)}")
        return None


def process_gps_task(question_data: Dict) -> Dict[str, Dict[str, float]]:
    """Process the main GPS task logic."""
    print("🎯 [*] Processing GPS task...")
    
    # Step 1: Extract location from question
    location = extract_location_from_question(question_data)
    if not location:
        print("❌ [-] Could not extract location from question")
        return {}
    
    # Step 2: Get people in that location
    people = get_people_in_location(location)
    if not people:
        print("❌ [-] No people found in location")
        return {}
    
    # Step 3: For each person, get userID and coordinates
    results = {}
    
    for person in people:
        print(f"\n🎯 [*] Processing person: {person}")
        
        # Get userID from database
        user_id = get_user_id_from_database(person)
        if user_id is None:
            print(f"❌ [-] Could not find userID for {person} - skipping")
            continue
        
        # Get GPS coordinates using userID
        coords = get_gps_coordinates(user_id)
        if coords:
            lat, lon = coords
            results[person] = {
                "lat": lat,
                "lon": lon
            }
            print(f"✅ [+] Added coordinates for {person}")
        else:
            print(f"❌ [-] Could not get coordinates for {person}")
    
    print(f"✅ [+] Final results: {json.dumps(results, indent=2)}")
    return results


def submit_gps_answer(coordinates: Dict[str, Dict[str, float]]) -> Dict:
    """Submit GPS coordinates to centrala."""
    print("📤 [*] Submitting GPS coordinates...")
    
    payload = {
        "task": "gps",
        "apikey": API_KEY,
        "answer": coordinates
    }
    
    print(f"📋 [*] Payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")
    
    try:
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
    
    except Exception as e:
        print(f"❌ [-] Error submitting GPS answer: {str(e)}")
        return {"error": str(e)}


def main():
    """Main execution function."""
    print("🚀 [*] Starting GPS task - Agent Reconstruction...")
    
    # Step 1: Download and analyze logs
    print("\n" + "="*60)
    print("📋 STEP 1: Analyzing GPS agent logs")
    
    logs = download_gps_logs()
    analysis = analyze_gps_logs(logs)
    
    # Step 2: Download question and process
    print("\n" + "="*60)
    print("❓ STEP 2: Processing GPS question")
    
    question_data = download_gps_question()
    
    # Step 3: Execute agent logic
    print("\n" + "="*60)
    print("🎯 STEP 3: Executing reconstructed agent logic")
    print("📋 [*] Agent logic:")
    print("    1. Extract location from question")
    print("    2. Get people in that location (places API)")
    print("    3. For each person, find userID (database API)")
    print("    4. Get GPS coordinates using userID (GPS API)")
    print("    5. Exclude Barbara from results")
    print("    6. Submit coordinates to centrala")
    
    coordinates = process_gps_task(question_data)
    
    if not coordinates:
        print("❌ [-] No coordinates found, cannot proceed")
        sys.exit(1)
    
    # Step 4: Submit results
    print("\n" + "="*60)
    print("📤 STEP 4: Submitting results")
    
    result = submit_gps_answer(coordinates)
    
    print("\n✅ [+] GPS task completed!")


if __name__ == "__main__":
    main()
