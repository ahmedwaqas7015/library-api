from flask import Flask, request, jsonify
import sqlite3
import os

app = Flask(__name__)


def get_db_connection():
    db_path = os.path.join(os.path.dirname(__file__), "books.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    try:
        with get_db_connection() as conn:
            conn.execute('''
            CREATE TABLE IF NOT EXISTS books ( 
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                read INTEGER DEFAULT 0
                )
        ''')
            conn.commit()
    except sqlite3.Error as e:
        print(f"Error initializing database: {e}")

with app.app_context():
    init_db()

# add a book
@app.route("/books", methods=["POST"])
def add_book():
    title = request.form.get("title")
    author = request.form.get("author")
    if not title or not author:
        return jsonify({"error": "Title and author are required"}), 400
    with get_db_connection() as conn:
        cursor = conn.execute("INSERT INTO books (title, author) values (?, ?)", (title, author))
        conn.commit()
    book_id = cursor.lastrowid
    return jsonify({"message": "Book added", "book": {"id": book_id, "title": title, "author": author, "read": False}}), 201

# get all books
@app.route("/books", methods=["GET"])
def get_books():
    with get_db_connection() as conn:
        books = conn.execute("SELECT * FROM books").fetchall()
    if len(books) == 0:
        return jsonify({"error": "No books found"}), 404
    books_list = [{"id": book['id'], "title": book['title'], "author": book['author'], "read": bool(book['read'])} for book in books]
    return jsonify(books_list)


# get specific book
@app.route("/books/<int:book_id>", methods=["GET"])
def get_book(book_id):
    with get_db_connection() as conn:
        book = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if book is None:
        return jsonify({"error": "Book not found"}), 404
    return jsonify({"id": book['id'], "title": book['title'], "author": book['author'], "read": bool(book['read'])})


# update a book
@app.route("/books/<int:book_id>", methods=["PUT"])
def update_book(book_id):
    title = request.form.get("title")
    author = request.form.get("author")
    if not title or not author:
        return jsonify({"error": "Title and author are required"}), 400
    with get_db_connection() as conn:
        cursor = conn.execute("UPDATE books SET title = ?, author = ? WHERE id = ?", (title, author, book_id))
        conn.commit()
    if cursor.rowcount == 0:
        return jsonify({"error": "Book not found"}), 404
    with get_db_connection() as conn:
        book = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        conn.commit()
    return jsonify({"message": f"Book {book_id} updated", "book": {"id": book_id, "author": book['author'], "title": book['title'], "read": bool(book['read'])}})

# delete using DELETE
@app.route("/books/<int:book_id>", methods=["DELETE"])
def delete_book_delete(book_id):
    with get_db_connection() as conn:
        cursor = conn.execute("DELETE FROM books where id = ?", (book_id,))
        conn.commit()
    if cursor.rowcount == 0:
        return jsonify({"error": "Book not found"}), 404
    return jsonify({"message": f"Book {book_id} deleted"})

# mark book as read
@app.route("/books/<int:book_id>", methods=["PATCH"])
def toggle_book_read(book_id):
    read = request.form.get("read")
    if read not in ["true", "false"]:
        return jsonify({"error": "Invalid read status"}), 400
    with get_db_connection() as conn:
        cursor = conn.execute("UPDATE books SET read = ? where id = ?", (read, book_id))
        conn.commit()
    if cursor.rowcount == 0:
        return jsonify({"error": "Book not found"}), 404
    return jsonify({"message": f"Book {book_id} status updated", "read": bool(read)})


if __name__ == "__main__":
    app.run(debug=True)
