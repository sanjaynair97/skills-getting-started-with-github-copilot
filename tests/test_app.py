"""
Tests for the Mergington High School Activities API
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Provide a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities before each test to ensure test isolation"""
    # Store original state
    original_activities = {
        "Basketball": {
            "description": "Play basketball and develop athletic skills",
            "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
            "max_participants": 15,
            "participants": ["alex@mergington.edu"]
        },
        "Soccer": {
            "description": "Competitive soccer training and matches",
            "schedule": "Tuesdays and Thursdays, 3:30 PM - 5:00 PM",
            "max_participants": 22,
            "participants": ["jordan@mergington.edu"]
        },
    }
    
    # Clear and reset
    activities.clear()
    activities.update(original_activities)
    
    yield
    
    # Cleanup after test
    activities.clear()
    activities.update(original_activities)


class TestGetActivities:
    def test_get_activities_returns_list(self, client):
        """Test that GET /activities returns all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert "Basketball" in data
        assert "Soccer" in data
        assert data["Basketball"]["description"] == "Play basketball and develop athletic skills"
    
    def test_activity_has_required_fields(self, client):
        """Test that each activity has required fields"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity in data.items():
            assert "description" in activity
            assert "schedule" in activity
            assert "max_participants" in activity
            assert "participants" in activity


class TestSignupForActivity:
    def test_signup_for_activity_success(self, client):
        """Test successful signup for an activity"""
        response = client.post("/activities/Basketball/signup", params={"email": "test@mergington.edu"})
        assert response.status_code == 200
        data = response.json()
        assert "Signed up" in data["message"]
        assert "test@mergington.edu" in activities["Basketball"]["participants"]
    
    def test_signup_for_nonexistent_activity(self, client):
        """Test signup for an activity that doesn't exist"""
        response = client.post("/activities/NonExistent/signup", params={"email": "test@mergington.edu"})
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]
    
    def test_signup_duplicate_student(self, client):
        """Test that a student cannot sign up twice for the same activity"""
        # First signup
        response1 = client.post("/activities/Basketball/signup", params={"email": "duplicate@mergington.edu"})
        assert response1.status_code == 200
        
        # Second signup with same email
        response2 = client.post("/activities/Basketball/signup", params={"email": "duplicate@mergington.edu"})
        assert response2.status_code == 400
        data = response2.json()
        assert "already signed up" in data["detail"].lower()
    
    def test_signup_multiple_students(self, client):
        """Test multiple different students can sign up"""
        response1 = client.post("/activities/Soccer/signup", params={"email": "student1@mergington.edu"})
        assert response1.status_code == 200
        
        response2 = client.post("/activities/Soccer/signup", params={"email": "student2@mergington.edu"})
        assert response2.status_code == 200
        
        # Verify both are in participants
        response = client.get("/activities")
        soccer = response.json()["Soccer"]
        assert "student1@mergington.edu" in soccer["participants"]
        assert "student2@mergington.edu" in soccer["participants"]


class TestUnregisterFromActivity:
    def test_unregister_success(self, client):
        """Test successful unregistration from an activity"""
        # First signup
        client.post("/activities/Basketball/signup", params={"email": "remove@mergington.edu"})
        
        # Then unregister
        response = client.delete("/activities/Basketball/unregister", params={"email": "remove@mergington.edu"})
        assert response.status_code == 200
        data = response.json()
        assert "Unregistered" in data["message"]
        assert "remove@mergington.edu" not in activities["Basketball"]["participants"]
    
    def test_unregister_nonexistent_activity(self, client):
        """Test unregistration from an activity that doesn't exist"""
        response = client.delete("/activities/NonExistent/unregister", params={"email": "test@mergington.edu"})
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]
    
    def test_unregister_not_signed_up(self, client):
        """Test unregistration when student is not signed up"""
        response = client.delete("/activities/Soccer/unregister", params={"email": "notregistered@mergington.edu"})
        assert response.status_code == 400
        data = response.json()
        assert "not signed up" in data["detail"].lower()
    
    def test_unregister_existing_participant(self, client):
        """Test unregistering a participant who is actually registered"""
        # alex@mergington.edu is in Basketball participants
        response = client.delete("/activities/Basketball/unregister", params={"email": "alex@mergington.edu"})
        assert response.status_code == 200
        assert "alex@mergington.edu" not in activities["Basketball"]["participants"]


class TestIntegration:
    def test_signup_and_unregister_flow(self, client):
        """Test the complete flow of signing up and unregistering"""
        email = "flow@mergington.edu"
        activity = "Basketball"
        
        # Check initial state
        response = client.get("/activities")
        initial_count = len(response.json()[activity]["participants"])
        
        # Sign up
        response = client.post(f"/activities/{activity}/signup", params={"email": email})
        assert response.status_code == 200
        
        # Verify participant was added
        response = client.get("/activities")
        assert email in response.json()[activity]["participants"]
        assert len(response.json()[activity]["participants"]) == initial_count + 1
        
        # Unregister
        response = client.delete(f"/activities/{activity}/unregister", params={"email": email})
        assert response.status_code == 200
        
        # Verify participant was removed
        response = client.get("/activities")
        assert email not in response.json()[activity]["participants"]
        assert len(response.json()[activity]["participants"]) == initial_count
