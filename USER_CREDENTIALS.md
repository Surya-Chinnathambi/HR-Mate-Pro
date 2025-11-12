# HRMS User Credentials - Temporary Access

## Organization Structure

### HR Department
**Febby Thomas** - HR Manager
- **Email:** febby.thomas@company.com
- **Password:** Febby@2024
- **Employee ID:** EMP1001
- **Role:** HR Manager
- **Designation:** HR Manager
- **Department:** Human Resources
- **Joining Date:** January 15, 2024

---

### Engineering Department

#### Manager
**Manohar Reddy** - Engineering Manager
- **Email:** manohar.reddy@company.com
- **Password:** Manohar@2024
- **Employee ID:** EMP1002
- **Role:** Manager
- **Designation:** Engineering Manager
- **Department:** Engineering
- **Joining Date:** February 1, 2024

#### Team Members

**Surya Chandra** - Senior Software Engineer
- **Email:** surya.chandra@company.com
- **Password:** Surya@2024
- **Employee ID:** EMP1003
- **Designation:** Senior Software Engineer
- **Joining Date:** March 1, 2024

**Kope Kumar** - Software Engineer
- **Email:** kope.kumar@company.com
- **Password:** Kope@2024
- **Employee ID:** EMP1004
- **Designation:** Software Engineer
- **Joining Date:** March 15, 2024

**Teja Rao** - Software Engineer
- **Email:** teja.rao@company.com
- **Password:** Teja@2024
- **Employee ID:** EMP1005
- **Designation:** Software Engineer
- **Joining Date:** April 1, 2024

**Srinithy Sharma** - Software Engineer
- **Email:** srinithy.sharma@company.com
- **Password:** Srinithy@2024
- **Employee ID:** EMP1006
- **Designation:** Software Engineer
- **Joining Date:** April 15, 2024

**Ashwatha Naik** - Junior Software Engineer
- **Email:** ashwatha.naik@company.com
- **Password:** Ashwatha@2024
- **Employee ID:** EMP1007
- **Designation:** Junior Software Engineer
- **Joining Date:** May 1, 2024

**Thrisha Menon** - Junior Software Engineer
- **Email:** thrisha.menon@company.com
- **Password:** Thrisha@2024
- **Employee ID:** EMP1008
- **Designation:** Junior Software Engineer
- **Joining Date:** May 15, 2024

---

## Quick Login Reference

| Name | Role | Email | Password | Employee ID |
|------|------|-------|----------|-------------|
| Febby Thomas | HR Manager | febby.thomas@company.com | Febby@2024 | EMP1001 |
| Manohar Reddy | Manager | manohar.reddy@company.com | Manohar@2024 | EMP1002 |
| Surya Chandra | Team Member | surya.chandra@company.com | Surya@2024 | EMP1003 |
| Kope Kumar | Team Member | kope.kumar@company.com | Kope@2024 | EMP1004 |
| Teja Rao | Team Member | teja.rao@company.com | Teja@2024 | EMP1005 |
| Srinithy Sharma | Team Member | srinithy.sharma@company.com | Srinithy@2024 | EMP1006 |
| Ashwatha Naik | Team Member | ashwatha.naik@company.com | Ashwatha@2024 | EMP1007 |
| Thrisha Menon | Team Member | thrisha.menon@company.com | Thrisha@2024 | EMP1008 |

---

## Security Notes

⚠️ **IMPORTANT:** These are temporary credentials for initial setup and testing.

- All passwords follow the format: `FirstName@2024`
- Users should change their passwords after first login
- Passwords meet security requirements (8+ characters, uppercase, lowercase, numbers, special characters)
- All accounts are set to ACTIVE status

## How to Seed the Database

Run the seed script from the `hrms_backend` directory:

```bash
python seed_users.py
```

This will create all users and their employee records in the database.

## Contact Hierarchy

```
Febby Thomas (HR Manager)
    └── Oversees all HR operations

Manohar Reddy (Engineering Manager)
    ├── Surya Chandra (Senior Software Engineer)
    ├── Kope Kumar (Software Engineer)
    ├── Teja Rao (Software Engineer)
    ├── Srinithy Sharma (Software Engineer)
    ├── Ashwatha Naik (Junior Software Engineer)
    └── Thrisha Menon (Junior Software Engineer)
```

---

**Generated on:** November 11, 2025
**System:** HRMS Pro
