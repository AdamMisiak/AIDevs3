"""
Task S02E03: Robot Image Generation

This script:
1. Downloads a robot description from the central server
2. Generates an image of the robot using DALL-E 3 based on the description
3. Submits the image URL to the central server
"""
import os
import sys
import json
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
ROBOT_DESCRIPTION_URL = os.getenv("ROBOT_DESCRIPTION_URL")
CENTRALA_REPORT_URL = os.getenv("CENTRALA_REPORT_URL")


def download_robot_description():
    """Download the robot description from the central server."""
    print("🔍 [*] Downloading robot description...")
    try:
        response = make_request(ROBOT_DESCRIPTION_URL.format(API_KEY=API_KEY))
        data = response.json()
        print(f"✅ [+] Successfully downloaded robot description")
        return data
    except Exception as e:
        print(f"❌ [-] Error downloading robot description: {str(e)}")
        sys.exit(1)


def generate_robot_image(robot_description):
    """Generate an image of the robot using DALL-E 3."""
    print("🤖 [*] Generating robot image...")
    
    # Extract description from the JSON response
    description = robot_description.get("description", "")
    if not description:
        print("❌ [-] No robot description found in the response")
        sys.exit(1)
    
    print(f"📝 [*] Robot description: {description}")
    
    # Create prompt for DALL-E 3
    prompt = f"""
    Generate a photorealistic image of a robot with the following description:
    
    {description}
    
    The robot should be clearly visible, centered in the image, with appropriate lighting and detail.
    Make it look like a high-quality photograph or 3D render.
    """
    
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
            response_format="url"
        )
        
        # Get the image URL from the response
        image_url = response.data[0].url
        print(f"🖼️ [+] Successfully generated robot image: {image_url}")
        return image_url
    except Exception as e:
        print(f"❌ [-] Error generating robot image: {str(e)}")
        sys.exit(1)


def submit_image_url(image_url):
    """Submit the image URL to the central server."""
    print("📤 [*] Submitting image URL...")
    
    # Prepare payload
    payload = {
        "task": "robotid",
        "apikey": API_KEY,
        "answer": image_url
    }
    
    try:
        response = make_request(
            CENTRALA_REPORT_URL,
            method="post",
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"}
        )
        
        print(f"✅ [+] Submission response: {response.text}")
        
        # Check for flag in response
        try:
            flag = find_flag_in_text(response.text)
            print(f"🚩 [+] Flag found: {flag}")
        except Exception as e:
            print(f"⚠️ [!] No flag found in response")
        
        return response.json()
    except Exception as e:
        print(f"❌ [-] Error submitting image URL: {str(e)}")
        sys.exit(1)


def main():
    """Main execution function."""
    print("🚀 [*] Starting Robot Image Generation task...")
    
    # Download robot description
    robot_description = download_robot_description()
    print(robot_description)
    
    # Generate robot image
    image_url = generate_robot_image(robot_description)
    print(image_url)
    
    # Submit image URL
    result = submit_image_url(image_url)
    print(result)
    
    print("✅ [+] Task completed successfully!")


if __name__ == "__main__":
    main()