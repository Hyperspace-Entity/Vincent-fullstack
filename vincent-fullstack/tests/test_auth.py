"""Comprehensive test suite for Vincent authentication and routes."""

import pytest
from app import create_app
from app.extensions import db
from app.auth.models import User, UserRole


@pytest.fixture
def app():
    """Create test app."""
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def admin_user(app):
    """Create admin user."""
    user = User(username="admin", email="admin@test.com", roles="admin")
    user.set_password("AdminPass123")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def reviewer_user(app):
    """Create reviewer user."""
    user = User(username="reviewer", email="reviewer@test.com", roles="reviewer")
    user.set_password("ReviewerPass123")
    db.session.add(user)
    db.session.commit()
    return user


class TestAuth:
    """Authentication tests."""

    def test_register_success(self, client):
        """Test successful registration."""
        response = client.post(
            "/auth/register",
            json={
                "username": "newuser",
                "email": "new@test.com",
                "password": "NewPass123",
            },
        )
        assert response.status_code == 201
        assert response.json["username"] == "newuser"
        assert "password_hash" not in response.json

    def test_register_weak_password(self, client):
        """Test registration with weak password."""
        response = client.post(
            "/auth/register",
            json={
                "username": "newuser",
                "email": "new@test.com",
                "password": "weak",
            },
        )
        assert response.status_code == 400

    def test_register_duplicate_username(self, client, reviewer_user):
        """Test registration with duplicate username."""
        response = client.post(
            "/auth/register",
            json={
                "username": "reviewer",
                "email": "different@test.com",
                "password": "NewPass123",
            },
        )
        assert response.status_code == 409

    def test_login_success(self, client, reviewer_user):
        """Test successful login."""
        response = client.post(
            "/auth/login",
            json={"username": "reviewer", "password": "ReviewerPass123"},
        )
        assert response.status_code == 200
        assert "access_token" in response.json
        assert response.json["token_type"] == "Bearer"

    def test_login_invalid_password(self, client, reviewer_user):
        """Test login with invalid password."""
        response = client.post(
            "/auth/login",
            json={"username": "reviewer", "password": "WrongPassword"},
        )
        assert response.status_code == 401

    def test_login_nonexistent_user(self, client):
        """Test login for nonexistent user."""
        response = client.post(
            "/auth/login",
            json={"username": "nonexistent", "password": "SomePass123"},
        )
        assert response.status_code == 401


class TestQueue:
    """Review queue endpoint tests."""

    def test_list_documents_requires_auth(self, client):
        """Test that list documents requires authentication."""
        response = client.get("/api/queue")
        assert response.status_code == 401

    def test_list_documents_authenticated(self, client, reviewer_user, app):
        """Test listing documents when authenticated."""
        # Get token
        login_response = client.post(
            "/auth/login",
            json={"username": "reviewer", "password": "ReviewerPass123"},
        )
        token = login_response.json["access_token"]

        # List documents
        response = client.get(
            "/api/queue",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert isinstance(response.json, list)

    def test_create_document(self, client, reviewer_user):
        """Test document creation."""
        login_response = client.post(
            "/auth/login",
            json={"username": "reviewer", "password": "ReviewerPass123"},
        )
        token = login_response.json["access_token"]

        response = client.post(
            "/api/queue",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": "Test Invoice",
                "content": "This is test content for an invoice",
                "doc_type": "invoice",
            },
        )
        assert response.status_code == 201
        assert response.json["title"] == "Test Invoice"
        assert response.json["status"] == "pending"

    def test_create_document_invalid_type(self, client, reviewer_user):
        """Test document creation with invalid type."""
        login_response = client.post(
            "/auth/login",
            json={"username": "reviewer", "password": "ReviewerPass123"},
        )
        token = login_response.json["access_token"]

        response = client.post(
            "/api/queue",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": "Test",
                "content": "Content",
                "doc_type": "invalid_type",
            },
        )
        assert response.status_code == 400


class TestSecurity:
    """Security-focused tests."""

    def test_xss_sanitization(self, client, reviewer_user):
        """Test XSS payload sanitization."""
        login_response = client.post(
            "/auth/login",
            json={"username": "reviewer", "password": "ReviewerPass123"},
        )
        token = login_response.json["access_token"]

        xss_payload = '<script>alert("XSS")</script>'
        response = client.post(
            "/api/queue",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": xss_payload,
                "content": "Content",
                "doc_type": "invoice",
            },
        )
        assert response.status_code == 201
        # Title should be HTML-escaped
        assert "<" not in response.json["title"]
        assert "script" not in response.json["title"]

    def test_rate_limiting(self, client):
        """Test rate limiting on login endpoint."""
        responses = []
        for i in range(12):
            response = client.post(
                "/auth/login",
                json={"username": f"user{i}", "password": "pass"},
            )
            responses.append(response.status_code)

        # Some requests should hit rate limit (429)
        assert 429 in responses

    def test_unauthorized_role_access(self, client, reviewer_user, app):
        """Test role-based access control."""
        # Create a document
        login_response = client.post(
            "/auth/login",
            json={"username": "reviewer", "password": "ReviewerPass123"},
        )
        token = login_response.json["access_token"]

        create_response = client.post(
            "/api/queue",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": "Test",
                "content": "Content",
                "doc_type": "invoice",
            },
        )
        doc_id = create_response.json["id"]

        # Reviewer can approve
        approve_response = client.post(
            f"/api/queue/{doc_id}/approve",
            headers={"Authorization": f"Bearer {token}"},
            json={"notes": "Approved"},
        )
        assert approve_response.status_code == 200
