# ✅ AI Broadcast System - Testing Guide

## System Status
- **Backend**: ✅ Running on port 8000
- **Frontend**: ✅ Running on port 5174  
- **Function Added**: ✅ `sendBroadcastMessage`
- **RBAC**: ✅ Configured (managers and HR only)
- **Quick Action**: ✅ Added to AICommandCenter

## How to Test

### Step 1: Open the Application
Navigate to: **http://localhost:5174/**

### Step 2: Open AI Assistant
Click the **purple sparkle button** (🤖) in the header to open AICommandCenter

### Step 3: Try These Commands

#### Test 1: Simple Broadcast to All Managers
```
send this message to all managers: Hi team, please check your tasks
```

**Expected Result:**
```
✅ Broadcast sent to X recipient(s) (all managers)

Details:
- Sender: Your Name
- Message: "Hi team, please check your tasks"
- Recipients: X managers
- Sent at: 2025-11-11T...
- Priority: medium
```

#### Test 2: Broadcast to All Employees
```
send a message to all employees: Office will be closed tomorrow
```

**Expected Result:**
```
✅ Broadcast sent to X recipient(s) (all employees)
```

#### Test 3: Quick Action Button
1. Click the **"Send Broadcast"** quick action button (pink, 📢 icon)
2. The command will auto-fill: `send a message to all managers: "Hi"`
3. Edit the message as needed
4. Press **Send**

#### Test 4: Urgent Priority
```
send urgent message to all managers: Critical system update at 5pm today
```

**Expected Result:**
- Priority should be detected as "urgent"
- Message sent with high priority flag

#### Test 5: Custom Recipients (if you know employee IDs)
```
send a message to employees 1 and 2: Please submit your timesheets
```

#### Test 6: Check Permissions (as Employee)
If you're logged in as a regular employee (not manager/HR):
```
send a message to all employees: Test
```

**Expected Result:**
```
❌ You don't have permission to perform this action. Required role: Manager
```

### Step 4: Verify Notifications Were Sent

#### Option A: Check Database
```sql
SELECT * FROM notifications 
WHERE notification_type = 'broadcast' 
ORDER BY created_at DESC 
LIMIT 10;
```

#### Option B: Check Notification Inbox (if implemented)
- Navigate to notifications icon in the app
- Recipients should see the broadcast message

#### Option C: Backend Logs
Check the terminal running the backend for:
```
INFO: POST /api/chatbot/chat
INFO: Function called: sendBroadcastMessage
```

## Expected Function Call Structure

When you send a broadcast command, the AI should call:

```json
{
  "function_name": "sendBroadcastMessage",
  "arguments": {
    "message": "Hi team, please check your tasks",
    "recipientType": "all_managers",
    "priority": "medium"
  }
}
```

## Troubleshooting

### Issue: "AI service is not configured"
**Solution**: Check backend logs for OpenAI API key errors. Ensure `AZURE_OPENAI_KEY` or `OPENAI_API_KEY` is set in environment variables.

### Issue: "You don't have permission"
**Solution**: You need to be logged in as a Manager or HR Admin. Employees cannot send broadcasts.

### Issue: "No recipients found"
**Possible Causes**:
- No managers in database (for "all_managers")
- No active employees (for "all_employees")
- Team IDs don't exist (for "specific_teams")

**Solution**: Check database for active employees with `is_active = true`.

### Issue: Function not called
**Symptoms**: AI responds with generic message instead of calling the function

**Solution**: 
1. Verify backend restarted successfully (check terminal)
2. Check `ai_chatbot.py` has `sendBroadcastMessage` in function definitions
3. Try a more explicit command: "call sendBroadcastMessage function to send message to all managers: Hi"

## Advanced Testing

### Test Natural Language Variations
Try different phrasings to test AI understanding:
- "broadcast to all managers: Meeting at 3pm"
- "send announcement to everyone: New policy"
- "message all team leads: Review pending tasks"
- "tell all employees: Fire drill tomorrow"

### Test Scheduled Broadcasts (Not Yet Implemented)
```
schedule a broadcast for tomorrow at 9am to all employees: Office closed Friday
```

**Expected**: Should return "scheduled" status (actual sending not implemented yet)

### Test Template Detection
```
send a weekly review reminder to all managers
```

**Expected**: AI should detect "weekly review" and potentially apply template

## Checking Conversation History

All broadcast commands are logged in the database:

```sql
SELECT 
    ch.message_text,
    ch.intent,
    ch.function_called,
    ch.action_status,
    ch.created_at
FROM conversation_history ch
WHERE ch.intent = 'send_broadcast'
ORDER BY ch.created_at DESC
LIMIT 10;
```

## Success Indicators

✅ **Backend Function Registered**: Check startup logs for no errors loading `ai_chatbot.py`

✅ **AI Understands Command**: Response mentions "broadcast" or "sent to X recipients"

✅ **Function Called**: Look for `"function_called": "sendBroadcastMessage"` in response

✅ **Notifications Created**: Database `notifications` table has new entries with `notification_type = 'broadcast'`

✅ **RBAC Enforced**: Employees get permission error, managers succeed

✅ **Recipients Filtered**: Correct number of recipients based on type (all_managers vs all_employees)

## Quick Verification Script

Run this in the backend terminal to test the function directly:

```python
# Test broadcast function
from app.services.ai_chatbot import HRChatbotService
from app.models.user import User
from app.database import get_async_session

# Simulate manager user
user = User(id=1, role="manager")

# Call function
result = await service._handle_send_broadcast_message({
    "message": "Test broadcast",
    "recipientType": "all_managers",
    "priority": "medium"
}, user)

print(result)
# Expected: {"success": True, "notifications_sent": X, ...}
```

## Documentation Reference

Full implementation details: See `AI_BROADCAST_INTEGRATION.md`

---

**Testing Date**: November 11, 2025  
**Status**: Ready for Testing  
**Expected Duration**: 5-10 minutes  
**Difficulty**: Easy - Just type natural language commands!

## Example Test Session

```
User Opens AI Assistant
↓
Clicks "Send Broadcast" Quick Action
↓
Types: "send this message to all managers: Please review Q3 reports"
↓
Presses Send
↓
AI Processes (2-3 seconds)
↓
Responds: "✅ Broadcast sent to 12 recipient(s) (all managers)"
↓
User Verifies: Checks notifications or database
↓
✅ Test Complete!
```

Start testing now! 🚀
