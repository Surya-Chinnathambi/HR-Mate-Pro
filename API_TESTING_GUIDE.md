# API Testing Guide for HRMS System

## System Status
- **Backend**: http://localhost:8000
- **Frontend**: http://localhost:5174
- **API Docs**: http://localhost:8000/api/docs

## Quick Test Commands

### 1. Test Backend Health
```powershell
curl http://localhost:8000/health
```

### 2. Create Test Admin User
```powershell
$body = @{
    email = "admin@company.com"
    password = "Admin@123"
    role = "admin"
    status = "active"
} | ConvertTo-Json

curl -Method POST -Uri "http://localhost:8000/api/auth/register" `
    -Headers @{"Content-Type"="application/json"} `
    -Body $body
```

### 3. Login and Get Token
```powershell
$loginBody = @{
    username = "admin@company.com"
    password = "Admin@123"
} | ConvertTo-Json

$response = curl -Method POST -Uri "http://localhost:8000/api/auth/login" `
    -Headers @{"Content-Type"="application/x-www-form-urlencoded"} `
    -Body "username=admin@company.com&password=Admin@123"

# Parse token from response
$token = ($response.Content | ConvertFrom-Json).access_token
Write-Host "Token: $token"
```

### 4. Test API Endpoints with Token

#### Get Current User
```powershell
curl -Method GET -Uri "http://localhost:8000/api/auth/me" `
    -Headers @{"Authorization"="Bearer $token"}
```

#### List Employees
```powershell
curl -Method GET -Uri "http://localhost:8000/api/employees" `
    -Headers @{"Authorization"="Bearer $token"}
```

#### Get Analytics Dashboard
```powershell
curl -Method GET -Uri "http://localhost:8000/api/analytics/dashboard" `
    -Headers @{"Authorization"="Bearer $token"}
```

## Frontend Portal Testing Checklist

### Employee Portal (All Users)
- [ ] Dashboard - Home view loads
- [ ] Attendance - Clock in/out functionality
- [ ] Leave - Apply leave, view balance
- [ ] Performance - View performance metrics
- [ ] Expenses - Submit expense claims
- [ ] Helpdesk - Create support tickets
- [ ] Apps - Access integrated applications
- [ ] Profile - View and edit personal information

### Manager Portal (Manager Role)
- [ ] My Team - View team members
- [ ] Team Summary - Team productivity metrics
- [ ] Team Calendar - View team availability
- [ ] Approval Queue - Approve/reject requests
- [ ] Work Assignments - Assign tasks to team
- [ ] Team Analytics - View team performance

### HR Portal (HR/Admin Role)
- [ ] Organization - Company structure
- [ ] Directory - Employee directory
- [ ] Policies - Company policies management
- [ ] Payroll - Process payroll
- [ ] Recruitment - Manage hiring
- [ ] Reports - Generate HR reports
- [ ] Settings - System configuration

### Finance Portal (Finance Role)
- [ ] Finances - Financial overview
- [ ] Expense Reports - Review expenses
- [ ] Payroll Processing - Salary disbursement
- [ ] Budget Management - Track budgets

## Dark Mode Testing

### Components to Verify
1. **Navigation Sidebar**
   - Background should adapt to dark theme
   - Text color should have good contrast
   - Icons should be visible

2. **Dashboard Cards**
   - Card backgrounds should use dark theme colors
   - Text should be readable
   - Charts should use dark-appropriate colors

3. **Forms and Inputs**
   - Input fields should have dark backgrounds
   - Labels should be visible
   - Validation messages should be readable

4. **Tables and Lists**
   - Row backgrounds should alternate
   - Hover states should be visible
   - Text should have good contrast

5. **Modals and Dialogs**
   - Modal backgrounds should be dark
   - Overlay should be appropriate
   - Close buttons should be visible

## Color Palette Verification

### Current Themes
1. Blue-Purple (Default)
2. Emerald-Teal
3. Rose-Orange
4. Indigo-Violet

### Dark Mode Colors to Check
- **Background**: Should use dark grays (#1a1a1a to #2d2d2d)
- **Surface**: Cards/panels (#2a2a2a to #3a3a3a)
- **Text Primary**: High contrast white (#ffffff to #f5f5f5)
- **Text Secondary**: Medium contrast gray (#a0a0a0 to #b0b0b0)
- **Borders**: Subtle dark borders (#404040 to #505050)
- **Accents**: Theme colors should maintain vibrancy

## API Endpoints Test Matrix

| Endpoint | Method | Auth Required | Expected Result | Status |
|----------|--------|---------------|-----------------|--------|
| `/health` | GET | No | `{status: "healthy"}` | ✅ |
| `/api/auth/register` | POST | No | User created | ⏳ |
| `/api/auth/login` | POST | No | Token returned | ⏳ |
| `/api/auth/me` | GET | Yes | Current user data | ⏳ |
| `/api/employees` | GET | Yes | Employee list | ⏳ |
| `/api/employees/{id}` | GET | Yes | Single employee | ⏳ |
| `/api/attendance` | GET | Yes | Attendance records | ⏳ |
| `/api/attendance/clock-in` | POST | Yes | Clock in recorded | ⏳ |
| `/api/attendance/clock-out` | POST | Yes | Clock out recorded | ⏳ |
| `/api/leaves` | GET | Yes | Leave applications | ⏳ |
| `/api/leaves/balance` | GET | Yes | Leave balance | ⏳ |
| `/api/work-assignments` | GET | Yes | Task list | ⏳ |
| `/api/approvals/pending` | GET | Yes | Pending approvals | ⏳ |
| `/api/analytics/dashboard` | GET | Yes | Dashboard metrics | ⏳ |
| `/api/scheduler/status` | GET | Yes | Scheduler status | ⏳ |
| `/api/ai/chat` | POST | Yes | AI response | ⏳ |

## WebSocket Testing

### Connection Test
```javascript
// Open browser console at http://localhost:5174
const socket = io('http://localhost:8000', {
  auth: { token: localStorage.getItem('access_token') }
});

