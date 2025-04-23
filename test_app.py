import pytest
from app import app, init_db

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        with app.app_context():
            init_db()
        yield client


def test_register_success(client):
    response = client.post('/register', data={'username': 'testuser', 'password': 'secret'})
    assert response.status_code == 200
    assert response.json == {'message': 'User registered successfully'}

def test_register_missing_fields(client):
    response = client.post('/register', data={'username': 'testuser'})
    assert response.status_code == 400
    assert response.json == {'error': 'Username and password are required'}

def test_register_duplicate_username(client):
    response = client.post('/register', data={'username': 'testuser', 'password': 'secret'})
    assert response.status_code == 400
    assert response.json == {'error': 'User already exists'}

def test_login_success(client):
    client.post('/register', data={'username': 'testuser', 'password': 'secret'})
    response = client.post('/login', data={'username': 'testuser', 'password': 'secret'})
    assert response.status_code == 200
    assert "access_token" in response.json
    assert response.json['message'] == 'Login successful'

def test_login_invalid_credentials(client):
    client.post('/register', data={'username': 'testuser', 'password': 'secret'})
    response = client.post('/login', data={'username': 'testuser', 'password': 'wrong'})
    assert response.status_code == 401
    assert response.json == {'error': 'Invalid credentials'}
