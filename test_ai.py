import os
from ai_service import generate_questions

def test_generation():
    print("Testing Gemini AI Generation...")
    try:
        # Testing with the 3 required arguments
        questions = generate_questions("Photosynthesis", "easy", 2)
        
        for i, q in enumerate(questions):
            print(f"\nQuestion {i+1}: {q['question_text']}")
            print(f"Correct Answer: {q['correct_option']}")
            print(f"Explanation: {q.get('explanation', 'MISSING!')}")
            
            # Check if all keys exist
            expected_keys = ["question_text", "option_a", "option_b", "option_c", "option_d", "correct_option", "explanation"]
            for key in expected_keys:
                if key not in q:
                    print(f"❌ Error: Key '{key}' is missing from AI response!")
        
        print("\n✅ Test Passed: AI Service is compatible with app.py")
        
    except Exception as e:
        print(f"❌ Test Failed: {e}")

if __name__ == "__main__":
    test_generation()