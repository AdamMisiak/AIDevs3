"""
Helper script to prepare JSONL training data for fine-tuning

This script:
1. Loads correct.txt and incorrect.txt files
2. Creates JSONL format training data
3. Saves the training data as training_data.jsonl
"""
import os
import json


def prepare_training_data():
    """Prepare JSONL training data from correct and incorrect files."""
    print("📝 [*] Preparing training data for fine-tuning...")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, "data")
    
    # Load correct data
    correct_file = os.path.join(data_dir, "correct.txt")
    incorrect_file = os.path.join(data_dir, "incorrect.txt")
    
    training_data = []
    
    # Process correct data
    try:
        with open(correct_file, 'r', encoding='utf-8') as f:
            correct_lines = [line.strip() for line in f.readlines() if line.strip()]
        
        print(f"✅ [+] Loaded {len(correct_lines)} correct samples")
        
        for line in correct_lines:
            training_example = {
                "messages": [
                    {"role": "system", "content": "validate data"},
                    {"role": "user", "content": line},
                    {"role": "assistant", "content": "1"}
                ]
            }
            training_data.append(training_example)
    
    except Exception as e:
        print(f"❌ [-] Error loading correct data: {str(e)}")
        return
    
    # Process incorrect data
    try:
        with open(incorrect_file, 'r', encoding='utf-8') as f:
            incorrect_lines = [line.strip() for line in f.readlines() if line.strip()]
        
        print(f"✅ [+] Loaded {len(incorrect_lines)} incorrect samples")
        
        for line in incorrect_lines:
            training_example = {
                "messages": [
                    {"role": "system", "content": "validate data"},
                    {"role": "user", "content": line},
                    {"role": "assistant", "content": "0"}
                ]
            }
            training_data.append(training_example)
    
    except Exception as e:
        print(f"❌ [-] Error loading incorrect data: {str(e)}")
        return
    
    # Save training data as JSONL
    output_file = os.path.join(script_dir, "training_data.jsonl")
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            for example in training_data:
                f.write(json.dumps(example, ensure_ascii=False) + '\n')
        
        print(f"✅ [+] Saved {len(training_data)} training examples to: {output_file}")
        print(f"📊 [*] Training data summary:")
        print(f"    Total examples: {len(training_data)}")
        print(f"    Correct examples: {len(correct_lines)}")
        print(f"    Incorrect examples: {len(incorrect_lines)}")
        
        # Show first few examples
        print(f"\n📋 [*] Sample training examples:")
        for i, example in enumerate(training_data[:3]):
            print(f"Example {i+1}: {json.dumps(example, ensure_ascii=False)}")
    
    except Exception as e:
        print(f"❌ [-] Error saving training data: {str(e)}")


if __name__ == "__main__":
    prepare_training_data() 