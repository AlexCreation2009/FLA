from flask import Flask, request, jsonify, g
import sqlite3
import json
import bcrypt

app = Flask(__name__)
DB_PATH = "users.db"

def get_db():
    if not hasattr(g, "db"):
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db = getattr(g, "db", None)
    if db is not None:
        db.close()

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # extra_data хранит JSON как текст
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            extra_data TEXT NOT NULL DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

@app.route("/users", methods=["POST"])
def create_user():
    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON is required"}), 400

    username = data.get("username")
    password = data.get("password")
    extra = data.get("extra", {})  # любые доп. данные: {"score": 100, "level": 5, ...}

    if not username or not password:
        return jsonify({"error": "username and password fields are required."}), 400

    salt = bcrypt.gensalt(rounds=12)
    password_hash = bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    # Превращаем extra в JSON-строку
    extra_json = json.dumps(extra, ensure_ascii=False)

    db = get_db()
    cur = db.cursor()

    try:
        cur.execute(
            "INSERT INTO users (username, password_hash, extra_data) VALUES (?, ?, ?)",
            (username, password_hash, extra_json),
        )
        db.commit()
        new_id = cur.lastrowid
        return jsonify({
            "id": new_id,
            "username": username,
            "extra": extra,
            "message": "User created"
        }), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "A user with this name already exists."}), 409

@app.route("/users/<int:user_id>", methods=["GET"])
def get_user(user_id):
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT id, username, extra_data, created_at FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    if row is None:
        return jsonify({"error": "User not found"}), 404

    extra = {}
    try:
        extra = json.loads(row["extra_data"])
    except Exception:
        extra = {}

    return jsonify({
        "id": row["id"],
        "username": row["username"],
        "created_at": row["created_at"],
        "extra": extra
    }), 200

@app.route("/users", methods=["GET"])
def list_users():
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT id, username, extra_data, created_at FROM users")
    rows = cur.fetchall()
    users = []
    for r in rows:
        extra = {}
        try:
            extra = json.loads(r["extra_data"])
        except Exception:
            extra = {}
        users.append({
            "id": r["id"],
            "username": r["username"],
            "created_at": r["created_at"],
            "extra": extra
        })
    return jsonify(users), 200

@app.route("/users/<int:user_id>", methods=["PATCH"])
def update_user_extra(user_id):
    """
    Обновляет только extra-данные (счёт, уровень, и т.д.).
    Пример тела запроса:
    {
      "extra": {
        "score": 250,
        "level": 6,
        "currency": 10
      }
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON is required"}), 400

    extra = data.get("extra")
    if extra is None or not isinstance(extra, dict):
        return jsonify({"error": "`extra` must be a JSON object"}), 400

    extra_json = json.dumps(extra, ensure_ascii=False)

    db = get_db()
    cur = db.cursor()
    cur.execute(
        "UPDATE users SET extra_data = ? WHERE id = ?",
        (extra_json, user_id),
    )
    db.commit()

    if cur.rowcount == 0:
        return jsonify({"error": "User not found"}), 404

    return jsonify({
        "id": user_id,
        "extra": extra,
        "message": "Data updated"
    }), 200

@app.route("/users/login", methods=["POST"])
def login():
    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON is required"}), 400

    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "username and password are required"}), 400

    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT id, username, password_hash FROM users WHERE username = ?", (username,))
    row = cur.fetchone()

    if row is None:
        return jsonify({"error": "Incorrect login or password"}), 401

    stored_hash = row["password_hash"].encode("utf-8")
    if bcrypt.checkpw(password.encode("utf-8"), stored_hash):
        return jsonify({
            "id": row["id"],
            "username": row["username"],
            "message": "Successful login"
        }), 200
    else:
        return jsonify({"error": "Incorrect login or password"}), 401

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
