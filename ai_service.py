import os
import json
from google import genai
from google.genai import types  # Import types for stricter config
from dotenv import load_dotenv

load_dotenv()

# Initialize the new Gemini Client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

class AIServiceError(Exception):
    """Custom exception for AI generation failures"""
    pass

def generate_questions(topic, difficulty, count):
    """
    Generates quiz questions using the Gemini 2.0 Flash model.
    Forces JSON output for easier parsing.
    """
    prompt = f"""
    Generate {count} multiple-choice questions about '{topic}' at a '{difficulty}' difficulty level.
    The response must be a JSON array of objects.
    Each object must have these keys: 
    "question_text", "option_a", "option_b", "option_c", "option_d", "correct_option", "explanation".
    """

    try:
        # Use 'gemini-2.0-flash' (Standard stable model in 2026)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type='application/json' # Forces raw JSON output
            )
        )
        
        # In the new SDK, response.text contains the raw JSON string
        content = response.text.strip()
        
        # Load string into Python list/dictionary
        questions = json.loads(content)
        
        # Basic verification that we got a list
        if not isinstance(questions, list):
            raise AIServiceError("AI returned an object instead of a list.")
            
        return questions

    except json.JSONDecodeError as e:
        print(f"JSON Parsing Error: {str(e)} | Content: {content}")
        raise AIServiceError("AI generated invalid JSON format.")
    except Exception as e:
        print(f"AI Service Error: {str(e)}")
        raise AIServiceError(f"Generation failed: {str(e)}")