socket.on('connect', () => console.log('Connected!'));
socket.on('notification', (data) => console.log('Notification:', data));
socket.on('task_update', (data) => console.log('Task Update:', data));
socket.on('approval_update', (data) => console.log('Approval:', data));
```

## Browser Testing

### Browsers to Test
- [ ] Chrome/Edge (Chromium)
- [ ] Firefox
- [ ] Safari (if available)

### Screen Sizes
- [ ] Desktop (1920x1080)
- [ ] Laptop (1366x768)
- [ ] Tablet (768x1024)
- [ ] Mobile (375x667)

## Performance Benchmarks

### API Response Times
- Authentication: < 200ms
- List endpoints: < 500ms
- Dashboard: < 1000ms
- Analytics: < 2000ms

### Frontend Load Times
- Initial load: < 3s
- Route changes: < 500ms
- Component rendering: < 100ms

## Common Issues and Solutions

### Issue: CORS Error
**Solution**: Check ALLOWED_ORIGINS in .env file includes http://localhost:5174

### Issue: 401 Unauthorized
**Solution**: Token expired or invalid. Re-login to get new token.

### Issue: 404 Not Found
**Solution**: Check endpoint URL. API prefix is /api/

### Issue: Dark mode not working
**Solution**: Check localStorage for 'isDarkMode' setting. Toggle theme in UI.

### Issue: Components not loading
**Solution**: Check browser console for errors. Verify API connection.

## Manual Testing Script

### Phase 1: Authentication
1. Open http://localhost:5174
2. Register new user (if needed)
3. Login with credentials
4. Verify dashboard loads
5. Check user menu in top-right

### Phase 2: Employee Portal
1. Click "Me" in sidebar
2. Test Attendance - Clock in/out
3. Test Leave - Apply for leave
4. Test Performance - View metrics
5. Test Expenses - Create expense
6. Verify data saves correctly

### Phase 3: Manager Portal (if manager role)
1. Click "My Team"
2. View team members
3. Open Approval Queue
4. Test approve/reject workflow
5. Assign work to team member
6. View team analytics

### Phase 4: HR Portal (if HR/admin role)
1. Click "Organization"
2. View org chart
3. Access employee directory
4. Manage company policies
5. View reports
6. Test settings

### Phase 5: Dark Mode
1. Click user menu (top-right)
2. Toggle dark mode switch
3. Verify all pages adapt
4. Check readability
5. Test theme picker
6. Verify persistence after refresh

### Phase 6: AI Features
1. Click "AI Command Center"
2. Type a question
3. Verify AI responds
4. Test work assignment suggestion
5. Test employee search
6. Check conversation history

### Phase 7: Real-time Updates
1. Open two browser windows
2. Login as different users
3. Create notification in one
4. Verify appears in other
5. Test task assignments
6. Test approval notifications

## Automated Testing Commands

```powershell
# Backend tests
cd c:\forlast\hrms_backend
pytest tests/ -v

# Frontend linting
cd c:\forlast
npm run lint

# Security audit
npm audit
pip audit
```

## Success Criteria

### ✅ Must Pass
- [ ] All API endpoints return 200 OK (with auth)
- [ ] Login/logout works correctly
- [ ] Dark mode toggles properly
- [ ] All portals load without errors
- [ ] Data persists after refresh
- [ ] WebSocket connections establish

### ⚠️ Should Pass
- [ ] Response times meet benchmarks
- [ ] UI is responsive on all screen sizes
- [ ] No console errors
- [ ] All forms validate correctly
- [ ] Error messages are user-friendly

### 💡 Nice to Have
- [ ] Animations are smooth
- [ ] Loading states are informative
- [ ] Empty states have helpful messages
- [ ] Keyboard navigation works
- [ ] Screen reader compatible
