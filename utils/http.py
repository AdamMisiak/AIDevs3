import re
import requests
from bs4 import BeautifulSoup
from openai import OpenAI

def extract_question(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    p = soup.find("p", id="human-question")
    if not p:
        raise Exception("Question not found in HTML")
    
    question_text = p.get_text(strip=True).replace("Question:", "").strip()
    return question_text

def find_url_in_text(text: str) -> str:
    url_match = re.search(r'(https://[^\s\'"]+)', text)
    if not url_match:
        raise Exception("No URL found in the response")
    return url_match.group(1)

def find_flag_in_text(text: str) -> str:
    flag_match = re.search(r'FLAG{[^}]+}', text)
    if not flag_match:
        raise Exception("No flag found in the response")
    return flag_match.group(0)

def make_request(url: str, method: str = "get", **kwargs) -> requests.Response:
    try:
        if method.lower() == "get":
            response = requests.get(url, **kwargs)
        elif method.lower() == "post":
            response = requests.post(url, **kwargs)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        raise Exception(f"Request failed: {str(e)}")
