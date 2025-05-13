"""HTML parsing utility functions."""
from bs4 import BeautifulSoup

def extract_question(html: str) -> str:
    """Extract question from HTML content.
    
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
