"""
Task S01E03: JSON file correction

This script:
1. Downloads a JSON calibration file
2. Fixes calculation errors in the test data
3. Fills in missing answers for open questions using OpenAI
4. Submits the corrected file to the central server
"""
import os
import sys
import json
import re
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
CENTRALA_SOURCE_URL = os.getenv("CENTRALA_SOURCE_URL")
CENTRALA_REPORT_URL = os.getenv("CENTRALA_REPORT_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def download_json_file():
    """Download the JSON calibration file."""
    print("🔍 [*] Downloading JSON calibration file...")
    try:
        response = make_request(CENTRALA_SOURCE_URL.format(API_KEY=API_KEY))
        return json.loads(response.text)
    except Exception as e:
        print(f"❌ [-] Error downloading or parsing file: {str(e)}")
        sys.exit(1)

def fix_calculations(test_data):
    """Fix calculation errors in test data."""
    print("🧮 [*] Fixing calculation errors...")
    fixed_count = 0
    
    for item in test_data:
        question = item["question"]
        current_answer = item["answer"]
        
        # Check if the question is a calculation (contains numbers and operators)
        if re.match(r'^\s*[\d\s\+\-\*\/\(\)]+\s*$', question):
            # Safely evaluate the expression
            try:
                correct_answer = eval(question)
                if current_answer != correct_answer:
                    print(f"🔧 [-] Fixing: {question} = {current_answer} -> {correct_answer}")
                    item["answer"] = correct_answer
                    fixed_count += 1
            except Exception as e:
                print(f"⚠️ [!] Warning: Could not evaluate {question}: {str(e)}")
    
    print(f"✅ [+] Fixed {fixed_count} calculations")
    return test_data

def answer_open_questions(test_data):
    """Fill in answers for open questions using OpenAI."""
    print("🤖 [*] Answering open questions...")
    answered_count = 0
    
    questions_to_answer = []
    indices = []
    
    # First, collect all questions that need answers
    for i, item in enumerate(test_data):
        if "test" in item and "q" in item["test"] and item["test"].get("a") in [None, "???"]:
            questions_to_answer.append(item["test"]["q"])
            indices.append(i)
    
    # If there are no questions to answer, return
    if not questions_to_answer:
        print("📝 [*] No open questions found")
        return test_data
    
    print(f"❓ [?] Found {len(questions_to_answer)} open questions to answer")
    
    # Process questions in batches to avoid token limits
    batch_size = 10
    for i in range(0, len(questions_to_answer), batch_size):
        batch_questions = questions_to_answer[i:i+batch_size]
        batch_indices = indices[i:i+batch_size]
        
        # Create prompt for this batch
        prompt = "Please answer the following questions concisely and factually:\n\n"
        for j, q in enumerate(batch_questions):
            prompt += f"{j+1}. {q}\n"
        
        response = ask_llm(prompt, OPENAI_API_KEY)

        # Parse the answers and update the test data
        answers = parse_answers(response, len(batch_questions), batch_questions)
        
        for j, answer in enumerate(answers):
            if j < len(batch_indices):
                idx = batch_indices[j]
                test_data[idx]["test"]["a"] = answer
                answered_count += 1
                print(f"📝 [+] Answered: {batch_questions[j]} -> {answer}")
    
    
    print(f"✅ [+] Answered {answered_count} open questions")
    return test_data

def parse_answers(text, expected_count, questions=None):
    """Parse answers from the OpenAI response."""
    answers = []
    
    # Try to parse numbered responses (1. Answer, 2. Answer, etc.)
    numbered_pattern = re.compile(r'^\s*(\d+)\.\s*(.*?)(?=\s*\d+\.\s*|\Z)', re.MULTILINE | re.DOTALL)
    matches = numbered_pattern.findall(text)
    
    if matches and len(matches) == expected_count:
        for _, answer in matches:
            answers.append(answer.strip())
        return answers
    
    # If that doesn't work, split by lines and clean up
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    # Try to extract answers from each line
    for line in lines:
        # Remove numbers at the beginning (1., 2., etc.)
        line = re.sub(r'^\s*\d+\.\s*', '', line)
        
        # If the line starts with a question, skip it (if questions provided)
        if questions and any(q.lower() in line.lower() for q in questions):
            continue
        
        answers.append(line)
    
    # If we still don't have enough answers, just split the text into expected_count parts
    if len(answers) != expected_count:
        answers = text.split('\n\n')[:expected_count]
        if len(answers) < expected_count:
            # Pad with placeholder answers if needed
            answers.extend(["Answer not available"] * (expected_count - len(answers)))
    
    return [a.strip() for a in answers]

def submit_corrected_file(data):
    """Submit the corrected file to the central server."""
    print("📤 [*] Submitting corrected file...")
    
    # Construct the payload according to the required format
    payload = {
        "task": "JSON",
        "apikey": API_KEY,
        "answer": data
    }
    
    try:
        # Use make_request from utils for consistency
        response = make_request(
            CENTRALA_REPORT_URL, 
            method="post", 
            data=json.dumps(payload), 
            headers={"Content-Type": "application/json"}
        )
        print(f"✅ [+] Submission response: {response.text}")
        return response.json()
    except Exception as e:
        print(f"❌ [-] Error submitting file: {str(e)}")
        sys.exit(1)

def main():
    """Main execution function."""
    print("🚀 [*] Starting JSON file correction task...")
    
    # Download the JSON file
    data = download_json_file()
    
    # Get the test data array
    test_data = data.get("test-data", [])
    if not test_data:
        print("❌ [-] No test data found in the file")
        sys.exit(1)
    
    # Fix calculation errors
    test_data = fix_calculations(test_data)
    
    # Answer open questions
    test_data = answer_open_questions(test_data)
    
    # Update the test data in the original file
    data["test-data"] = test_data
    
    # Make sure the API key is set in both required locations
    data["apikey"] = API_KEY
    
    # Submit the corrected file
    result = submit_corrected_file(data)

    flag = find_flag_in_text(result.get("message", ""))
    
    print("✅ [+] Task completed successfully!")

if __name__ == "__main__":
    main()