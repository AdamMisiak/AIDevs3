"""
Task S02E04: Factory Files Categorization

This script:
1. Processes factory data files from the 'files' directory
2. Processes files of different formats (TXT, PNG, MP3)
3. Categorizes files based on their content (people-related or hardware-related)
4. Submits the categorized file lists to the central server
"""
import os
import sys
import json
import re
import base64
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to Python path to allow imports from shared utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import make_request, find_flag_in_text
from openai import OpenAI

# Load environment variables
load_dotenv()

# Configuration
API_KEY = os.getenv("API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CENTRALA_REPORT_URL = os.getenv("CENTRALA_REPORT_URL")
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")


def get_files_from_directory():
    """Get files from the local 'files' directory."""
    print("🔍 [*] Looking for files in the 'files' directory...")
    
    # Use absolute path based on script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    files_dir = os.path.join(script_dir, "files")
    
    print(f"📂 [*] Looking in directory: {files_dir}")
    
    # Check if directory exists
    if not os.path.exists(files_dir):
        print(f"❌ [-] Directory '{files_dir}' not found. Please make sure it exists.")
        sys.exit(1)
    
    # Get all files recursively
    all_files = []
    for root, _, files in os.walk(files_dir):
        # Skip the "facts" directory
        if "facts" in root.lower():
            print(f"⏭️ [*] Skipping directory: {root}")
            continue
        
        # Skip weapons_tests.zip and other non-relevant files
        for f in files:
            if f.endswith(('.txt', '.png', '.mp3')) and not f.startswith('.'):
                all_files.append(os.path.join(root, f))
    
    print(f"📊 [*] Found {len(all_files)} files to process")
    
    return all_files


def get_file_content(file_path):
    """Get the content of a file based on its extension."""
    filename = os.path.basename(file_path)
    print(f"📄 [*] Processing file: {filename}")
    
    # Create cache directory if it doesn't exist
    os.makedirs(CACHE_DIR, exist_ok=True)
    
    # Generate cache filename from the original filename
    cache_file = os.path.join(CACHE_DIR, f"{filename}.txt")
    
    # Check if file is already cached
    if os.path.exists(cache_file):
        print(f"🔄 [*] Using cached content for {filename}")
        with open(cache_file, 'r', encoding='utf-8') as f:
            return f.read()
    
    # Process based on file extension
    ext = os.path.splitext(file_path)[1].lower()
    content = ""
    
    try:
        if ext == '.txt':
            # Read text file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            print(f"📝 [*] Read text file: {filename}")
                
        elif ext == '.png':
            # Use OpenAI to extract text from image
            client = OpenAI(api_key=OPENAI_API_KEY)
            with open(file_path, "rb") as image_file:
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "system", 
                            "content": "You are an image text extraction assistant. Extract ALL text from the image, preserving the exact formatting."
                        },
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "Extract all text from this image:"},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/png;base64,{base64.b64encode(image_file.read()).decode('utf-8')}"
                                    }
                                }
                            ]
                        }
                    ]
                )
                content = response.choices[0].message.content
                print(f"🖼️ [*] Extracted text from image: {filename}")
                print(f"Extracted content: {content[:100]}...")
                
        elif ext == '.mp3':
            # Use Whisper to transcribe audio
            client = OpenAI(api_key=OPENAI_API_KEY)
            with open(file_path, "rb") as audio_file:
                transcription = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file
                )
                content = transcription.text
                print(f"🎵 [*] Transcribed audio: {filename}")
                print(f"Transcription: {content[:100]}...")
        else:
            print(f"⚠️ [!] Unsupported file format: {ext}")
            return None
        
        # Cache the content
        with open(cache_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return content
        
    except Exception as e:
        print(f"❌ [-] Error processing file {filename}: {str(e)}")
        return None


def categorize_file(file_path, content):
    """Categorize a file based on its content."""
    # Skip if content is None
    if content is None:
        return None
    
    filename = os.path.basename(file_path)
    
    # Skip files in the "facts" directory
    if "facts" in file_path.lower():
        print(f"⏭️ [*] Skipping file in facts directory: {filename}")
        return None
    
    # Placeholder for the prompt, you can replace with your own
    system_prompt = """
[Classify Extracted Text from Archive Files]

You are an intelligence filter classifying raw extracted text into one of two categories: people-related evidence or hardware-related malfunctions.

<prompt_objective>
Label each piece of text as either `people` or `hardware` if it contains relevant information. If it does not match either category, do NOT return anything.
</prompt_objective>

<prompt_rules>
- Return ONLY one of the following labels: `people` or `hardware`.
- DO NOT return `no data`, `unknown`, or any other label.
- DO NOT explain or summarize.
- DO NOT fabricate labels for irrelevant or ambiguous input – return nothing at all in such cases.

Classification criteria:

**Label as `people` if the text mentions:**
- Captured individuals, hostages, prisoners, detainees.
- Traces of human presence such as:
  - footprints, fingerprints, blood stains, hair, voice, handwritten notes, body temperature traces, surveillance imagery.
- Direct or indirect indicators like: “two sets of boots”, “human heat signature”, “unidentified subject spotted”.

**Label as `hardware` if the text mentions:**
- Physical equipment malfunctions (excluding software issues).
- Faulty machinery, broken components, overheating, short-circuits, loss of structural integrity, sensor failure.
- Phrases like: “broken gear”, “cooling system failure”, “detected voltage spike”, “damaged rotor”, “battery leakage”, “faulty connection”.

<prompt_examples>
USER: "W miejscu zdarzenia odnaleziono dwa odciski butów oraz ręcznie zapisane notatki."
AI: people

USER: "Moduł sensoryczny przestał reagować po wykryciu anomalii w zasilaniu."
AI: hardware

USER: "Odczyt wskazuje na obecność istoty biologicznej w strefie 3."
AI: people

USER: "Kamera termowizyjna zarejestrowała ślad cieplny o ludzkim kształcie."
AI: people

USER: "Wadliwy przekaźnik spowodował spięcie i zatrzymanie całego układu."
AI: hardware

USER: "Sygnał GPS został utracony na 3 godziny."
AI:

USER: "W kanałach wentylacyjnych wykryto ślady włókien organicznych i ludzkiego naskórka."
AI: people

USER: "Drgania osi obrotu przekroczyły dopuszczalną normę, sugerując uszkodzenie łożyska."
AI: hardware

USER: "Notatki znalezione przy porzuconym obozowisku sugerują, że przebywały tam przynajmniej dwie osoby."
AI: people
</prompt_examples>

Return only: `people` or `hardware`. If nothing fits, return nothing.

    """
    
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o",  # Using a smaller, faster model for cost efficiency
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Categorize this factory report:\n\n{content}"}
            ],
            temperature=0 # Low temperature for more consistent results
        )
        
        result = response.choices[0].message.content.strip()
        print(f"🏷️ [*] Categorization result for {filename}:")
        print(result)
        
        # Parse categories from response
        categories = []
        if "people" in result.lower():
            categories.append("people")
        if "hardware" in result.lower():
            categories.append("hardware")
        
        return categories
        
    except Exception as e:
        print(f"❌ [-] Error categorizing file {filename}: {str(e)}")
        return None


