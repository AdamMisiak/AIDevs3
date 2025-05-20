"""
Task S02E01: Audio Testimonies Analysis

This script:
1. Processes audio testimonies from the 'przesluchania' directory
2. Transcribes audio files using OpenAI's Whisper model
3. Analyzes transcriptions to find the street name of the institute where Professor Maj teaches
4. Submits the answer to the central server
"""
import os
import sys
import json
import re
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

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


def get_audio_files():
    """Get audio files from the przesluchania directory."""
    print("🔍 [*] Looking for audio files in the przesluchania directory...")
    
    # Use absolute path based on script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    audio_dir = os.path.join(script_dir, "przesluchania")
    
    print(f"📂 [*] Looking in directory: {audio_dir}")
    
    # Check if directory exists
    if not os.path.exists(audio_dir):
        print(f"❌ [-] Directory '{audio_dir}' not found. Please make sure it exists.")
        sys.exit(1)
    
    try:
        # Get list of audio files
        audio_files = [os.path.join(audio_dir, file) for file in os.listdir(audio_dir) 
                       if file.endswith(('.m4a', '.mp3', '.wav'))]
        
        if not audio_files:
            print(f"❌ [-] No audio files found in '{audio_dir}' directory.")
            sys.exit(1)
            
        print(f"✅ [+] Found {len(audio_files)} audio files")
        return audio_files
    
    except Exception as e:
        print(f"❌ [-] Error getting audio files: {str(e)}")
        sys.exit(1)


def transcribe_audio(audio_file_path):
    """Transcribe audio file using OpenAI's Whisper model."""
    print(f"🎙️ [*] Transcribing audio: {os.path.basename(audio_file_path)}...")
    
    client = OpenAI(api_key=OPENAI_API_KEY)
    
    try:
        with open(audio_file_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file
            )
        
        print(f"✅ [+] Transcription completed for: {os.path.basename(audio_file_path)}")
        print(transcript.text)
        return transcript.text
    
    except Exception as e:
        print(f"❌ [-] Error transcribing {os.path.basename(audio_file_path)}: {str(e)}")
        return f"ERROR TRANSCRIBING {os.path.basename(audio_file_path)}: {str(e)}"


def analyze_transcriptions(transcriptions):
    """
    Analyze transcriptions to find the street name of the institute 
    where Professor Maj teaches.
    """
    print("🔍 [*] Analyzing transcriptions to find the street name...")
    
    # Prepare a combined text from all transcriptions
    combined_text = ""
    for file_name, transcript in transcriptions.items():
        combined_text += f"\n--- Transkrypcje od {file_name} ---\n{transcript}\n"
    
    # Create prompt with transcriptions embedded
    system_prompt = f"""
    ZADANIE  
    Ustal, PRZY JAKIEJ ULICY znajduje się KONKRETNY INSTYTUT uczelni, w którym wykłada profesor Andrzej Maj. Nie interesuje nas adres rektoratu ani ogólna siedziba uczelni – tylko ta jednostka (instytut).

    KONTEXT  
    Poniżej masz pełne transkrypcje nagrań z przesłuchań świadków. Zeznania mogą sobie przeczyć lub uzupełniać; jedno z nagrań (Rafał) jest chaotyczne, więc zwróć uwagę na możliwość błędnych wskazówek. Przeanalizuj wszystkie fragmenty, ale wnioski opieraj wyłącznie na tych informacjach i swojej wiedzy o strukturze polskich uczelni.

    <<<TRANSKRYPCJE_START
    {combined_text}
    <<<TRANSKRYPCJE_STOP

    INSTRUKCJA ROZUMOWANIA  
    1. Myśl na głos: zapisuj kolejno obserwacje z transkrypcji, wskazując, które fragmenty sugerują możliwy adres.  
    2. Uporządkuj sprzeczne dane; wyjaśnij, które uznajesz za wiarygodne i dlaczego.  
    3. Zderz te obserwacje ze swoją wiedzą o uczelniach w Polsce, aby zidentyfikować nazwę instytutu i przypisaną mu ulicę.  
    4. Na końcu podaj wyłącznie końcową odpowiedź w formacie (czysty string):  
    <nazwa ulicy, numer jeśli występuje>  
    Nie wypisuj pełnych transkrypcji w odpowiedzi.
    """
    
    print("🤖 [*] Asking LLM to analyze the transcriptions...")
    response = ask_llm(
        question="Analizuj transkrypcje i znajdź ulicę, gdzie znajduje się instytut profesora Maja.",
        api_key=OPENAI_API_KEY,
        model="gpt-4o",
        context=system_prompt
    )
    
    print("🔎 [*] LLM response:")
    print(response)
    return response
    
    # Find street name in the response
    # street_name = extract_street_name(response)
    # if street_name:
    #     print(f"🏙️ [+] Found street name: {street_name}")
    #     return street_name
    # else:
    #     print("❌ [-] Could not clearly identify the street name from the analysis")
    #     return None


