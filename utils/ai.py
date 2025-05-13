"""OpenAI-related utility functions."""
from openai import OpenAI

def ask_llm(question: str, api_key: str, model: str = "gpt-4") -> str:
    """Send a question to the language model and get response.
    
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
            {"role": "system", "content": "Answer questions precisely and concisely. Provide very short responses with only necessery data. Response in Polish."},
            {"role": "user", "content": question},
        ]
    )
    return response.choices[0].message.content.strip()
