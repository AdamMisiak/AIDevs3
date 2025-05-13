import requests
import sys
from dotenv import load_dotenv
import json # Import json for potentially better inspection/debugging if needed
import os
load_dotenv()

AID3_API_KEY = os.getenv("AID3_API_KEY")
POLIGON_DATA_URL = os.getenv("POLIGON_DATA_URL")
POLIGON_VERIFY_URL = os.getenv("POLIGON_VERIFY_URL")
TASK_NAME = "POLIGON"
REQUEST_TIMEOUT = 15 # seconds for network requests

print(f"Fetching data from: {POLIGON_DATA_URL}")
# Fetch data - simplified error handling (requests might still raise exceptions)
response_data = requests.get(POLIGON_DATA_URL, timeout=REQUEST_TIMEOUT)
response_data.raise_for_status() # Will stop script if status code is 4xx or 5xx
raw_text_data = response_data.text
print(raw_text_data)
print("Data fetched successfully.")

# Process data into a list of non-empty strings (lines)
string_array = [line.strip() for line in raw_text_data.splitlines() if line.strip()]
print(string_array)

# Prepare payload for verification
payload = {
    "task": TASK_NAME,
    "apikey": AID3_API_KEY,
    "answer": string_array
}

print(f"\nSending verification to: {POLIGON_VERIFY_URL}")
# Send for verification - simplified error handling
response_verify = requests.post(POLIGON_VERIFY_URL, json=payload, timeout=REQUEST_TIMEOUT)
response_verify.raise_for_status() # Will stop script if status code is 4xx or 5xx

print("Verification request successful.")
print("-" * 30)
print("Verification Server Response:")
print("-" * 30)
# Try to print JSON response nicely, otherwise print raw text
try:
    print(response_verify.json())
except requests.exceptions.JSONDecodeError:
    print(response_verify.text)

