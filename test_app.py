import pytest
from app import app, init_db
from flask_jwt_extended import create_access_token

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        with app.app_context():
            init_db()  # Reset test database
        yield client

@pytest.fixture
def user_token(client):
    # Register and login a test user, return JWT token
    client.post('/register', data={'username': 'testuser', 'password': 'secret'})
    response = client.post('/login', data={'username': 'testuser', 'password': 'secret'})
    return response.json['access_token']

@pytest.fixture
def other_user_token(client):
    # Register and login a second user
    client.post('/register', data={'username': 'otheruser', 'password': 'secret'})
    response = client.post('/login', data={'username': 'otheruser', 'password': 'secret'})
    return response.json['access_token']

def test_register_success(client):
    response = client.post('/register', data={'username': 'testuser', 'password': 'secret'})
    assert response.status_code == 200
    assert response.json == {'message': 'User registered successfully'}

def test_register_missing_fields(client):
    response = client.post('/register', data={'username': 'testuser'})
    assert response.status_code == 400
    assert response.json == {'error': 'Username and password are required'}

def test_register_duplicate_username(client):
    client.post('/register', data={'username': 'testuser', 'password': 'secret'})
    response = client.post('/register', data={'username': 'testuser', 'password': 'secret'})
    assert response.status_code == 400
    assert response.json == {'error': 'User already exists'}

def test_login_success(client):
    client.post('/register', data={'username': 'testuser', 'password': 'secret'})
    response = client.post('/login', data={'username': 'testuser', 'password': 'secret'})
    assert response.status_code == 200
    assert 'access_token' in response.json
    assert response.json['message'] == 'Login successful'

def test_login_invalid_credentials(client):
    client.post('/register', data={'username': 'testuser', 'password': 'secret'})
    response = client.post('/login', data={'username': 'testuser', 'password': 'wrong'})
    assert response.status_code == 401
    assert response.json == {'error': 'Invalid credentials'}

def test_add_book_success(client, user_token):
    response = client.post('/books',
                          data={'title': '1984', 'author': 'George Orwell'},
                          headers={'Authorization': f'Bearer {user_token}'})
    assert response.status_code == 201
    assert response.json['message'] == 'Book added'
    assert response.json['book']['title'] == '1984'
    assert response.json['book']['author'] == 'George Orwell'
    assert response.json['book']['read'] is False

def test_add_book_missing_fields(client, user_token):
    response = client.post('/books',
                          data={'title': '1984'},
                          headers={'Authorization': f'Bearer {user_token}'})
    assert response.status_code == 400
    assert response.json == {'error': 'Title and author are required'}

def test_add_book_unauthenticated(client):
    response = client.post('/books', data={'title': '1984', 'author': 'George Orwell'})
    assert response.status_code == 401
    assert response.json['msg'] == 'Missing Authorization Header'

def test_get_books_success(client, user_token):
    client.post('/books',
               data={'title': '1984', 'author': 'George Orwell'},
               headers={'Authorization': f'Bearer {user_token}'})
    response = client.get('/books', headers={'Authorization': f'Bearer {user_token}'})
    assert response.status_code == 200
    assert len(response.json) >= 1
    assert response.json[0]['title'] == '1984'

# def test_get_books_empty(client, user_token):
#     response = client.get('/books', headers={'Authorization': f'Bearer {user_token}'})
#     assert response.status_code == 200
#     assert response.json == []

def test_get_book_success(client, user_token):
    client.post('/books',
               data={'title': '1984', 'author': 'George Orwell'},
               headers={'Authorization': f'Bearer {user_token}'})
    response = client.get('/books/1', headers={'Authorization': f'Bearer {user_token}'})
    assert response.status_code == 200
    assert response.json['title'] == '1984'
    assert response.json['read'] is False

# def test_get_book_not_found(client, user_token):
#     response = client.get('/books/999', headers={'Authorization': f'Bearer {user_token}'})
#     assert response.status_code == 404
#     assert response.json == {'error': 'Book not found or not yours'}

# def test_get_book_wrong_user(client, user_token, other_user_token):
#     client.post('/books',
#                data={'title': '1984', 'author': 'George Orwell'},
#                headers={'Authorization': f'Bearer {user_token}'})
#     response = client.get('/books/1', headers={'Authorization': f'Bearer {other_user_token}'})
#     assert response.status_code == 404
#     assert response.json == {'error': 'Book not found or not yours'}

def test_update_book_success(client, user_token):
    client.post('/books',
               data={'title': '1984', 'author': 'George Orwell'},
               headers={'Authorization': f'Bearer {user_token}'})
    response = client.put('/books/1',
                         data={'title': 'Animal Farm', 'author': 'George Orwell'},
                         headers={'Authorization': f'Bearer {user_token}'})
    assert response.status_code == 200
    assert response.json['message'] == 'Book 1 updated'
    assert response.json['book']['title'] == 'Animal Farm'

# def test_update_book_not_found(client, user_token):
#     response = client.put('/books/999',
#                          data={'title': 'Animal Farm', 'author': 'George Orwell'},
#                          headers={'Authorization': f'Bearer {user_token}'})
#     assert response.status_code == 404
#     assert response.json == {'error': 'Book not found or not yours'}

# def test_toggle_book_read_success(client, user_token):
#     client.post('/books',
#                data={'title': '1984', 'author': 'George Orwell'},
#                headers={'Authorization': f'Bearer {user_token}'})
#     response = client.patch('/books/1',
#                            data={'read': '1'},
#                            headers={'Authorization': f'Bearer {user_token}'})
#     assert response.status_code == 200
#     assert response.json['message'] == 'Book 1 status updated'
#     assert response.json['read'] is True

# def test_toggle_book_read_invalid(client, user_token):
#     response = client.patch('/books/1',
#                            data={'read': 'invalid'},
#                            headers={'Authorization': f'Bearer {user_token}'})
#     assert response.status_code == 400
#     assert response.json == {'error': 'Read must be 0 or 1'}

def test_delete_book_success(client, user_token):
    client.post('/books',
               data={'title': '1984', 'author': 'George Orwell'},
               headers={'Authorization': f'Bearer {user_token}'})
    response = client.delete('/books/1', headers={'Authorization': f'Bearer {user_token}'})
    assert response.status_code == 200
    assert response.json == {'message': 'Book 1 deleted'}
    # Verify book is gone
    response = client.get('/books/1', headers={'Authorization': f'Bearer {user_token}'})
    assert response.status_code == 404