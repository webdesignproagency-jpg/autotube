import google.generativeai as genai
import os

def get_model():
    genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
    return genai.GenerativeModel('gemini-1.5-flash')

async def generate(prompt: str) -> str:
    try:
        model = get_model()
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f'Error: {e}'
