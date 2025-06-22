"""
Task S04E04: Webhook - Drone Navigation API

This script:
1. Creates a FastAPI webhook server to handle drone navigation instructions
2. Uses LLM to parse natural language movement instructions
3. Tracks drone position on a 4x4 map starting from top-left corner
4. Returns location descriptions in Polish (max 2 words)
5. Provides endpoint to register webhook URL with centrala
"""
import os
import sys
import json
from typing import Dict, Tuple, Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn
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
WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", "8000"))
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "0.0.0.0")

# Map representation (4x4 grid, coordinates as (row, col) starting from 0)
MAP_GRID = {
    (0, 0): "start",      # a1 - punkt startowy
    (0, 1): "trawa",      # b1
    (0, 2): "drzewo",     # c1
    (0, 3): "dom",        # d1
    (1, 0): "trawa",      # a2
    (1, 1): "wiatrak",    # b2
    (1, 2): "trawa",      # c2
    (1, 3): "trawa",      # d2
    (2, 0): "trawa",      # a3
    (2, 1): "trawa",      # b3
    (2, 2): "skaly",      # c3
    (2, 3): "drzewo",     # d3
    (3, 0): "skaly",      # a4
    (3, 1): "skaly",      # b4
    (3, 2): "auto",       # c4
    (3, 3): "jaskinia"    # d4
}

# Starting position (top-left corner)
START_POSITION = (0, 0)

# FastAPI app
app = FastAPI(title="Drone Navigation API", version="1.0.0")

class DroneInstruction(BaseModel):
    instruction: str

class DroneResponse(BaseModel):
    description: str

class WebhookRegistration(BaseModel):
    webhook_url: str


def get_map_description() -> str:
    """Generate a textual description of the map for the LLM."""
    return """Mapa terenu 4x4:
Współrzędne (wiersz, kolumna) liczone od 0:

Wiersz 0: (0,0)=start, (0,1)=trawa, (0,2)=drzewo, (0,3)=dom
Wiersz 1: (1,0)=trawa, (1,1)=wiatrak, (1,2)=trawa, (1,3)=trawa  
Wiersz 2: (2,0)=trawa, (2,1)=trawa, (2,2)=skaly, (2,3)=drzewo
Wiersz 3: (3,0)=skaly, (3,1)=skaly, (3,2)=auto, (3,3)=jaskinia

Punkt startowy: (0,0) - lewy górny róg
Ruch w prawo: kolumna +1
Ruch w lewo: kolumna -1  
Ruch w dół: wiersz +1
Ruch w górę: wiersz -1

Granice mapy: wiersze 0-3, kolumny 0-3"""


def parse_movement_instruction(instruction: str) -> Tuple[int, int]:
    """Use LLM to parse natural language movement instruction and return final position."""
    print(f"🧭 [*] Parsing instruction: {instruction}")
    
    map_desc = get_map_description()
    
    system_prompt = f"""Jesteś ekspertem w nawigacji dronów. Twoim zadaniem jest interpretacja instrukcji ruchu i obliczenie końcowej pozycji drona na mapie 4x4.

{map_desc}

INSTRUKCJE:
1. Dron ZAWSZE zaczyna z pozycji (0,0) - lewy górny róg
2. Przeanalizuj instrukcję ruchu krok po kroku
3. Oblicz końcową pozycję (wiersz, kolumna)
4. Upewnij się, że pozycja mieści się w granicach mapy (0-3, 0-3)
5. Odpowiedz TYLKO w formacie: "wiersz,kolumna" (np. "2,1")

Przykłady:
- "jedno pole w prawo" → z (0,0) do (0,1) → odpowiedź: "0,1"
- "dwa pola w dół" → z (0,0) do (2,0) → odpowiedź: "2,0"  
- "jedno w prawo, potem jedno w dół" → z (0,0) do (0,1) do (1,1) → odpowiedź: "1,1"
- "na sam dół" → z (0,0) do (3,0) → odpowiedź: "3,0"
- "w prawo do końca" → z (0,0) do (0,3) → odpowiedź: "0,3"

Jeśli instrukcja wyprowadziłaby drona poza mapę, zatrzymaj go na granicy."""
    
    user_prompt = f"""Instrukcja ruchu drona: "{instruction}"

Dron startuje z pozycji (0,0). Gdzie się znajdzie po wykonaniu tej instrukcji?
Odpowiedz tylko współrzędnymi w formacie "wiersz,kolumna"."""
    
    try:
        response = ask_llm(
            question=user_prompt,
            api_key=OPENAI_API_KEY,
            model="gpt-4o-mini",
            context=system_prompt
        )
        
        # Parse response to extract coordinates
        response = response.strip().replace(" ", "")
        if "," in response:
            parts = response.split(",")
            if len(parts) == 2:
                try:
                    row = int(parts[0])
                    col = int(parts[1])
                    
                    # Validate coordinates are within map bounds
                    if 0 <= row <= 3 and 0 <= col <= 3:
                        print(f"✅ [+] Parsed position: ({row}, {col})")
                        return (row, col)
                except ValueError:
                    pass
        
        print(f"⚠️ [!] Invalid LLM response: '{response}', using start position")
        return START_POSITION
        
    except Exception as e:
        print(f"❌ [-] Error parsing instruction: {str(e)}")
        return START_POSITION


