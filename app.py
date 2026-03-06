import os
import random
import string
from datetime import datetime, timezone
from functools import wraps

from flask import Flask, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from models import db, Teacher, Quiz, Question, Session, Participant, Answer
from ai_service import generate_questions, AIServiceError

load_dotenv()

app = Flask(__name__)
# --- THE HOTFIX START ---
# 1. Get the URL from Render's environment
database_url = os.getenv("DATABASE_URL")

# 2. Fix the "postgres://" vs "postgresql://" issue
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

# 3. Use Postgres if available, otherwise fall back to local SQLite
app.config["SQLALCHEMY_DATABASE_URI"] = database_url or "sqlite:///quiz.db"
# --- THE HOTFIX END ---

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.secret_key = os.getenv("FLASK_SECRET", "dev-secret-replace-this")



db.init_app(app)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

QUESTION_TIME_LIMIT = 30

# ---------------- DECORATORS ----------------

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "teacher_id" not in session:
            return jsonify({"error": "Authentication required"}), 401
        return f(*args, **kwargs)
    return decorated_function

# ---------------- HELPERS ----------------

def time_left(session_obj):
    if not session_obj.question_start_time:
        return QUESTION_TIME_LIMIT
    now = datetime.now(timezone.utc)
    start_time = session_obj.question_start_time.replace(tzinfo=timezone.utc)
    elapsed = (now - start_time).total_seconds()
    return max(0, QUESTION_TIME_LIMIT - int(elapsed))

def advance_question_if_needed(session_obj, questions):
    if time_left(session_obj) == 0:
        if session_obj.current_question_index < len(questions) - 1:
            session_obj.current_question_index += 1
            session_obj.question_start_time = datetime.now(timezone.utc)
        else:
            session_obj.is_active = False
        db.session.commit()

def get_unique_session_code():
    while True:
        code = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        if not Session.query.filter_by(session_code=code).first():
            return code

# ---------------- AUTH ----------------

