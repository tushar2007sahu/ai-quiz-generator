import os
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# Initialize Gemini client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


class AIServiceError(Exception):
    """Custom exception for AI generation failures"""
    pass


def generate_questions(topic, difficulty, count):
    """
    Generates quiz questions using Gemini Flash and returns a validated list of questions.
    """

    prompt = f"""
You are a quiz generator.

Generate {count} multiple choice questions about "{topic}" with {difficulty} difficulty.

Return ONLY valid JSON.

The JSON must be an ARRAY of objects.

Each object must contain EXACTLY these fields:

question_text
option_a
option_b
option_c
option_d
correct_option
explanation

Rules:
- correct_option must be A, B, C, or D
- No markdown
- No extra text
- Only return the JSON array

Example:

[
 {{
  "question_text": "What does CPU stand for?",
  "option_a": "Central Processing Unit",
  "option_b": "Computer Personal Unit",
  "option_c": "Central Performance Utility",
  "option_d": "Control Processing Unit",
  "correct_option": "A",
  "explanation": "CPU stands for Central Processing Unit."
 }}
]
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            ),
        )

        content = response.text.strip()

        questions = json.loads(content)

        if not isinstance(questions, list):
            raise AIServiceError("AI response was not a list.")

        validated_questions = []

        required_fields = [
            "question_text",
            "option_a",
            "option_b",
            "option_c",
            "option_d",
            "correct_option",
        ]

        for q in questions:

            if not isinstance(q, dict):
                continue

            if not all(field in q for field in required_fields):
                continue

            if q["correct_option"] not in ["A", "B", "C", "D"]:
                continue

            validated_questions.append(q)

        if len(validated_questions) == 0:
            raise AIServiceError("AI returned no valid questions.")

        return validated_questions

    except json.JSONDecodeError as e:
        print("JSON Parse Error:", e)
        raise AIServiceError("AI returned invalid JSON.")

    except Exception as e:
        print("AI Service Error:", e)
        raise AIServiceError(str(e))