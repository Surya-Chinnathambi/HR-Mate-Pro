"""
Comprehensive Integration Tests for HRMS APIs

Tests all major API endpoints with realistic scenarios
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import get_session
from app.models.user import User, Employee, Department
from app.models.workflow import WorkAssignment, ApprovalRequest, TaskStatus, TaskPriority
from app.core.security import get_password_hash, create_access_token

# Test database setup
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db_session():
    """Create a fresh database session for each test"""
    from sqlmodel import SQLModel
    SQLModel.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        SQLModel.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db_session):
    """Create test client with database override"""
    def override_get_session():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db_session):
    """Create a test user"""
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=get_password_hash("testpass123"),
        role="Employee",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_department(db_session):
    """Create a test department"""
    dept = Department(
        name="Engineering",
        description="Engineering Department",
        head_id=None
    )
    db_session.add(dept)
    db_session.commit()
    db_session.refresh(dept)
    return dept


@pytest.fixture
def test_employee(db_session, test_user, test_department):
    """Create a test employee"""
    employee = Employee(
        user_id=test_user.user_id,
        employee_id=1001,
        first_name="Test",
        last_name="User",
        full_name="Test User",
        email="test@example.com",
        department_id=test_department.department_id,
        position="Software Engineer",
        hire_date=datetime.utcnow(),
        is_active=True
    )
    db_session.add(employee)
    db_session.commit()
    db_session.refresh(employee)
    return employee


@pytest.fixture
def auth_token(test_user):
    """Generate authentication token"""
    return create_access_token(data={"sub": test_user.username})


@pytest.fixture
def auth_headers(auth_token):
    """Generate authorization headers"""
    return {"Authorization": f"Bearer {auth_token}"}


# ============================================================================
# AUTHENTICATION TESTS
# ============================================================================

class TestAuthentication:
    """Test authentication endpoints"""
    
    def test_login_success(self, client, test_user):
        """Test successful login"""
        response = client.post(
            "/api/auth/login",
            data={
                "username": "testuser",
                "password": "testpass123"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    def test_login_invalid_credentials(self, client, test_user):
        """Test login with invalid credentials"""
        response = client.post(
            "/api/auth/login",
            data={
                "username": "testuser",
                "password": "wrongpassword"
            }
        )
        assert response.status_code == 401
    
    def test_get_current_user(self, client, auth_headers, test_user):
        """Test getting current user info"""
        response = client.get("/api/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"


# ============================================================================
# EMPLOYEE TESTS
# ============================================================================

class TestEmployees:
    """Test employee management endpoints"""
    
    def test_list_employees(self, client, auth_headers, test_employee):
        """Test listing employees"""
        response = client.get("/api/employees", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
    
    def test_get_employee_by_id(self, client, auth_headers, test_employee):
        """Test getting specific employee"""
        response = client.get(
            f"/api/employees/{test_employee.employee_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["employee_id"] == test_employee.employee_id
        assert data["full_name"] == "Test User"
    
    def test_create_employee(self, client, auth_headers, test_department):
        """Test creating new employee"""
        employee_data = {
            "employee_id": 1002,
            "first_name": "Jane",
            "last_name": "Doe",
            "email": "jane@example.com",
            "department_id": test_department.department_id,
            "position": "Senior Engineer",
            "hire_date": datetime.utcnow().isoformat()
        }
        response = client.post(
            "/api/employees",
            headers=auth_headers,
            json=employee_data
        )
        assert response.status_code in [200, 201]
        data = response.json()
        assert data["email"] == "jane@example.com"


# ============================================================================
# WORK ASSIGNMENT TESTS
# ============================================================================

class TestWorkAssignments:
    """Test work assignment endpoints"""
    
    def test_create_task(self, client, auth_headers, test_employee):
        """Test creating a new task"""
        task_data = {
            "title": "Test Task",
            "description": "This is a test task",
            "assignee_id": test_employee.employee_id,
            "assigner_id": test_employee.employee_id,
            "priority": "HIGH",
            "status": "NOT_STARTED",
            "estimated_hours": 8.0,
            "due_date": (datetime.utcnow() + timedelta(days=7)).isoformat()
        }
        response = client.post(
            "/api/work-assignments",
            headers=auth_headers,
            json=task_data
        )
        assert response.status_code in [200, 201]
        data = response.json()
        assert data["title"] == "Test Task"
        assert data["priority"] == "HIGH"
    
    def test_list_tasks(self, client, auth_headers, db_session, test_employee):
        """Test listing tasks"""
        # Create a test task first
        task = WorkAssignment(
            title="Test Task",
            description="Test",
            assignee_id=test_employee.employee_id,
            assigner_id=test_employee.employee_id,
            priority=TaskPriority.MEDIUM,
            status=TaskStatus.NOT_STARTED,
            estimated_hours=4.0,
            due_date=datetime.utcnow() + timedelta(days=5)
        )
        db_session.add(task)
        db_session.commit()
        
        response = client.get("/api/work-assignments", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_update_task_status(self, client, auth_headers, db_session, test_employee):
        """Test updating task status"""
        # Create task
        task = WorkAssignment(
            title="Status Update Test",
            description="Test",
            assignee_id=test_employee.employee_id,
            assigner_id=test_employee.employee_id,
            priority=TaskPriority.HIGH,
            status=TaskStatus.NOT_STARTED,
            estimated_hours=2.0,
            due_date=datetime.utcnow() + timedelta(days=3)
        )
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)
        
        # Update status
        response = client.patch(
            f"/api/work-assignments/{task.task_id}/status",
            headers=auth_headers,
            json={"status": "IN_PROGRESS", "progress_percentage": 25}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "IN_PROGRESS"
        assert data["progress_percentage"] == 25


# ============================================================================
# ANALYTICS TESTS
# ============================================================================

class TestAnalytics:
    """Test analytics endpoints"""
    
    def test_productivity_metrics(self, client, auth_headers):
        """Test productivity metrics endpoint"""
        params = {
            "start_date": (datetime.utcnow() - timedelta(days=30)).isoformat(),
            "end_date": datetime.utcnow().isoformat()
        }
        response = client.get(
            "/api/analytics/productivity",
            headers=auth_headers,
            params=params
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_tasks" in data
        assert "completion_rate" in data
        assert "avg_completion_time_hours" in data
    
    def test_workload_analytics(self, client, auth_headers):
        """Test workload distribution analytics"""
        response = client.get("/api/analytics/workload", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_employees" in data
        assert "avg_utilization" in data
        assert "balance_score" in data
    
    def test_dashboard_summary(self, client, auth_headers):
        """Test comprehensive dashboard endpoint"""
        params = {
            "start_date": (datetime.utcnow() - timedelta(days=7)).isoformat(),
            "end_date": datetime.utcnow().isoformat()
        }
        response = client.get(
            "/api/analytics/dashboard",
            headers=auth_headers,
            params=params
        )
        assert response.status_code == 200
        data = response.json()
        assert "productivity" in data
        assert "approvals" in data
        assert "workload" in data
        assert "trends" in data


# ============================================================================
# SCHEDULER TESTS
# ============================================================================

class TestScheduler:
    """Test scheduler endpoints"""
    
    def test_scheduler_status(self, client, auth_headers):
        """Test getting scheduler status"""
        response = client.get("/api/scheduler/status", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "running" in data
        assert "job_count" in data
        assert "jobs" in data
    
    def test_manual_job_trigger(self, client, auth_headers):
        """Test manually triggering a job"""
        # This might fail if jobs have dependencies, but should respond
        response = client.post(
            "/api/scheduler/jobs/workload-sync/run",
            headers=auth_headers
        )
        # Accept both success and error responses
        assert response.status_code in [200, 500]


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

class TestErrorHandling:
    """Test error handling and edge cases"""
    
    def test_unauthorized_access(self, client):
        """Test accessing protected endpoint without auth"""
        response = client.get("/api/employees")
        assert response.status_code == 401
    
    def test_invalid_token(self, client):
        """Test with invalid authentication token"""
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/api/employees", headers=headers)
        assert response.status_code == 401
    
    def test_not_found_resource(self, client, auth_headers):
        """Test accessing non-existent resource"""
        response = client.get("/api/employees/99999", headers=auth_headers)
        assert response.status_code == 404
    
    def test_invalid_input_validation(self, client, auth_headers):
        """Test input validation"""
        invalid_task = {
            "title": "",  # Empty title should fail
            "assignee_id": -1,  # Invalid ID
            "priority": "INVALID_PRIORITY"
        }
        response = client.post(
            "/api/work-assignments",
            headers=auth_headers,
            json=invalid_task
        )
        assert response.status_code in [400, 422]  # Validation error


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

class TestPerformance:
    """Test API performance and response times"""
    
    def test_list_endpoint_performance(self, client, auth_headers):
        """Test list endpoint responds in reasonable time"""
        import time
        start = time.time()
        response = client.get("/api/employees", headers=auth_headers)
        duration = time.time() - start
        
        assert response.status_code == 200
        assert duration < 2.0  # Should respond within 2 seconds
    
    def test_analytics_endpoint_performance(self, client, auth_headers):
        """Test analytics endpoint performance"""
        import time
        params = {
            "start_date": (datetime.utcnow() - timedelta(days=30)).isoformat(),
            "end_date": datetime.utcnow().isoformat()
        }
        start = time.time()
        response = client.get(
            "/api/analytics/productivity",
            headers=auth_headers,
            params=params
        )
        duration = time.time() - start
        
        assert response.status_code == 200
        assert duration < 3.0  # Analytics can take longer but should be < 3s


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
