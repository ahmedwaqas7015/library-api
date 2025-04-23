from flask import Flask, request, jsonify
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, get_jwt_identity,
    get_jwt
    )
from passlib.hash import pbkdf2_sha256
from datetime import timedelta
import sqlite3
import os

app = Flask(__name__)


# JWT Configuration
app.config['JWT_SECRET_KEY'] = "12345678"
app.config['TESTING'] = False 
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(minutes=15)
app.config['JWT_BLACKLIST_ENABLED'] = True
app.config['JWT_BLACKLIST_TOKEN_CHECKS'] = ['access']
jwt = JWTManager(app)

jwt_blacklist = set()

def get_db_connection():
    db_path = "test_books.db" if app.config["TESTING"] else os.path.join(os.path.dirname(__file__), "books.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    try:
        with get_db_connection() as conn:
            # create users table
            conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL
            )
        ''')
            # create books table
            conn.execute('''
            CREATE TABLE IF NOT EXISTS books ( 
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                read INTEGER DEFAULT 0,
                user_id INTEGER NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
            conn.commit()
    except sqlite3.Error as e:
        print(f"Error initializing database: {e}")

with app.app_context():
    init_db()

@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    jti = jwt_payload['jti']
    return jti in jwt_blacklist

# User registration
@app.route("/register", methods=["POST"])
def register():
    username = request.form.get("username")
    password = request.form.get("password")
    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400
    
    with get_db_connection() as conn:
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if user:
            return jsonify({"error": "User already exists"}), 400

        hashed_password = pbkdf2_sha256.hash(password)
        conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
        conn.commit()
    return jsonify({"message": "User registered successfully"})

# loging and get JWT
@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username")
    password = request.form.get("password")
    if not username or not password:
        return jsonify({"error": "Username and Password are required"}), 400
    with get_db_connection() as conn:
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if not user or not pbkdf2_sha256.verify(password, user['password']):
            return jsonify({"error": "Invalid credentials"}), 401
    # Create JWT token
    access_token = create_access_token(identity=username)
    return jsonify({"message": "Login successful", "access_token": access_token})        

# add a book
@app.route("/books", methods=["POST"])
@jwt_required() # add book (protected)
def add_book():
    title = request.form.get("title")
    author = request.form.get("author")
    if not title or not author:
        return jsonify({"error": "Title and author are required"}), 400
    user_id = get_jwt_identity()
    with get_db_connection() as conn:
        cursor = conn.execute("INSERT INTO books (title, author, user_id) values (?, ?, ?)", (title, author, user_id))
        conn.commit()
    book_id = cursor.lastrowid
    return jsonify({"message": "Book added", "book": {"id": book_id, "title": title, "author": author, "read": False}}), 201

# get all books
@app.route("/books", methods=["GET"])
@jwt_required() # get all books (protected)
def get_books():
    user_id = get_jwt_identity()
    with get_db_connection() as conn:
        books = conn.execute("SELECT * FROM books WHERE user_id = ?", (user_id,)).fetchall()
    if len(books) == 0:
        return jsonify({"error": "No books found"}), 404
    books_list = [{"id": book['id'], "title": book['title'], "author": book['author'], "read": bool(book['read'])} for book in books]
    return jsonify(books_list)


# get specific book
@app.route("/books/<int:book_id>", methods=["GET"])
@jwt_required() # get specific book (protected)
def get_book(book_id):
    user_id = get_jwt_identity()
    with get_db_connection() as conn:
        book = conn.execute("SELECT * FROM books WHERE id = ? AND user_id = ?", (book_id, user_id)).fetchone()
    if book is None:
        return jsonify({"error": "Book not found"}), 404
    return jsonify({"id": book['id'], "title": book['title'], "author": book['author'], "read": bool(book['read'])})


# update a book
@app.route("/books/<int:book_id>", methods=["PUT"])
@jwt_required() # update book (protected)
def update_book(book_id):
    title = request.form.get("title")
    author = request.form.get("author")
    if not title or not author:
        return jsonify({"error": "Title and author are required"}), 400
    user_id = get_jwt_identity()
    with get_db_connection() as conn:
        cursor = conn.execute("UPDATE books SET title = ?, author = ? WHERE id = ? AND user_id = ?", (title, author, book_id, user_id))
        conn.commit()
    if cursor.rowcount == 0:
        return jsonify({"error": "Book not found"}), 404
    with get_db_connection() as conn:
        book = conn.execute("SELECT * FROM books WHERE id = ? AND user_id = ?", (book_id, user_id)).fetchone()
        conn.commit()
    return jsonify({"message": f"Book {book_id} updated", "book": {"id": book_id, "author": book['author'], "title": book['title'], "read": bool(book['read'])}})

# mark book as read
@app.route("/books/<int:book_id>", methods=["PATCH"])
@jwt_required() # toggle status (protected)
def toggle_book_read(book_id):
    read = request.form.get("read")
    if read not in ["true", "false"]:
        return jsonify({"error": "Invalid read status"}), 400
    user_id = get_jwt_identity()
    with get_db_connection() as conn:
        cursor = conn.execute("UPDATE books SET read = ? where id = ? AND user_id = ?", (read, book_id, user_id))
        conn.commit()
    if cursor.rowcount == 0:
        return jsonify({"error": "Book not found"}), 404
    return jsonify({"message": f"Book {book_id} status updated", "read": bool(read)})

# delete using DELETE
@app.route("/books/<int:book_id>", methods=["DELETE"])
@jwt_required() # delete book (protected)
def delete_book_delete(book_id):
    user_id = get_jwt_identity()
    with get_db_connection() as conn:
        cursor = conn.execute("DELETE FROM books where id = ? AND user_id = ?", (book_id, user_id))
        conn.commit()
    if cursor.rowcount == 0:
        return jsonify({"error": "Book not found"}), 404
    return jsonify({"message": f"Book {book_id} deleted"})

@app.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    jti = get_jwt()['jti']
    jwt_blacklist.add(jti)
    return jsonify({"message": "Token revoked"})


if __name__ == "__main__":
    app.run(debug=True)