def extract_street_name(text):
    """Extract the street name from the LLM's response."""
    # Look for direct mentions of the street
    direct_pattern = r"(?i)ULICA:\s+([A-ZĘÓĄŚŁŻŹĆŃa-zęóąśłżźćń]+(?:\s+[A-ZĘÓĄŚŁŻŹĆŃa-zęóąśłżźćń]+)*)"
    direct_match = re.search(direct_pattern, text)
    
    if direct_match:
        return direct_match.group(1).strip()
    
    # Look for 'ul.' pattern
    ul_pattern = r"(?i)ul\.\s+([A-ZĘÓĄŚŁŻŹĆŃa-zęóąśłżźćń]+(?:\s+[A-ZĘÓĄŚŁŻŹĆŃa-zęóąśłżźćń]+)*)"
    ul_match = re.search(ul_pattern, text)
    
    if ul_match:
        return ul_match.group(1).strip()
    
    # Look for a clear answer format
    answer_pattern = r"(?i)Answer:[\s\n]*([A-ZĘÓĄŚŁŻŹĆŃa-zęóąśłżźćń]+(?:\s+[A-ZĘÓĄŚŁŻŹĆŃa-zęóąśłżźćń]+)*)"
    answer_match = re.search(answer_pattern, text)
    
    if answer_match:
        return answer_match.group(1).strip()
    
    # Fallback: Try to find the most confidently stated street name
    confident_pattern = r"(?i)instytut\s+znajduje\s+się\s+na\s+ulicy\s+([A-ZĘÓĄŚŁŻŹĆŃa-zęóąśłżźćń]+(?:\s+[A-ZĘÓĄŚŁŻŹĆŃa-zęóąśłżźćń]+)*)"
    confident_match = re.search(confident_pattern, text)
    
    if confident_match:
        return confident_match.group(1).strip()
    
    return None


def submit_answer(street_name):
    """Submit the street name to the central server."""
    print("📤 [*] Submitting answer to the central server...")
    
    payload = {
        "task": "mp3",
        "apikey": API_KEY,
        "answer": street_name
    }
    
    try:
        response = make_request(
            CENTRALA_REPORT_URL,
            method="post",
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"}
        )
        
        print(f"✅ [+] Submission response: {response.text}")
        return response.json()
    except Exception as e:
        print(f"❌ [-] Error submitting answer: {str(e)}")
        sys.exit(1)


def cache_transcriptions(audio_files, cache_dir="transcription_cache"):
    """Cache transcriptions to avoid re-transcribing audio files."""
    # Create cache directory if it doesn't exist
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
    
    transcriptions = {}
    
    for audio_file in audio_files:
        file_name = os.path.basename(audio_file)
        cache_file = os.path.join(cache_dir, f"{file_name}.txt")
        
        # Check if transcription is already cached
        if os.path.exists(cache_file):
            print(f"📂 [*] Loading cached transcription for {file_name}...")
            with open(cache_file, 'r', encoding='utf-8') as f:
                transcriptions[file_name] = f.read()
        else:
            # Transcribe and cache
            transcription = transcribe_audio(audio_file)
            transcriptions[file_name] = transcription
            
            # Save to cache
            with open(cache_file, 'w', encoding='utf-8') as f:
                f.write(transcription)
    
    return transcriptions


def main():
    """Main execution function."""
    print("🚀 [*] Starting Audio Testimonies Analysis...")
    
    # Step 1: Get audio files from the przesluchania directory
    audio_files = get_audio_files()
    print(audio_files)
    
    # Step 2: Transcribe audio files (with caching)
    transcriptions = cache_transcriptions(audio_files)
    print(transcriptions)
    
    # Step 3: Analyze transcriptions to find the street name
    street_name = analyze_transcriptions(transcriptions)
    print(street_name)
    
    if not street_name:
        print("❌ [-] Could not determine the street name")
        sys.exit(1)
    
    # Step 4: Submit the answer
    result = submit_answer(street_name)
    
    # Step 5: Check for flag
    try:
        flag = find_flag_in_text(result.get("message", ""))
        print(f"🚩 [+] Flag found: {flag}")
    except Exception as e:
        print(f"⚠️ [!] No flag found in response: {str(e)}")
    
    print("✅ [+] Task completed successfully!")


if __name__ == "__main__":
    main()