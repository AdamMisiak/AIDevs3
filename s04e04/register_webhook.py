"""
Helper script to register webhook URL with centrala.

Usage:
1. Start the main server first: python main.py
2. Expose it via ngrok: ngrok http 8000
3. Run this script with your public URL: python register_webhook.py https://your-ngrok-url.ngrok.io/drone
"""
import os
import sys
import requests
from dotenv import load_dotenv

# Add parent directory to Python path to allow imports from shared utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import (
    make_request,
    find_flag_in_text
)

# Load environment variables
load_dotenv()

API_KEY = os.getenv("API_KEY")
CENTRALA_REPORT_URL = os.getenv("CENTRALA_REPORT_URL")


def register_webhook_url(webhook_url: str):
    """Register webhook URL with centrala."""
    print(f"📝 [*] Registering webhook URL: {webhook_url}")
    
    # Validate URL format
    if not webhook_url.startswith("https://"):
        print(f"❌ [-] Error: URL must start with https://")
        return False
    
    if not webhook_url.endswith("/drone"):
        print(f"⚠️ [!] Warning: URL should end with /drone endpoint")
    
    payload = {
        "task": "webhook",
        "apikey": API_KEY,
        "answer": webhook_url
    }
    
    print(f"📤 [*] Sending registration to centrala...")
    print(f"📦 [*] Payload: {payload}")
    
    try:
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
            return True
        except Exception:
            print(f"⚠️ [!] No flag found in response - centrala might still be testing your webhook")
            print(f"⏳ [*] Keep your server running and wait for centrala to test it")
            return True
    
    except Exception as e:
        print(f"❌ [-] Error registering webhook: {str(e)}")
        return False


def main():
    """Main function."""
    if len(sys.argv) != 2:
        print(f"Usage: python register_webhook.py <webhook_url>")
        print(f"Example: python register_webhook.py https://abc123.ngrok.io/drone")
        sys.exit(1)
    
    webhook_url = sys.argv[1]
    
    print(f"🚀 [*] Webhook Registration Tool")
    print(f"🔗 [*] URL to register: {webhook_url}")
    
    success = register_webhook_url(webhook_url)
    
    if success:
        print(f"✅ [+] Registration completed!")
        print(f"⏳ [*] Keep your main server running - centrala will test it now")
    else:
        print(f"❌ [-] Registration failed")
        sys.exit(1)


if __name__ == "__main__":
    main() 