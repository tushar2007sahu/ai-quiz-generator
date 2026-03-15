import requests

# 1. Your Render URL
BASE_URL = "https://ai-quiz-generator-lpay.onrender.com"

# Use a session object to keep cookies (login state)
s = requests.Session()

def run_test():
    print(f"🚀 Starting Test against: {BASE_URL}")

    # --- 🔵 STEP 1: Teacher Auth ---
    print("\n--- 🔵 STEP 1: Teacher Auth ---")
    teacher_data = {
        "username": "test_teacher",
        "email": "teacher@test.com",
        "password": "password123"
    }
    
    # Login (The map says /auth/login)
    login_res = s.post(f"{BASE_URL}/auth/login", json=teacher_data)
    if login_res.status_code != 200:
        print("Registering new teacher...")
        s.post(f"{BASE_URL}/auth/register", json=teacher_data)
        login_res = s.post(f"{BASE_URL}/auth/login", json=teacher_data)

    if login_res.status_code == 200:
        print("✅ Teacher logged in")
    else:
        print(f"❌ Auth Failed: {login_res.text}")
        return

    # --- 🔵 STEP 2: Create Quiz Shell ---
    print("\n--- 🔵 STEP 2: Create Quiz Shell ---")
    quiz_payload = {
        "title": "Cloud Computing Quiz",
        "description": "Testing Render Deployment"
    }
    # FIXED: Changed from /quiz/create to /quiz based on your url_map
    quiz_res = s.post(f"{BASE_URL}/quiz", json=quiz_payload)
    
    quiz_id = None
    if quiz_res.status_code in [200, 201]:
        data = quiz_res.json()
        # We check both keys just in case
        quiz_id = data.get("quiz_id") or data.get("id")
        print(f"✅ Quiz Shell created. ID: {quiz_id}")
    else:
        print(f"❌ Quiz Creation Failed: {quiz_res.status_code}")
        print(f"Server said: {quiz_res.text}")
        return

    # --- 🔵 STEP 3: Generate AI Questions ---
    print("\n--- 🔵 STEP 3: Generate AI Questions ---")
    if not quiz_id:
        print("❌ Cannot proceed: Quiz ID is missing from server response.")
        return

    # FIXED: Matches /ai/generate-questions/<int:quiz_id>
    ai_url = f"{BASE_URL}/ai/generate-questions/{quiz_id}"
    ai_payload = {
        "topic": "Python Functions",
        "difficulty": "easy",
        "num_questions": 2
    }
    
    print(f"Sending request to: {ai_url}")
    ai_res = s.post(ai_url, json=ai_payload)
    
    if ai_res.status_code == 200:
        print("✅ AI Questions Generated successfully!")
        questions = ai_res.json().get("questions", [])
        for q in questions:
            print(f"   - {q['question_text']}")
    else:
        print(f"❌ AI Error: {ai_res.status_code}")
        print(f"Response: {ai_res.text}")

if __name__ == "__main__":
    run_test()