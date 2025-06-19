"""
Task S04E02: Research - Lab Data Validation

This script:
1. Loads lab data files (correct.txt, incorrect.txt, verify.txt)
2. Uses a fine-tuned OpenAI model to validate data from verify.txt
3. Identifies valid records based on the trained model's predictions
4. Submits only the IDs of valid records to the central server
"""
import os
import sys
import json
from dotenv import load_dotenv
from openai import OpenAI

# Add parent directory to Python path to allow imports from shared utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import (
    make_request,
    find_flag_in_text
)

# Load environment variables
load_dotenv()

# Configuration
API_KEY = os.getenv("API_KEY")
CENTRALA_REPORT_URL = os.getenv("CENTRALA_REPORT_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
FINE_TUNED_MODEL = os.getenv("FINE_TUNED_MODEL")  # e.g., "ft:gpt-4o-mini-2024-07-18:organization:suffix:id"


def load_data_files():
    """Load the lab data files from the data directory."""
    print("📂 [*] Loading lab data files...")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, "data")
    
    files = {}
    file_names = ["correct.txt", "incorrect.txt", "verify.txt"]
    
    for file_name in file_names:
        file_path = os.path.join(data_dir, file_name)
        
        if not os.path.exists(file_path):
            print(f"❌ [-] File not found: {file_path}")
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f.readlines() if line.strip()]
            
            files[file_name.replace('.txt', '')] = lines
            print(f"✅ [+] Loaded {file_name}: {len(lines)} records")
        
        except Exception as e:
            print(f"❌ [-] Error reading {file_name}: {str(e)}")
            return None
    
    return files


def extract_record_id(line):
    """Extract the two-digit ID from the beginning of a line."""
    parts = line.split(',')
    if parts and len(parts[0]) >= 2:
        return parts[0][:2]
    return None


def validate_with_fine_tuned_model(data_line):
    """Validate a single data line using the fine-tuned model."""
    print(f"🔍 [*] Validating record: {extract_record_id(data_line)}")
    
    client = OpenAI(api_key=OPENAI_API_KEY)
    
    try:
        response = client.chat.completions.create(
            model=FINE_TUNED_MODEL,
            messages=[
                {"role": "system", "content": "validate data"},
                {"role": "user", "content": data_line}
            ],
            max_tokens=10,
            temperature=0
        )
        
        result = response.choices[0].message.content.strip()
        print(f"✅ [+] Model response: '{result}'")
        
        # Check if the result indicates valid data (1, true, valid, etc.)
        is_valid = result.lower() in ['1', 'true', 'valid', 'correct']
        return is_valid
    
    except Exception as e:
        print(f"❌ [-] Error validating with model: {str(e)}")
        return False


def verify_all_records(verify_data):
    """Verify all records in the verify.txt data using the fine-tuned model."""
    print(f"\n🧪 [*] Verifying {len(verify_data)} records...")
    
    valid_ids = []
    invalid_ids = []
    
    for i, line in enumerate(verify_data, 1):
        record_id = extract_record_id(line)
        if not record_id:
            print(f"⚠️ [!] Could not extract ID from line {i}: {line[:50]}...")
            continue
        
        print(f"\n📊 [*] Processing {i}/{len(verify_data)} - ID: {record_id}")
        
        is_valid = validate_with_fine_tuned_model(line)
        
        if is_valid:
            valid_ids.append(record_id)
            print(f"✅ [+] Record {record_id}: VALID")
        else:
            invalid_ids.append(record_id)
            print(f"❌ [-] Record {record_id}: INVALID")
    
    print(f"\n📈 [*] Verification summary:")
    print(f"    Valid records: {len(valid_ids)}")
    print(f"    Invalid records: {len(invalid_ids)}")
    print(f"    Valid IDs: {valid_ids}")
    
    return valid_ids


def submit_results(valid_ids):
    """Submit the valid record IDs to the central server."""
    print("📤 [*] Submitting validation results...")
    
    payload = {
        "task": "research",
        "apikey": API_KEY,
        "answer": valid_ids
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
        
        print(f"✅ [+] Results submitted successfully")
        print(f"📋 [*] Response: {response.text}")
        
        # Check for flag in response
        try:
            flag = find_flag_in_text(response.text)
            print(f"🚩 [+] Flag found: {flag}")
        except Exception:
            print(f"⚠️ [!] No flag found in response")
        
        return response.json()
    
    except Exception as e:
        print(f"❌ [-] Error submitting results: {str(e)}")
        return None


def analyze_training_data(data_files):
    """Analyze the training data to understand the format (optional)."""
    print("\n📊 [*] Analyzing training data format...")
    
    correct_data = data_files.get('correct', [])
    incorrect_data = data_files.get('incorrect', [])
    
    print(f"📈 [*] Correct samples: {len(correct_data)}")
    if correct_data:
        print(f"    Example: {correct_data[0][:100]}...")
    
    print(f"📉 [*] Incorrect samples: {len(incorrect_data)}")
    if incorrect_data:
        print(f"    Example: {incorrect_data[0][:100]}...")
    
    # Show some sample record IDs
    correct_ids = [extract_record_id(line) for line in correct_data[:5]]
    incorrect_ids = [extract_record_id(line) for line in incorrect_data[:5]]
    
    print(f"📋 [*] Sample correct IDs: {correct_ids}")
    print(f"📋 [*] Sample incorrect IDs: {incorrect_ids}")


def main():
    """Main execution function."""
    print("🚀 [*] Starting Research task...")
    
    # Check if fine-tuned model is configured
    if not FINE_TUNED_MODEL:
        print("❌ [-] FINE_TUNED_MODEL environment variable not set")
        print("💡 [*] Please set FINE_TUNED_MODEL to your fine-tuned model ID")
        print("💡 [*] Example: ft:gpt-4o-mini-2024-07-18:organization:suffix:id")
        sys.exit(1)
    
    print(f"🤖 [*] Using fine-tuned model: {FINE_TUNED_MODEL}")
    
    # Step 1: Load data files
    data_files = load_data_files()
    if not data_files:
        print("❌ [-] Could not load data files")
        sys.exit(1)
    
    # Step 2: Analyze training data (optional)
    analyze_training_data(data_files)
    
    # Step 3: Verify records using fine-tuned model
    verify_data = data_files.get('verify', [])
    if not verify_data:
        print("❌ [-] No verification data found")
        sys.exit(1)
    
    valid_ids = verify_all_records(verify_data)
    
    if not valid_ids:
        print("❌ [-] No valid records found")
        sys.exit(1)
    
    # Step 4: Submit results
    result = submit_results(valid_ids)
    
    print("✅ [+] Research task completed successfully!")


if __name__ == "__main__":
    main()
