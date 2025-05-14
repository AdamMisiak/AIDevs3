from bs4 import BeautifulSoup

def extract_question(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    p = soup.find("p", id="human-question")
    if not p:
        raise Exception("Question not found in HTML")
    
    question_text = p.get_text(strip=True).replace("Question:", "").strip()
    return question_text
