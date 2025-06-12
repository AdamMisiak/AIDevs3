import os
import sys
import json
import re
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import ask_llm, make_request

load_dotenv()
# --- KONFIGURACJA ---
API_KEY = os.environ["API_KEY"]
OPENAI_KEY = os.environ["OPENAI_API_KEY"]
BARBARA_NOTE_URL = os.environ["BARBARA_NOTE_URL"]
PEOPLE_API = os.environ["PEOPLE_API"]
PLACES_API = os.environ["PLACES_API"]
REPORT_API = os.environ["REPORT_API"]

# --- Pomocnicza funkcja do czyszczenia odpowiedzi LLM ---
def extract_json_from_llm_response(llm_response):
    llm_response = llm_response.strip()
    llm_response = re.sub(r"^```json", "", llm_response, flags=re.IGNORECASE).strip()
    llm_response = re.sub(r"^```", "", llm_response).strip()
    llm_response = re.sub(r"```$", "", llm_response).strip()
    return llm_response

def normalize(s):
    import unicodedata
    s = s.upper()
    s = ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c))
    return s

def is_valid_name(s):
    # Akceptuj tylko napisy złożone z wielkich liter A-Z (po normalizacji)
    return s.isalpha() and s.isupper() and all('A' <= c <= 'Z' for c in s)

# --- 1. Pobierz notatkę ---
print("[INFO] Pobieram notatkę o Barbarze...")
resp = make_request(BARBARA_NOTE_URL)
notatka = resp.text
print("[NOTATKA]", notatka)

# --- 2. Wyciągnij imiona i miasta przez LLM ---
prompt = (
    "Wypisz wszystkie imiona osób i nazwy miast, które pojawiają się w tym tekście, "
    "w formie dwóch oddzielnych list: najpierw imiona, potem miasta. "
    "Każde imię i miasto podaj w mianowniku, bez polskich znaków, wielkimi literami. "
    "Odpowiedz tylko listami w formacie JSON: {\"imiona\": [...], \"miasta\": [...]}\n\n" + notatka
)
llm_response = ask_llm(prompt, OPENAI_KEY)
print("[LLM RESPONSE]", llm_response)
try:
    llm_response_clean = extract_json_from_llm_response(llm_response)
    data = json.loads(llm_response_clean)
    imiona = set(data.get("imiona", []))
    miasta = set(data.get("miasta", []))
except Exception as e:
    print("[ERROR] Nie udało się sparsować odpowiedzi LLM:", e)
    exit(1)

# --- 3. Normalizacja ---
kolejka_osob = set(normalize(i) for i in imiona)
kolejka_miast = set(normalize(m) for m in miasta)
sprawdzone_osoby = set()
sprawdzone_miasta = set()
miasta_z_notatki = set(kolejka_miast)

print(f"[INFO] Startowe imiona: {kolejka_osob}")
print(f"[INFO] Startowe miasta: {kolejka_miast}")

# --- 4. Pętla BFS ---
found = None
while kolejka_osob or kolejka_miast:
    # Osoby
    if kolejka_osob:
        osoba = kolejka_osob.pop()
        if osoba in sprawdzone_osoby:
            continue
        sprawdzone_osoby.add(osoba)
        print(f"[API/people] Sprawdzam osobę: {osoba}")
        payload = {"apikey": API_KEY, "query": osoba}
        resp = make_request(PEOPLE_API, method="post", json=payload)
        try:
            data = resp.json()
            if isinstance(data, dict) and "message" in data:
                miejsca = data["message"].split()
            else:
                miejsca = data
        except Exception as e:
            print("[ERROR] Nie udało się sparsować odpowiedzi people:", e)
            continue
        print(f"[API/people] {osoba} widziano w: {miejsca}")
        for m in miejsca:
            m_norm = normalize(m)
            if is_valid_name(m_norm):
                if m_norm not in sprawdzone_miasta:
                    kolejka_miast.add(m_norm)
            else:
                print(f"[WARN] Pomijam nietypową nazwę miasta: {m_norm}")
    # Miasta
    if kolejka_miast:
        miasto = kolejka_miast.pop()
        if miasto in sprawdzone_miasta:
            continue
        sprawdzone_miasta.add(miasto)
        print(f"[API/places] Sprawdzam miasto: {miasto}")
        payload = {"apikey": API_KEY, "query": miasto}
        resp = make_request(PLACES_API, method="post", json=payload)
        try:
            data = resp.json()
            if isinstance(data, dict) and "message" in data:
                osoby = data["message"].split()
            else:
                osoby = data
        except Exception as e:
            print("[ERROR] Nie udało się sparsować odpowiedzi places:", e)
            continue
        print(f"[API/places] W {miasto} widziano: {osoby}")
        for o in osoby:
            o_norm = normalize(o)
            if is_valid_name(o_norm):
                if o_norm not in sprawdzone_osoby:
                    kolejka_osob.add(o_norm)
            else:
                print(f"[WARN] Pomijam nietypowe imię: {o_norm}")
        # Szukamy Barbary
        # if "BARBARA" in [normalize(x) for x in osoby]:
        #     if miasto not in miasta_z_notatki:
        #         print(f"[ODPOWIEDŹ] Barbara może być w: {miasto}")
        #         found = miasto
        #         break

# --- 5. Raportowanie ---
if found:
    print(f"[REPORT] Zgłaszam miasto: {found}")
    payload = {"task": "loop", "apikey": API_KEY, "answer": found}
    resp = make_request(REPORT_API, method="post", json=payload)
    print("[REPORT RESPONSE]", resp.text)
else:
    print("[INFO] Nie znaleziono nowego miasta Barbary.")
