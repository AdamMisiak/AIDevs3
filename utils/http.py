"""Common utility functions for AI Devs 3 tasks."""
import re
import requests
from bs4 import BeautifulSoup
from openai import OpenAI

def extract_question(html: str) -> str:
    """🔍 Extract question from HTML content.
    
    Args:
        html: HTML content to parse
        
    Returns:
        Extracted question text
        
    Raises:
        Exception: If question is not found in HTML
    """
    soup = BeautifulSoup(html, "html.parser")
    p = soup.find("p", id="human-question")
    if not p:
        raise Exception("Question not found in HTML")
    
    question_text = p.get_text(strip=True).replace("Question:", "").strip()
    return question_text

def ask_llm(question: str, api_key: str, model: str = "gpt-4") -> str:
    """🤖 Send a question to the language model and get response.
    
    Args:
        question: The question to ask
        api_key: OpenAI API key
        model: Model to use (default: gpt-4)
        
    Returns:
        Model's response
    """
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "Answer questions precisely and concisely."},
            {"role": "user", "content": question},
        ]
    )
    return response.choices[0].message.content.strip()

def find_url_in_text(text: str) -> str:
    """🔗 Find and extract URL from text.
    
    Args:
        text: Text to search in
        
    Returns:
        Extracted URL
        
    Raises:
        Exception: If no URL is found
    """
    url_match = re.search(r'(https://[^\s\'"]+)', text)
    if not url_match:
        raise Exception("No URL found in the response")
    return url_match.group(1)

def find_flag_in_text(text: str) -> str:
    """🚩 Find and extract flag from text.
    
    Args:
        text: Text to search in
        
    Returns:
        Extracted flag
        
    Raises:
        Exception: If no flag is found
    """
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
