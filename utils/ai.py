from openai import OpenAI

DEFAULT_CONTEXT = "Answer questions precisely and concisely. Provide very short responses with only necessary data."

def ask_llm(question: str, api_key: str, model: str = "gpt-4o", context: str = DEFAULT_CONTEXT) -> str:
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": context},
            {"role": "user", "content": question},
        ]
    )
    return response.choices[0].message.content.strip()
