# Security Audit Checklist for HRMS System

## Overview
This document provides a comprehensive security audit checklist for the enterprise HRMS system. Use this checklist to ensure all security measures are properly implemented and configured.

---

## 1. Authentication & Authorization

### ✅ Password Security
- [ ] **Password Complexity**: Enforce minimum 8 characters with uppercase, lowercase, numbers, and special characters
- [ ] **Password Hashing**: Using bcrypt with appropriate cost factor (currently 12 rounds)
  - Verify in: `app/core/security.py` - `get_password_hash()` function
- [ ] **Password Storage**: Never store plain text passwords in database
- [ ] **Password Reset**: Implement secure password reset with time-limited tokens
- [ ] **Account Lockout**: Implement account lockout after 5 failed login attempts
- [ ] **Password History**: Prevent password reuse (last 5 passwords)

### ✅ JWT Token Security
- [ ] **Secret Key Strength**: Minimum 32 characters, cryptographically random
  - Current location: `.env` file - `SECRET_KEY` variable
  - Action: Change default key in production!
- [ ] **Token Expiration**: Access tokens expire in 30 minutes (configurable)
- [ ] **Refresh Tokens**: Implement refresh tokens with 7-day expiration
- [ ] **Token Revocation**: Implement token blacklisting mechanism
- [ ] **Secure Storage**: Store tokens in httpOnly cookies (not localStorage)
- [ ] **HTTPS Only**: Ensure tokens are only transmitted over HTTPS

### ✅ Role-Based Access Control (RBAC)
- [ ] **Role Enforcement**: Verify all endpoints check user roles
  - Check: `@require_role()` decorators in API routes
- [ ] **Principle of Least Privilege**: Users have minimum necessary permissions
- [ ] **Role Validation**: Test unauthorized access attempts return 403
- [ ] **Admin Access**: Super admin role is properly protected
- [ ] **Employee Hierarchy**: Managers can only access direct reports' data

### ✅ Session Management
- [ ] **Session Timeout**: Automatic logout after 30 minutes of inactivity
- [ ] **Concurrent Sessions**: Limit to 3 concurrent sessions per user
- [ ] **Session Invalidation**: Logout invalidates all user sessions
- [ ] **Remember Me**: If implemented, use secure long-lived tokens

---

## 2. Input Validation & Sanitization

### ✅ SQL Injection Prevention
- [ ] **Parameterized Queries**: All database queries use SQLModel/SQLAlchemy ORM
  - No raw SQL queries with string concatenation
- [ ] **Input Validation**: All API inputs validated with Pydantic schemas
- [ ] **Type Checking**: Enforce strict type checking on all inputs
- [ ] **Test SQL Injection**: Run automated SQLi tests with tools like SQLMap

### ✅ Cross-Site Scripting (XSS) Prevention
- [ ] **Output Encoding**: All user-generated content is HTML-encoded
- [ ] **Content Security Policy**: CSP headers configured in Nginx
  - Location: `nginx/nginx.conf` - `add_header Content-Security-Policy`