def process_files(files):
    """Process all files and categorize them."""
    print("🔍 [*] Processing files...")
    
    # Initialize categories
    categories = {
        "people": [],
        "hardware": []
    }
    
    # Process each file
    for file_path in files:
        content = get_file_content(file_path)
        file_categories = categorize_file(file_path, content)
        
        if file_categories:
            filename = os.path.basename(file_path)
            for category in file_categories:
                if category in categories and filename not in categories[category]:
                    categories[category].append(filename)
    
    # Sort filenames alphabetically in each category
    for category in categories:
        categories[category].sort()
    
    print("✅ [+] File processing and categorization completed")
    return categories


def submit_categories(categories):
    """Submit categorized file lists to the central server."""
    print("📤 [*] Submitting categorized file lists...")
    
    # Prepare payload
    payload = {
        "task": "kategorie",
        "apikey": API_KEY,
        "answer": categories
    }
    
    print(f"📦 [*] Payload: {json.dumps(payload, indent=2)}")
    
    response = make_request(
        CENTRALA_REPORT_URL,
        method="post",
        data=json.dumps(payload),
        headers={"Content-Type": "application/json"}
    )
    
    print(f"✅ [+] Submission response: {response.text}")
    print(response)
    
    # Check for flag in response
    try:
        flag = find_flag_in_text(response.text)
        print(f"🚩 [+] Flag found: {flag}")
    except Exception as e:
        print(f"⚠️ [!] No flag found in response")
    
    return response.json()


def main():
    """Main execution function."""
    print("🚀 [*] Starting Factory Files Categorization task...")
    
    # Get files from directory
    files = get_files_from_directory()
    print(files)
    
    # Process and categorize files
    categories = process_files(files)
    print(files)
    
    # Print categorized files
    print("📋 [*] Categorized files:")
    for category, files in categories.items():
        print(f"  {category}: {len(files)} files")
        for file in files:
            print(f"    - {file}")
    
    # Submit categories
    result = submit_categories(categories)
    
    print("✅ [+] Task completed successfully!")


if __name__ == "__main__":
    main()