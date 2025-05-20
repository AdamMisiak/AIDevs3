"""
Task S02E02: Map Analysis

This script:
1. Processes map fragments from the 'map' directory
2. Uses OpenAI's vision model to analyze the map fragments
3. Determines which city the map fragments belong to
4. Submits the answer to the central server
"""
import os
import sys
import base64
from dotenv import load_dotenv
from openai import OpenAI

# Add parent directory to Python path to allow imports from shared utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

# Configuration
API_KEY = os.getenv("API_KEY")
CENTRALA_REPORT_URL = os.getenv("CENTRALA_REPORT_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


def get_map_fragments():
    """Get map fragments from the map directory."""
    print("🔍 [*] Looking for map fragments in the map directory...")
    
    # Use absolute path based on script location
    map_dir = os.path.dirname(os.path.abspath(__file__))
    
    print(f"📂 [*] Looking in directory: {map_dir}")
    
    # Check if directory exists
    if not os.path.exists(map_dir):
        print(f"❌ [-] Directory '{map_dir}' not found. Please make sure it exists.")
        sys.exit(1)
    
    try:
        # Get list of image files
        image_files = [os.path.join(map_dir, file) for file in os.listdir(map_dir) 
                       if file.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))]
        
        if not image_files:
            print(f"❌ [-] No image files found in '{map_dir}' directory.")
            sys.exit(1)
            
        print(f"✅ [+] Found {len(image_files)} map fragments")
        return image_files
    
    except Exception as e:
        print(f"❌ [-] Error getting map fragments: {str(e)}")
        sys.exit(1)


def encode_image(image_path):
    """Encode image file to base64."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def analyze_map_fragments(image_files):
    """
    Analyze map fragments using OpenAI's vision model to determine the city.
    """
    print("🔍 [*] Analyzing map fragments...")
    
    # Prepare encoded images
    encoded_images = []
    for image_path in image_files:
        print(f"📊 [*] Encoding image: {os.path.basename(image_path)}...")
        encoded_images.append(encode_image(image_path))
    
    # Create prompt with detailed instructions
    system_prompt = """
    [Map Fragment Analysis – Identify the City v2]

    You will receive **exactly four map images** (map-1 … map-4).  
    Your task is to identify the **single Polish city** that **at least three** of these fragments belong to.

    <prompt_objective>
    Determine the Polish city shared by ≥ 3 fragments with high confidence, after verifying that every cited street or landmark truly exists in that city.
    </prompt_objective>

    <prompt_rules>
    STEP 1 – EXTRACT  
    • For each fragment, list **all legible street names** and **all visible landmarks** (churches, cemeteries, stations, parks, rivers, etc.).  
    • Note compass hints (river bend, coastline, grid vs. radial plan).

    STEP 2 – CANDIDATE MATCHING  
    • Generate a **candidate city list** where ≥ 2 items (street or landmark) from a fragment co-exist.  
    • Cross-check every fragment against each candidate.

    STEP 3 – CONSISTENCY CHECK  
    • A city is valid iff **≥ 3 fragments** can be mapped there **and** each of those fragments has ≥ 2 verified items present in that city.  
    • Mark any fragment that fails this test as **decoy**.

    STEP 4 – CERTAINTY THRESHOLD  
    • If no city meets the criteria above with **≥ 80 % confidence**, output **`unknown`** (lowercase, no quotes).  
    • Otherwise proceed.

    STEP 5 – SELF-REVISION  
    • Silently review your reasoning: *“Do all verified streets/landmarks truly exist in the chosen city? Could another city fit better?”*  
    • If a contradiction appears, return to STEP 2.

    OUTPUT FORMAT (STRICT)  
    • Return the city name in lowercase without diacritics (e.g. `krakow`) and whole reasoning behind the final answer.  

    EXPLICITLY FORBIDDEN  
    • Guessing without verification.  
    • Including any explanation, confidence score, or scratch notes in the final answer.  
    • Outputting more than one token except the city or `unknown`.
    </prompt_rules>

    <prompt_examples>
    USER (images) → AI: wroclaw
    USER (3×Lublin, 1×Łódź) → AI: lublin
    USER (no city passes threshold) → AI: unknown
    </prompt_examples>

    """
    
    # Prepare messages for the API call
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": [
            {"type": "text", "text": "Przeanalizuj te cztery fragmenty mapy i określ, z jakiego miasta one pochodzą. Uwaga: jeden z fragmentów może pochodzić z innego miasta (jest błędny). Zwróć nazwę miasta, z którego pochodzą pozostałe fragmenty."},
        ]}
    ]
    
    # Add images to the user message
    for i, encoded_image in enumerate(encoded_images):
        messages[1]["content"].append(
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{encoded_image}"
                }
            }
        )
    
    print("🤖 [*] Asking vision model to analyze the map fragments...")
    
    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
    )
    
    print("🔎 [*] Vision model response:")
    print(response.choices[0].message.content)
    
    return response.choices[0].message.content



def main():
    """Main execution function."""
    print("🚀 [*] Starting Map Fragment Analysis...")
    
    # Step 1: Get map fragments from the map directory
    image_files = get_map_fragments()
    print(image_files)
    
    # Step 2: Analyze map fragments using vision model
    analysis_response = analyze_map_fragments(image_files)
    print(analysis_response)
    
    print("✅ [+] Task completed successfully!")


if __name__ == "__main__":
    main()