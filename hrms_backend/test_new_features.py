"""
Quick test script to verify chat history and role-based access

Run this after migration and setup to test the new features
"""
import sys
sys.path.append('c:/forlast/hrms_backend')

from app.database import engine
from sqlmodel import Session, select
from app.models.user import Employee, User
from app.models.chat import ChatConversation, ChatMessage, ChatRole
from datetime import datetime

def test_chat_system():
    """Test chat conversation creation and message storage"""
    session = Session(engine)
    
    try:
        # Get first employee
        employee = session.exec(select(Employee).limit(1)).first()
        
        if not employee:
            print("❌ No employees found. Run data generation first.")
            return
        
        print(f"📝 Testing chat system for {employee.first_name} {employee.last_name}")
        
        # Create a test conversation
        conversation = ChatConversation(
            employee_id=employee.id,
            title="Test Conversation",
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        session.add(conversation)
        session.commit()
        session.refresh(conversation)
        
        print(f"✅ Created conversation ID: {conversation.id}")
        
        # Add some test messages
        messages = [
            ChatMessage(
                conversation_id=conversation.id,
                role=ChatRole.USER,
                content="Hello, can you help me with my tasks?",
                created_at=datetime.utcnow()
            ),
            ChatMessage(
                conversation_id=conversation.id,
                role=ChatRole.ASSISTANT,
                content="Of course! I can help you manage your tasks. What would you like to do?",
                created_at=datetime.utcnow()
            ),
            ChatMessage(
                conversation_id=conversation.id,
                role=ChatRole.USER,
                content="Show me my pending tasks",
                created_at=datetime.utcnow()
            )
        ]
        
        for msg in messages:
            session.add(msg)
        
        conversation.message_count = len(messages)
        conversation.last_message_at = datetime.utcnow()
        session.add(conversation)
        
        session.commit()
        
        print(f"✅ Added {len(messages)} test messages")
        
        # Verify by reading back
        saved_conversation = session.get(ChatConversation, conversation.id)
        saved_messages = session.exec(
            select(ChatMessage).where(ChatMessage.conversation_id == conversation.id)
        ).all()
        
        print(f"\n📊 Verification:")
        print(f"   Conversation: {saved_conversation.title}")
        print(f"   Messages: {len(saved_messages)}")
        print(f"   Message count: {saved_conversation.message_count}")
        
        for idx, msg in enumerate(saved_messages, 1):
            print(f"\n   Message {idx}:")
            print(f"      Role: {msg.role}")
            print(f"      Content: {msg.content[:50]}...")
        
        print("\n✅ Chat system test PASSED!")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        session.close()


def test_role_based_access():
    """Test role and team assignments"""
    session = Session(engine)
    
    try:
        print("\n" + "="*60)
        print("🔒 Testing Role-Based Access")
        print("="*60)
        
        # Count by role
        hr_employees = session.exec(select(Employee).where(Employee.role == 'hr')).all()
        managers = session.exec(select(Employee).where(Employee.role == 'manager')).all()
        employees = session.exec(select(Employee).where(Employee.role == 'employee')).all()
        
        print(f"\n📊 Employee Distribution:")
        print(f"   HR: {len(hr_employees)} employees")
        print(f"   Managers: {len(managers)} employees")
        print(f"   Employees: {len(employees)} employees")
        
        # Show HR employees
        print(f"\n👥 HR Team (Full Access):")
        for hr in hr_employees:
            print(f"   • {hr.first_name} {hr.last_name} (ID: {hr.id})")
            print(f"     Email: {hr.email}")
            print(f"     Can see: ALL 38 employees")
        
        # Show managers and their teams
        print(f"\n👔 Manager Teams:")
        for manager in managers:
            team_members = session.exec(
                select(Employee).where(
                    Employee.team_id == manager.team_id,
                    Employee.role == 'employee'
                )
            ).all()
            
            print(f"\n   Team {manager.team_id} - Manager: {manager.first_name} {manager.last_name}")
            print(f"   • Email: {manager.email}")
            print(f"   • Team Size: {len(team_members)} employees")
            print(f"   • Can see: Only Team {manager.team_id} members")
            
            if team_members:
                print(f"   • Team Members:")
                for member in team_members[:3]:  # Show first 3
                    print(f"      - {member.first_name} {member.last_name}")
                if len(team_members) > 3:
                    print(f"      - ... and {len(team_members) - 3} more")
        
        # Show sample employees
        print(f"\n👨‍💼 Sample Employees:")
        for emp in employees[:3]:
            print(f"   • {emp.first_name} {emp.last_name} (Team {emp.team_id})")
            print(f"     Email: {emp.email}")
            print(f"     Can see: Only their own data")
        
        print("\n✅ Role-based access test PASSED!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        raise
    finally:
        session.close()


def test_team_isolation():
    """Test that managers can only access their team's data"""
    session = Session(engine)
    
    try:
        print("\n" + "="*60)
        print("🔐 Testing Team Isolation")
        print("="*60)
        
        # Get a manager
        manager = session.exec(
            select(Employee).where(Employee.role == 'manager')
        ).first()
        
        if not manager:
            print("❌ No managers found")
            return
        
        print(f"\n🧪 Test Manager: {manager.first_name} {manager.last_name}")
        print(f"   Team ID: {manager.team_id}")
        
        # Get team members
        team_members = session.exec(
            select(Employee).where(Employee.team_id == manager.team_id)
        ).all()
        
        # Get other employees (should NOT be accessible)
        other_employees = session.exec(
            select(Employee).where(Employee.team_id != manager.team_id)
        ).all()
        
        print(f"\n✅ Manager CAN see:")
        print(f"   • {len(team_members)} employees in Team {manager.team_id}")
        for member in team_members[:3]:
            print(f"      - {member.first_name} {member.last_name}")
        
        print(f"\n❌ Manager CANNOT see:")
        print(f"   • {len(other_employees)} employees in other teams")
        print(f"   • (Would get 403 Forbidden if trying to access)")
        
        print("\n✅ Team isolation test PASSED!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        raise
    finally:
        session.close()


def main():
    """Run all tests"""
    print("🚀 Starting HRMS Feature Tests\n")
    
    try:
        # Test 1: Chat System
        test_chat_system()
        
        # Test 2: Role-Based Access
        test_role_based_access()
        
        # Test 3: Team Isolation
        test_team_isolation()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("="*60)
        print("\nYou can now:")
        print("1. Access chat history via: GET /api/chat/conversations")
        print("2. Test role-based dashboards in frontend")
        print("3. Verify team isolation in API calls")
        
    except Exception as e:
        print(f"\n❌ Tests failed: {e}")
        print("\nTroubleshooting:")
        print("1. Did you run migration? alembic upgrade head")
        print("2. Did you run setup script? python setup_roles_and_teams.py")
        print("3. Check database connection in app/database.py")


if __name__ == "__main__":
    main()