- [ ] **Input Sanitization**: Remove/escape dangerous characters (<, >, ", ', &)
- [ ] **React Protection**: Using React (escapes by default) for frontend
- [ ] **Test XSS**: Test with common XSS payloads

### ✅ Cross-Site Request Forgery (CSRF) Prevention
- [ ] **CSRF Tokens**: Implement CSRF tokens for state-changing operations
- [ ] **SameSite Cookies**: Set `SameSite=Strict` on authentication cookies
- [ ] **Origin Validation**: Verify request origin matches allowed domains
- [ ] **CORS Configuration**: Properly configured in `main.py`
  - Current: ALLOWED_ORIGINS in .env file

### ✅ API Input Validation
- [ ] **Request Size Limits**: Max request body size = 10MB
- [ ] **File Upload Validation**: 
  - Max file size: 5MB per file
  - Allowed types: PDF, DOCX, XLSX, PNG, JPG
  - Filename sanitization
- [ ] **JSON Validation**: Use Pydantic models for all JSON inputs
- [ ] **Path Traversal Prevention**: Sanitize all file path inputs
- [ ] **Command Injection Prevention**: Never execute shell commands with user input

---

## 3. Database Security

### ✅ Connection Security
- [ ] **Encrypted Connections**: Use SSL/TLS for database connections
  - PostgreSQL: `sslmode=require` in connection string
- [ ] **Strong Credentials**: Database password minimum 16 characters
  - Current: `postgres:postgres` (CHANGE IN PRODUCTION!)
- [ ] **Connection Pooling**: Max 10 connections, timeout 30s
- [ ] **Principle of Least Privilege**: Application user has minimal database permissions

### ✅ Data Protection
- [ ] **Sensitive Data Encryption**: Encrypt PII at rest
  - SSN, bank accounts, salary information
- [ ] **Column-Level Encryption**: Use `pgcrypto` extension for sensitive columns
- [ ] **Backup Encryption**: All database backups encrypted with AES-256
- [ ] **Secure Deletion**: Implement soft deletes with audit trail
- [ ] **Data Masking**: Mask sensitive data in non-production environments

### ✅ Query Security
- [ ] **Prepared Statements**: Always use parameterized queries
- [ ] **Query Timeouts**: Set 30-second timeout on all queries
- [ ] **Row-Level Security**: Implement RLS policies for multi-tenant data
- [ ] **Audit Logging**: Log all data access and modifications
  - Table: `audit_logs`

---

## 4. API Security

### ✅ Rate Limiting
- [ ] **API Endpoints**: 10 requests/second per IP
  - Configured in: `nginx/nginx.conf` - `limit_req_zone $binary_remote_addr`
- [ ] **WebSocket Connections**: 5 connections/second per IP
- [ ] **Login Endpoint**: 5 attempts/15 minutes per IP
- [ ] **Rate Limit Headers**: Return X-RateLimit-* headers
- [ ] **Rate Limit Storage**: Use Redis for distributed rate limiting

### ✅ API Authentication
- [ ] **Bearer Token Authentication**: All protected endpoints require JWT
- [ ] **Token Validation**: Verify token signature and expiration
- [ ] **Audience Validation**: Check token audience claim
- [ ] **Issuer Validation**: Verify token issuer
- [ ] **API Key Security**: If using API keys, rotate every 90 days

### ✅ API Versioning & Deprecation
- [ ] **Version Management**: Use URL versioning (/api/v1/)
- [ ] **Deprecation Warnings**: Warn clients 90 days before deprecation
- [ ] **Breaking Changes**: Never introduce breaking changes in same version
- [ ] **Documentation**: Keep API docs updated (Swagger at /api/docs)

### ✅ Error Handling
- [ ] **Generic Error Messages**: Don't expose stack traces to clients
- [ ] **HTTP Status Codes**: Use appropriate status codes
  - 400: Bad Request, 401: Unauthorized, 403: Forbidden, 404: Not Found
- [ ] **Error Logging**: Log all errors with context
- [ ] **Sensitive Data**: Never include passwords/tokens in error messages

---

## 5. Network Security

### ✅ HTTPS/TLS Configuration
- [ ] **Force HTTPS**: Redirect all HTTP to HTTPS
  - Configured in: `nginx/nginx.conf` - server block on port 80
- [ ] **TLS Version**: Minimum TLS 1.2, prefer TLS 1.3
  - Set: `ssl_protocols TLSv1.2 TLSv1.3;`
- [ ] **Strong Ciphers**: Use modern cipher suites
  - Check: `ssl_ciphers` in Nginx config
- [ ] **HSTS Header**: Enforce HTTPS for 1 year
  - `add_header Strict-Transport-Security "max-age=31536000; includeSubDomains"`
- [ ] **Certificate Validation**: Valid SSL certificate (Let's Encrypt or commercial)

### ✅ Firewall Configuration
- [ ] **UFW Enabled**: Uncomplicated Firewall active on server
- [ ] **Port Restrictions**:
  - Allow: 22 (SSH), 80 (HTTP), 443 (HTTPS)
  - Deny: 5432 (PostgreSQL), 6379 (Redis) from external
- [ ] **Fail2ban**: Installed and configured for SSH, HTTP
  - Ban after 5 failed attempts, 1-hour ban duration
- [ ] **IP Whitelisting**: Restrict admin endpoints to known IPs

### ✅ Security Headers
- [ ] **X-Frame-Options**: DENY (prevent clickjacking)
- [ ] **X-Content-Type-Options**: nosniff
- [ ] **X-XSS-Protection**: 1; mode=block
- [ ] **Referrer-Policy**: strict-origin-when-cross-origin
- [ ] **Permissions-Policy**: Disable unnecessary features
- [ ] **Content-Security-Policy**: Restrict resource loading
  - Check: `nginx/nginx.conf` - all add_header directives

---

## 6. Application Security

### ✅ Dependency Management
- [ ] **Vulnerability Scanning**: Run `pip audit` monthly
- [ ] **Dependency Updates**: Update dependencies quarterly
- [ ] **Lock Files**: Commit `requirements.txt` and `package-lock.json`
- [ ] **Security Advisories**: Monitor GitHub security alerts
- [ ] **Deprecated Packages**: Remove or replace deprecated packages

### ✅ Code Security
- [ ] **Static Analysis**: Run Bandit for Python code
  - `pip install bandit; bandit -r app/`
- [ ] **Linting**: Use Pylint, ESLint for code quality
- [ ] **Code Review**: All code changes peer-reviewed
- [ ] **Secrets Detection**: Use tools like GitGuardian, TruffleHog
- [ ] **No Hardcoded Secrets**: All secrets in environment variables

### ✅ File Upload Security
- [ ] **File Type Validation**: Whitelist allowed MIME types
- [ ] **File Size Limits**: Max 5MB per file, 20MB per request
- [ ] **Virus Scanning**: Integrate ClamAV for uploaded files
- [ ] **Storage Isolation**: Store uploads outside web root
- [ ] **File Permissions**: Uploaded files not executable (chmod 644)

### ✅ WebSocket Security
- [ ] **Authentication**: Require JWT token for WebSocket connections
- [ ] **Rate Limiting**: 5 connections/second per IP
- [ ] **Message Validation**: Validate all incoming WebSocket messages
- [ ] **Connection Limits**: Max 100 concurrent connections per user
- [ ] **Timeout**: Auto-disconnect after 5 minutes of inactivity

---

## 7. Logging & Monitoring

### ✅ Security Logging
- [ ] **Authentication Events**: Log all login/logout/failed attempts
- [ ] **Authorization Failures**: Log 401/403 responses with context
- [ ] **Data Access**: Log access to sensitive data (audit_logs table)
- [ ] **Configuration Changes**: Log all system configuration changes
- [ ] **Security Events**: Log rate limit violations, suspicious activity

### ✅ Log Management
- [ ] **Centralized Logging**: Send logs to centralized system (ELK, Splunk)
- [ ] **Log Rotation**: Rotate logs daily, retain 90 days
- [ ] **Log Integrity**: Use write-once storage or log signing
- [ ] **Sensitive Data**: Never log passwords, tokens, credit cards
- [ ] **Structured Logging**: Use JSON format for easy parsing

### ✅ Monitoring & Alerting
- [ ] **Uptime Monitoring**: Use Pingdom, UptimeRobot, or similar
- [ ] **Performance Monitoring**: Track response times, error rates
- [ ] **Security Alerts**: Alert on:
  - 10+ failed logins in 5 minutes
  - SQL injection attempts
  - Privilege escalation attempts
  - Unusual database queries
- [ ] **Capacity Monitoring**: Alert on high CPU, memory, disk usage

---

## 8. Infrastructure Security

### ✅ Server Hardening
- [ ] **OS Updates**: Apply security patches monthly
- [ ] **Minimal Services**: Disable unnecessary services
- [ ] **SSH Hardening**:
  - Disable root login
  - Use SSH keys (not passwords)
  - Change default port from 22
  - Install Fail2ban
- [ ] **User Permissions**: No services run as root
- [ ] **File Permissions**: Proper chmod on sensitive files

### ✅ Container Security (Docker)
- [ ] **Base Images**: Use official, minimal base images
- [ ] **Image Scanning**: Scan images with Trivy, Clair
- [ ] **Non-Root User**: Containers run as non-root user
  - Check: `USER hrms` in Dockerfile
- [ ] **Resource Limits**: Set CPU and memory limits
- [ ] **Read-Only Filesystem**: Use read-only root filesystem where possible
- [ ] **Secrets Management**: Use Docker secrets, not environment variables

### ✅ Cloud Security (if applicable)
- [ ] **IAM Policies**: Principle of least privilege
- [ ] **Security Groups**: Minimal open ports
- [ ] **VPC Configuration**: Private subnets for databases
- [ ] **Encryption at Rest**: Enable for all storage services
- [ ] **Backup Security**: Encrypted, immutable backups
- [ ] **MFA**: Enable for all admin accounts

---

## 9. Data Privacy & Compliance

### ✅ GDPR Compliance (if applicable)
- [ ] **Data Minimization**: Collect only necessary data
- [ ] **Consent Management**: Explicit consent for data processing
- [ ] **Right to Access**: Users can download their data
- [ ] **Right to Deletion**: Users can request data deletion
- [ ] **Data Portability**: Export data in machine-readable format
- [ ] **Privacy Policy**: Clear, accessible privacy policy

### ✅ Data Retention
- [ ] **Retention Policy**: Define retention periods for each data type
  - Audit logs: 90 days
  - Old notifications: 30 days
  - Completed tasks: 1 year
- [ ] **Automated Cleanup**: Scheduler job runs weekly
  - Check: `app/services/scheduler.py` - `cleanup_old_records()`
- [ ] **Secure Deletion**: Overwrite or encrypt before deletion

### ✅ Data Classification
- [ ] **Classification Levels**: Public, Internal, Confidential, Restricted
- [ ] **PII Identification**: Identify all personally identifiable information
- [ ] **Access Controls**: Apply controls based on data classification
- [ ] **Data Labeling**: Tag sensitive data in database

---

## 10. Incident Response

### ✅ Incident Response Plan
- [ ] **Response Team**: Defined security incident response team
- [ ] **Contact Information**: Emergency contacts documented
- [ ] **Escalation Procedures**: Clear escalation path
- [ ] **Communication Plan**: How to notify affected users
- [ ] **Forensics**: Process for preserving evidence

### ✅ Breach Procedures
- [ ] **Detection**: Automated alerts for security events
- [ ] **Containment**: Steps to isolate compromised systems
- [ ] **Eradication**: Remove malware, close vulnerabilities
- [ ] **Recovery**: Restore from clean backups
- [ ] **Notification**: Legal requirements for breach notification

### ✅ Security Testing
- [ ] **Penetration Testing**: Annual penetration tests
- [ ] **Vulnerability Scans**: Monthly automated scans
- [ ] **Bug Bounty Program**: Consider public bug bounty
- [ ] **Red Team Exercises**: Simulate attacks annually

---

## 11. Third-Party Security

### ✅ API Security (External Integrations)
- [ ] **OpenAI API**: Secure API key storage
  - Check: `.env` file - `AZURE_OPENAI_KEY`
- [ ] **API Key Rotation**: Rotate keys every 90 days
- [ ] **Error Handling**: Don't expose API keys in errors
- [ ] **Network Restrictions**: Whitelist IP addresses if possible

### ✅ Frontend Security
- [ ] **React Security**: Using React 19 (latest security patches)
- [ ] **Dependencies**: Run `npm audit` monthly
- [ ] **Subresource Integrity**: Use SRI for CDN resources
- [ ] **Environment Variables**: Don't expose secrets in frontend
  - Prefix with `VITE_` for public variables only

---

## 12. Backup & Recovery

### ✅ Backup Strategy
- [ ] **Frequency**: Daily incremental, weekly full backups
  - Script location: Mentioned in DEPLOYMENT_GUIDE.md
- [ ] **Encryption**: All backups encrypted with AES-256
- [ ] **Offsite Storage**: Store backups in different location/region
- [ ] **Retention**: Keep daily backups for 7 days, weekly for 4 weeks, monthly for 1 year
- [ ] **Testing**: Test restore process monthly

### ✅ Disaster Recovery
- [ ] **RTO (Recovery Time Objective)**: Define acceptable downtime (e.g., 4 hours)
- [ ] **RPO (Recovery Point Objective)**: Define acceptable data loss (e.g., 1 hour)
- [ ] **DR Plan**: Documented disaster recovery procedures
- [ ] **Failover Testing**: Test failover process quarterly
- [ ] **Communication Plan**: How to communicate during outages

---

## Security Audit Schedule

### Daily
- Review failed login attempts
- Check system logs for anomalies
- Monitor rate limit violations

### Weekly
- Review user access logs
- Check for new CVEs in dependencies
- Review backup success/failure logs

### Monthly
- Run vulnerability scans
- Update dependencies
- Review security logs in detail
- Test backup restoration
- Review API usage patterns

### Quarterly
- Update all dependencies
- Review and update security policies
- Conduct internal security training
- Review access control lists
- Audit user permissions

### Annually
- Conduct penetration testing
- Review and update incident response plan
- Conduct disaster recovery drill
- Review compliance requirements
- Security architecture review

---

## Critical Security Reminders

### 🔴 MUST CHANGE BEFORE PRODUCTION
1. **SECRET_KEY** in `.env` - Generate strong 32+ character key
2. **Database Password** - Change from `postgres:postgres`
3. **Redis Password** - Set strong password (currently none)
4. **Admin Accounts** - Remove default/test accounts
5. **Debug Mode** - Set `DEBUG=False` in production
6. **ALLOWED_ORIGINS** - Restrict to production domains only

### 🟡 HIGH PRIORITY
1. Configure SSL certificates (Let's Encrypt recommended)
2. Enable Fail2ban for brute force protection
3. Set up backup automation with encryption
4. Configure monitoring and alerting
5. Implement rate limiting in production

### 🟢 RECOMMENDED
1. Set up centralized logging (ELK Stack)
2. Implement SIEM for security monitoring
3. Enable database query auditing
4. Set up Web Application Firewall (WAF)
5. Conduct security awareness training

---

## Tools for Security Testing

### Automated Scanning
```bash
# Python dependency vulnerabilities
pip install pip-audit
pip-audit

# Python code security issues
pip install bandit
bandit -r app/

# JavaScript dependency vulnerabilities
npm audit

# Docker image vulnerabilities
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image hrms_backend:latest
```

### Manual Testing
- **Burp Suite**: Web application security testing
- **OWASP ZAP**: Automated security scanning
- **SQLMap**: SQL injection testing
- **Nmap**: Network port scanning
- **Nikto**: Web server scanning

---

## Compliance Checklist

### OWASP Top 10 (2021)
- [ ] A01: Broken Access Control
- [ ] A02: Cryptographic Failures
- [ ] A03: Injection
- [ ] A04: Insecure Design
- [ ] A05: Security Misconfiguration
- [ ] A06: Vulnerable and Outdated Components
- [ ] A07: Identification and Authentication Failures
- [ ] A08: Software and Data Integrity Failures
- [ ] A09: Security Logging and Monitoring Failures
- [ ] A10: Server-Side Request Forgery (SSRF)

### CIS Benchmarks
- [ ] CIS PostgreSQL Benchmark
- [ ] CIS Docker Benchmark
- [ ] CIS Linux Benchmark
- [ ] CIS Nginx Benchmark

---

## Sign-Off

### Audit Completed By
- **Name**: ______________________
- **Date**: ______________________
- **Role**: ______________________
- **Signature**: ______________________

### Findings Summary
- **Critical Issues**: ___
- **High Priority**: ___
- **Medium Priority**: ___
- **Low Priority**: ___

### Next Audit Date
- **Scheduled**: ______________________

---

## Additional Resources

- [OWASP Cheat Sheet Series](https://cheatsheetseries.owasp.org/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [CIS Controls](https://www.cisecurity.org/controls)
- [FastAPI Security Best Practices](https://fastapi.tiangolo.com/tutorial/security/)
- [PostgreSQL Security Best Practices](https://www.postgresql.org/docs/current/security.html)