def get_location_description(position: Tuple[int, int]) -> str:
    """Get description of what's at the given position."""
    description = MAP_GRID.get(position, "nieznane")
    print(f"📍 [*] Position {position}: {description}")
    return description


@app.post("/drone", response_model=DroneResponse)
async def handle_drone_instruction(instruction: DroneInstruction):
    """Handle drone navigation instruction and return location description."""
    print(f"\n🚁 [*] Received drone instruction: {instruction.instruction}")
    
    try:
        # Parse instruction to get final position
        final_position = parse_movement_instruction(instruction.instruction)
        
        # Get description of what's at that position
        description = get_location_description(final_position)
        
        response = DroneResponse(description=description)
        print(f"📤 [*] Sending response: {response.description}")
        
        return response
    
    except Exception as e:
        print(f"❌ [-] Error handling drone instruction: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/register-webhook")
async def register_webhook(registration: WebhookRegistration):
    """Register webhook URL with centrala and wait for the response."""
    print(f"📝 [*] Registering webhook URL: {registration.webhook_url}")
    
    payload = {
        "task": "webhook",
        "apikey": API_KEY,
        "answer": registration.webhook_url
    }
    
    try:
        print(f"📤 [*] Sending registration to centrala...")
        response = make_request(
            CENTRALA_REPORT_URL,
            method="post",
            json=payload,
            headers={"Content-Type": "application/json; charset=utf-8"}
        )
        
        print(f"✅ [+] Registration successful!")
        print(f"📋 [*] Response: {response.text}")
        
        # Check for flag in response
        try:
            flag = find_flag_in_text(response.text)
            print(f"🚩 [+] Flag found: {flag}")
            return {"status": "success", "flag": flag, "response": response.text}
        except Exception:
            print(f"⚠️ [!] No flag found in response")
            return {"status": "success", "response": response.text}
    
    except Exception as e:
        print(f"❌ [-] Error registering webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"message": "Drone Navigation API is running", "status": "ok"}


@app.get("/map")
async def get_map():
    """Return map information for debugging."""
    return {
        "map": MAP_GRID,
        "start_position": START_POSITION,
        "map_size": "4x4",
        "coordinates": "row,col (0-based)"
    }


def main():
    """Main function to start the FastAPI server."""
    print("🚀 [*] Starting Drone Navigation API server...")
    print(f"📍 [*] Server will run on {WEBHOOK_HOST}:{WEBHOOK_PORT}")
    print(f"🔗 [*] Drone endpoint: http://{WEBHOOK_HOST}:{WEBHOOK_PORT}/drone")
    print(f"📝 [*] Registration endpoint: http://{WEBHOOK_HOST}:{WEBHOOK_PORT}/register-webhook")
    print(f"🗺️  [*] Map endpoint: http://{WEBHOOK_HOST}:{WEBHOOK_PORT}/map")
    
    # Display map for reference
    print(f"\n🗺️ [*] Map layout:")
    print(f"     a(0)    b(1)     c(2)      d(3)")
    for row in range(4):
        row_desc = f"{row+1}({row}) |"
        for col in range(4):
            location = MAP_GRID.get((row, col), "?")
            row_desc += f" {location:8} |"
        print(row_desc)
    
    print(f"\n⚠️ [*] Remember to:")
    print(f"    1. Expose this server via ngrok or Azyl")
    print(f"    2. Use the /register-webhook endpoint to register your public URL")
    print(f"    3. The public URL should point to /drone endpoint")
    
    uvicorn.run(app, host=WEBHOOK_HOST, port=WEBHOOK_PORT)


if __name__ == "__main__":
    main()
