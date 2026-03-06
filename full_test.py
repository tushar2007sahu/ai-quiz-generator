import requests

BASE_URL = "http://127.0.0.1:5000"
session = requests.Session()

def run_full_test():
    print("🚀 Starting Full Project Flow Test...")

    # 1. REGISTER
    print("\n[1/6] Registering new user...")
    reg_data = {"username": "tester1", "password": "password123"}
    session.post(f"{BASE_URL}/auth/register", json=reg_data) 
    print("✅ Register Step complete.")

    # 2. LOGIN
    print("\n[2/6] Logging in...")
    login_response = session.post(f"{BASE_URL}/auth/login", json=reg_data)
    if login_response.status_code in [200, 201]:
        print("✅ Login Successful!")
    else:
        print(f"❌ Login Failed! Status: {login_response.status_code}")
        return

    # 3. CREATE QUIZ
    print("\n[3/6] Creating Quiz Metadata...")
    quiz_response = session.post(f"{BASE_URL}/quiz", json={"title": "Odisha Quiz"})
    if quiz_response.status_code not in [200, 201]:
        print(f"❌ Quiz Metadata Failed: {quiz_response.text}")
        return
    quiz_data = quiz_response.json()
    quiz_id = quiz_data.get('quiz_id') or quiz_data.get('id')
    print(f"✅ Quiz Metadata Created. ID: {quiz_id}")

    # 4. AI GENERATE QUESTIONS
    print(f"\n[4/6] Generating AI Questions for Quiz {quiz_id}...")
    ai_data = {"topic": "Odisha History", "difficulty": "easy", "count": 3}
    ai_res = session.post(f"{BASE_URL}/ai/generate-questions/{quiz_id}", json=ai_data)
    if ai_res.status_code in [200, 201]:
        print("✅ AI Questions added to Database!")
    else:
        print(f"❌ AI Generation failed: {ai_res.text}")
        return

    # 5. START SESSION
    print("\n[5/6] Starting Quiz Session...")
    start_res = session.post(f"{BASE_URL}/quiz/{quiz_id}/start")
    start_data = start_res.json()
    code = start_data.get('code') or start_data.get('session_code')
    
    if not code:
        print(f"❌ Failed to get code. Response: {start_data}")
        return
    print(f"✅ Session Started! Join Code: {code}")

    # 6. JOIN SESSION
    print("\n[6/6] Joining Session...")
    # FIX: Using 'name' instead of 'username' to match your app.py line 225
    join_payload = {
        "session_code": code, 
        "name": "tester1" 
    }
    join_res = session.post(f"{BASE_URL}/session/join", json=join_payload)
    
    if join_res.status_code in [200, 201] or (join_res.history and join_res.history[0].status_code == 302):
        print(f"\n✨ ✨ ✨ SUCCESS! ✨ ✨ ✨")
        print(f"The entire backend logic is working perfectly.")
        print(f"Your AI is generating, Database is saving, and Session is joining!")
    else:
        print(f"❌ Join failed: {join_res.text}")

if __name__ == "__main__":
    run_full_test()