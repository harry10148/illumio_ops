import pytest
import os
import json
import tempfile
from src.config import ConfigManager
from src.gui import _create_app, _hash_password

@pytest.fixture
def temp_config_file():
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    
    # Init empty config
    with open(path, 'w') as f:
        json.dump({"api": {"url": "test", "key": "test", "secret": "test", "org_id": "1"}, "rules": []}, f)
        
    yield path
    os.unlink(path)

@pytest.fixture
def app_persistent(temp_config_file):
    # Override ConfigManager path for testing
    cm = ConfigManager()
    cm.CONFIG_FILE = temp_config_file
    cm.load()
    
    # Setup test credentials
    salt = "testsalt"
    pass_hash = _hash_password(salt, "testpass")
    
    cm.config["web_gui"] = {
        "username": "admin",
        "password_salt": salt,
        "password_hash": pass_hash,
        "allowed_ips": ["127.0.0.1", "192.168.1.0/24"],
        "secret_key": "test-secret"
    }
    cm.save()
    
    app = _create_app(cm, persistent_mode=True)
    app.config.update({
        "TESTING": True,
    })
    
    yield app

@pytest.fixture
def client(app_persistent):
    return app_persistent.test_client()

def test_redirect_unauthenticated(client):
    response = client.get('/')
    assert response.status_code == 302
    assert response.location.endswith('/login')

def test_login_success(client):
    response = client.post('/api/login', json={
        "username": "admin",
        "password": "testpass"
    })
    assert response.status_code == 200
    assert response.json.get("ok") is True
    
    # Should now be able to access root
    response = client.get('/')
    assert response.status_code == 200

def test_login_fail(client):
    response = client.post('/api/login', json={
        "username": "admin",
        "password": "wrongpassword"
    })
    assert response.status_code == 401
    assert response.json.get("ok") is False

def test_ip_whitelist(app_persistent):
    client = app_persistent.test_client()
    
    # Mock remote_addr by directly calling request context
    with app_persistent.test_request_context('/', environ_base={'REMOTE_ADDR': '10.0.0.1'}):
        app_persistent.preprocess_request()
        # Should be forbidden
        from flask import request
        response = app_persistent.full_dispatch_request()
        assert response.status_code == 403

    # Should allow 127.0.0.1 (in whitelist)
    with app_persistent.test_request_context('/', environ_base={'REMOTE_ADDR': '127.0.0.1'}):
        response = app_persistent.full_dispatch_request()
        # Returns 302 because unauthenticated, but NOT 403
        assert response.status_code == 302

    # Should allow CIDR 192.168.1.50
    with app_persistent.test_request_context('/', environ_base={'REMOTE_ADDR': '192.168.1.50'}):
        response = app_persistent.full_dispatch_request()
        assert response.status_code == 302

def test_api_security_endpoints(client):
    # Authenticate first
    client.post('/api/login', json={"username": "admin", "password": "testpass"})
    
    res = client.get('/api/security')
    assert res.status_code == 200
    assert res.json['username'] == 'admin'
    assert '127.0.0.1' in res.json['allowed_ips']
    
    # Update allowed IPs and password
    res = client.post('/api/security', json={
        "username": "admin2",
        "old_password": "testpass",
        "new_password": "newpass",
        "allowed_ips": ["10.0.0.0/8"]
    })
    assert res.status_code == 200
    assert res.json['ok'] is True
    
    # Re-login with new password
    client.get('/logout')
    res = client.post('/api/login', json={"username": "admin2", "password": "newpass"})
    assert res.status_code == 200
    assert res.json['ok'] is True