@app.route("/auth/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    if not data.get("username") or not data.get("password"):
        return jsonify({"error": "Missing username or password"}), 400

    hashed = generate_password_hash(data["password"])
    teacher = Teacher(username=data["username"], password_hash=hashed)

    try:
        db.session.add(teacher)
        db.session.commit()
        return jsonify({"message": "Registered"}), 201
    except:
        db.session.rollback()
        return jsonify({"error": "Username already exists"}), 400

@app.route("/auth/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    teacher = Teacher.query.filter_by(username=data.get("username")).first()

    if teacher and check_password_hash(teacher.password_hash, data.get("password")):
        session["teacher_id"] = teacher.id
        return jsonify({"message": "Logged in"}), 200

    return jsonify({"error": "Invalid credentials"}), 401

@app.route("/auth/logout", methods=["POST"])
def logout():
    session.pop("teacher_id", None)
    return jsonify({"message": "Logged out"}), 200

# ---------------- QUIZ & AI ----------------

@app.route("/quiz", methods=["POST"])
@login_required
def create_quiz():
    data = request.get_json() or {}
    if not data.get("title"):
        return jsonify({"error": "Title required"}), 400

    quiz = Quiz(title=data["title"], teacher_id=session["teacher_id"])
    db.session.add(quiz)
    db.session.commit()
    return jsonify({"quiz_id": quiz.id}), 201

@app.route("/ai/generate-questions/<int:quiz_id>", methods=["POST"])
@login_required
def generate_ai_questions_route(quiz_id):

    quiz = Quiz.query.filter_by(id=quiz_id, teacher_id=session["teacher_id"]).first()
    if not quiz:
        return jsonify({"error": "Unauthorized or Quiz not found"}), 403

    data = request.get_json() or {}
    topic = data.get("topic")
    count = data.get("count", 5)
    difficulty = data.get("difficulty", "medium")

    if not topic or not isinstance(count, int) or not (1 <= count <= 10):
        return jsonify({"error": "Invalid input. Count 1-10 and topic required."}), 400

    if difficulty not in ["easy", "medium", "hard"]:
        return jsonify({"error": "Invalid difficulty"}), 400

    try:
        raw_questions = generate_questions(topic, difficulty, count)
    except AIServiceError as e:
        return jsonify({"error": str(e)}), 500

    added_count = 0

    for q in raw_questions:

        if Question.query.filter_by(quiz_id=quiz_id, question_text=q["question_text"]).first():
            continue

        options_list = [
            (q["option_a"], "A"),
            (q["option_b"], "B"),
            (q["option_c"], "C"),
            (q["option_d"], "D")
        ]

        correct_text = None
        for text, letter in options_list:
            if letter == q["correct_option"]:
                correct_text = text
                break

        if not correct_text:
            continue

        random.shuffle(options_list)

        mapping = ["A", "B", "C", "D"]
        new_correct_letter = None

        for i, opt in enumerate(options_list):
            if opt[0] == correct_text:
                new_correct_letter = mapping[i]
                break

        if not new_correct_letter:
            continue

        new_q = Question(
            quiz_id=quiz_id,
            question_text=q["question_text"],
            option_a=options_list[0][0],
            option_b=options_list[1][0],
            option_c=options_list[2][0],
            option_d=options_list[3][0],
            correct_option=new_correct_letter,
            explanation=q.get("explanation")
        )

        db.session.add(new_q)
        added_count += 1

    db.session.commit()

    return jsonify({"message": f"Added {added_count} unique questions"}), 200

# ---------------- LIVE SESSION ----------------

@app.route("/quiz/<int:quiz_id>/start", methods=["POST"])
@login_required
def create_session(quiz_id):

    quiz = Quiz.query.filter_by(id=quiz_id, teacher_id=session["teacher_id"]).first()
    if not quiz:
        return jsonify({"error": "Unauthorized"}), 403

    code = get_unique_session_code()

    session_obj = Session(quiz_id=quiz_id, session_code=code)
    db.session.add(session_obj)
    db.session.commit()

    return jsonify({"session_code": code}), 201

@app.route("/session/<code>/begin", methods=["POST"])
@login_required
def begin_session(code):

    session_obj = Session.query.filter_by(session_code=code, is_active=True).first()
    if not session_obj:
        return jsonify({"error": "Not found"}), 404

    if session_obj.quiz.teacher_id != session["teacher_id"]:
        return jsonify({"error": "Unauthorized"}), 403

    if Question.query.filter_by(quiz_id=session_obj.quiz_id).count() == 0:
        return jsonify({"error": "No questions"}), 400

    session_obj.has_started = True
    session_obj.question_start_time = datetime.now(timezone.utc)
    db.session.commit()

    return jsonify({"message": "Quiz started"})

@app.route("/session/join", methods=["POST"])
def join():
    data = request.get_json() or {}

    session_obj = Session.query.filter_by(
        session_code=data.get("session_code"),
        is_active=True
    ).first()

    if not session_obj:
        return jsonify({"error": "Invalid session"}), 404

    if Participant.query.filter_by(session_id=session_obj.id).count() >= 30:
        return jsonify({"error": "Session full"}), 403

    if Participant.query.filter_by(session_id=session_obj.id, name=data.get("name")).first():
        return jsonify({"error": "Name already taken"}), 400

    p = Participant(session_id=session_obj.id, name=data.get("name"))
    db.session.add(p)
    db.session.commit()

    return jsonify({"participant_id": p.id})

@app.route("/session/<code>/question", methods=["GET"])
def get_current_question(code):

    session_obj = Session.query.filter_by(session_code=code, is_active=True).first()
    if not session_obj or not session_obj.has_started:
        return jsonify({"status": "waiting"})

    questions = Question.query.filter_by(
        quiz_id=session_obj.quiz_id
    ).order_by(Question.id).all()

    advance_question_if_needed(session_obj, questions)

    if not session_obj.is_active:
        return jsonify({"status": "completed"})

    q = questions[session_obj.current_question_index]

    return jsonify({
        "question": q.question_text,
        "options": {
            "A": q.option_a,
            "B": q.option_b,
            "C": q.option_c,
            "D": q.option_d
        },
        "time_left": time_left(session_obj)
    })

@app.route("/session/<code>/answer", methods=["POST"])
def submit_answer(code):

    data = request.get_json() or {}

    session_obj = Session.query.filter_by(session_code=code, is_active=True).first()
    if not session_obj or not session_obj.has_started:
        return jsonify({"error": "Inactive"}), 400

    if time_left(session_obj) <= 0:
        return jsonify({"error": "TIME_UP"}), 400

    participant = Participant.query.filter_by(
        id=data.get("participant_id"),
        session_id=session_obj.id
    ).first()

    if not participant:
        return jsonify({"error": "Invalid participant"}), 400

    questions = Question.query.filter_by(
        quiz_id=session_obj.quiz_id
    ).order_by(Question.id).all()

    current_q = questions[session_obj.current_question_index]

    if Answer.query.filter_by(
        participant_id=participant.id,
        question_id=current_q.id
    ).first():
        return jsonify({"error": "Already answered"}), 400

    is_correct = data.get("answer") == current_q.correct_option

    if is_correct:
        participant.score += 10

    ans = Answer(
        participant_id=participant.id,
        question_id=current_q.id,
        selected_option=data.get("answer"),
        is_correct=is_correct
    )

    db.session.add(ans)
    db.session.commit()

    return jsonify({
        "correct": is_correct,
        "score": participant.score,
        "explanation": current_q.explanation if (is_correct or time_left(session_obj) == 0) else "Keep going!"
    })

@app.route("/session/<code>/leaderboard", methods=["GET"])
def leaderboard(code):

    session_obj = Session.query.filter_by(session_code=code).first()
    if not session_obj:
        return jsonify({"error": "Session not found"}), 404

    pts = Participant.query.filter_by(
        session_id=session_obj.id
    ).order_by(Participant.score.desc()).all()

    return jsonify({
        "leaderboard": [{"name": p.name, "score": p.score} for p in pts]
    })

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
