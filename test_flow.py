import requests

BASE_URL = "http://127.0.0.1:5000"

def run_test():
    teacher = requests.Session()
    student = requests.Session()

    print("--- 🔵 STEP 1: Teacher Auth ---")
    # Using /auth/register and /auth/login
    teacher.post(f"{BASE_URL}/auth/register", json={
        "username": "teacher_pro", "password": "password123", "role": "teacher"
    })
    teacher.post(f"{BASE_URL}/auth/login", json={
        "username": "teacher_pro", "password": "password123"
    })
    print("✅ Teacher logged in via /auth/login")

    print("\n--- 🔵 STEP 2: Create Quiz Shell ---")
    # According to your routes, you have a /quiz endpoint to create the container
    quiz_resp = teacher.post(f"{BASE_URL}/quiz", json={
        "title": "Science Quiz"
    }).json()
    quiz_id = quiz_resp.get("id") or quiz_resp.get("quiz_id")
    print(f"✅ Quiz Shell created. ID: {quiz_id}")

    print("\n--- 🔵 STEP 3: Generate AI Questions ---")
    # Route: /ai/generate-questions/<quiz_id>
    ai_resp = teacher.post(f"{BASE_URL}/ai/generate-questions/{quiz_id}", json={
        "topic": "Biology", "difficulty": "easy", "count": 2
    })
    if ai_resp.status_code != 200:
        print(f"❌ AI Error: {ai_resp.text}")
        return
    print("✅ AI Questions added to quiz.")

    print("\n--- 🔵 STEP 4: Start Session ---")
    # Route: /quiz/<quiz_id>/start
    session_resp = teacher.post(f"{BASE_URL}/quiz/{quiz_id}/start").json()
    code = session_resp.get("session_code") or session_resp.get("code")
    print(f"✅ Session started! Code: {code}")

    print("\n--- 🟡 STEP 5: Student Join ---")
    # Route: /session/join
    student.post(f"{BASE_URL}/session/join", json={
        "session_code": code, "nickname": "Student_1"
    })
    print(f"✅ Student joined via /session/join")

    print("\n--- 🔵 STEP 6: Teacher Begins Session ---")
    # Route: /session/<code>/begin
    teacher.post(f"{BASE_URL}/session/{code}/begin")
    print("✅ Session is now ACTIVE.")

    print("\n--- 🟡 STEP 7: Student Answer ---")
    # Route: /session/<code>/answer
    # Note: You might need to fetch the question_id first from /session/<code>/question
    # For now, let's assume question_id 1
    ans_resp = student.post(f"{BASE_URL}/session/{code}/answer", json={
        "question_id": 1, "selected_option": "a"
    }).json()
    print(f"✅ Answer submitted: {ans_resp.get('message')}")

    print("\n--- 🏆 FINAL STEP: Leaderboard ---")
    # Route: /session/<code>/leaderboard
    lb = teacher.get(f"{BASE_URL}/session/{code}/leaderboard").json()
    print("Leaderboard Results:")
    for entry in lb:
        print(f"- {entry['nickname']}: {entry['score']} pts")

if __name__ == "__main__":
    run_test()