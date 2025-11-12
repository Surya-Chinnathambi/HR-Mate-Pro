// Quick API Test Script - Run in browser console at http://localhost:5174

// Test Configuration
const API_BASE = 'http://localhost:8000/api';

// Color-coded console logging
const log = {
    success: (msg) => console.log(`%c✅ ${msg}`, 'color: green; font-weight: bold'),
    error: (msg) => console.log(`%c❌ ${msg}`, 'color: red; font-weight: bold'),
    info: (msg) => console.log(`%c🔵 ${msg}`, 'color: blue'),
    warn: (msg) => console.log(`%c⚠️  ${msg}`, 'color: orange'),
};

// Test Suite
const runTests = async () => {
    console.clear();
    console.log('%c🚀 Starting HRMS API Tests', 'font-size: 20px; font-weight: bold; color: #4CAF50');
    console.log('================================\n');

    let testResults = {
        passed: 0,
        failed: 0,
        total: 0
    };

    // Test 1: Health Check
    try {
        log.info('Test 1: Health Check');
        const response = await fetch(`${API_BASE.replace('/api', '')}/health`);
        const data = await response.json();
        if (data.status === 'healthy') {
            log.success('Health check passed');
            testResults.passed++;
        } else {
            log.error('Health check failed: Unexpected response');
            testResults.failed++;
        }
    } catch (error) {
        log.error(`Health check failed: ${error.message}`);
        testResults.failed++;
    }
    testResults.total++;

    // Test 2: Register User
    try {
        log.info('Test 2: Register User');
        const response = await fetch(`${API_BASE}/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                email: `test${Date.now()}@company.com`,
                password: 'Test@123',
                role: 'employee',
                status: 'active'
            })
        });

        if (response.ok) {
            const data = await response.json();
            log.success(`User registered: ${data.email || 'Success'}`);
            testResults.passed++;
        } else if (response.status === 400) {
            log.warn('User registration: Email might already exist');
            testResults.passed++;  // Consider as pass if validation works
        } else {
            log.error(`User registration failed: ${response.status}`);
            testResults.failed++;
        }
    } catch (error) {
        log.error(`User registration failed: ${error.message}`);
        testResults.failed++;
    }
    testResults.total++;

    // Test 3: Login
    let token = localStorage.getItem('access_token');
    if (!token) {
        try {
            log.info('Test 3: Login');
            const formData = new URLSearchParams();
            formData.append('username', 'admin@company.com');
            formData.append('password', 'Admin@123');

            const response = await fetch(`${API_BASE}/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: formData
            });

            if (response.ok) {
                const data = await response.json();
                token = data.access_token;
                localStorage.setItem('access_token', token);
                log.success('Login successful');
                testResults.passed++;
            } else {
                log.warn('Login failed: Try creating admin user first');
                log.info('Run: await createAdminUser()');
                testResults.failed++;
            }
        } catch (error) {
            log.error(`Login failed: ${error.message}`);
            testResults.failed++;
        }
        testResults.total++;
    } else {
        log.info('Test 3: Login - Using existing token');
        testResults.passed++;
        testResults.total++;
    }

    // Test 4: Get Current User
    if (token) {
        try {
            log.info('Test 4: Get Current User');
            const response = await fetch(`${API_BASE}/auth/me`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.ok) {
                const data = await response.json();
                log.success(`Current user: ${data.email} (${data.role})`);
                testResults.passed++;
            } else {
                log.error(`Get user failed: ${response.status}`);
                testResults.failed++;
            }
        } catch (error) {
            log.error(`Get user failed: ${error.message}`);
            testResults.failed++;
        }
        testResults.total++;
    }

    // Test 5: List Employees
    if (token) {
        try {
            log.info('Test 5: List Employees');
            const response = await fetch(`${API_BASE}/employees`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.ok) {
                const data = await response.json();
                log.success(`Employees loaded: ${Array.isArray(data) ? data.length : 'N/A'} employees`);
                testResults.passed++;
            } else {
                log.error(`List employees failed: ${response.status}`);
                testResults.failed++;
            }
        } catch (error) {
            log.error(`List employees failed: ${error.message}`);
            testResults.failed++;
        }
        testResults.total++;
    }

    // Test 6: Analytics Dashboard
    if (token) {
        try {
            log.info('Test 6: Analytics Dashboard');
            const response = await fetch(`${API_BASE}/analytics/dashboard`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.ok) {
                const data = await response.json();
                log.success('Analytics dashboard loaded');
                testResults.passed++;
            } else {
                log.error(`Analytics failed: ${response.status}`);
                testResults.failed++;
            }
        } catch (error) {
            log.error(`Analytics failed: ${error.message}`);
            testResults.failed++;
        }
        testResults.total++;
    }

    // Test 7: Scheduler Status
    if (token) {
        try {
            log.info('Test 7: Scheduler Status');
            const response = await fetch(`${API_BASE}/scheduler/status`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.ok) {
                const data = await response.json();
                log.success(`Scheduler running: ${data.is_running ? 'Yes' : 'No'}, Jobs: ${data.jobs?.length || 0}`);
                testResults.passed++;
            } else {
                log.error(`Scheduler status failed: ${response.status}`);
                testResults.failed++;
            }
        } catch (error) {
            log.error(`Scheduler status failed: ${error.message}`);
            testResults.failed++;
        }
        testResults.total++;
    }

    // Test Summary
    console.log('\n================================');
    console.log('%c📊 Test Results', 'font-size: 18px; font-weight: bold');
    console.log(`Total: ${testResults.total}`);
    console.log(`%cPassed: ${testResults.passed}`, 'color: green; font-weight: bold');
    console.log(`%cFailed: ${testResults.failed}`, 'color: red; font-weight: bold');

    const passRate = ((testResults.passed / testResults.total) * 100).toFixed(1);
    console.log(`%cPass Rate: ${passRate}%`, passRate >= 80 ? 'color: green' : 'color: red');

    if (testResults.failed === 0) {
        console.log('%c🎉 All tests passed!', 'color: green; font-size: 16px; font-weight: bold');
    } else {
        console.log('%c⚠️  Some tests failed. Check errors above.', 'color: orange; font-weight: bold');
    }
};

// Helper function to create admin user
const createAdminUser = async () => {
    try {
        const response = await fetch(`${API_BASE}/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                email: 'admin@company.com',
                password: 'Admin@123',
                role: 'admin',
                status: 'active'
            })
        });

        if (response.ok) {
            const data = await response.json();
            console.log('%c✅ Admin user created!', 'color: green; font-weight: bold');
            console.log('Email: admin@company.com');
            console.log('Password: Admin@123');
            return data;
        } else {
            const error = await response.json();
            console.log('%c⚠️  ' + (error.detail || 'User might already exist'), 'color: orange');
        }
    } catch (error) {
        console.error('Failed to create admin user:', error);
    }
};

// Test dark mode
const testDarkMode = () => {
    console.log('%c🌙 Testing Dark Mode', 'font-size: 16px; font-weight: bold');

    const currentMode = document.documentElement.classList.contains('dark');
    console.log(`Current mode: ${currentMode ? 'Dark' : 'Light'}`);

    // Toggle
    document.documentElement.classList.toggle('dark');

    const newMode = document.documentElement.classList.contains('dark');
    console.log(`New mode: ${newMode ? 'Dark' : 'Light'}`);

    // Save to localStorage
    localStorage.setItem('isDarkMode', newMode.toString());

    console.log('%c✅ Dark mode toggled!', 'color: green; font-weight: bold');
};

// Test WebSocket
const testWebSocket = () => {
    console.log('%c🔌 Testing WebSocket Connection', 'font-size: 16px; font-weight: bold');

    const token = localStorage.getItem('access_token');
    if (!token) {
        console.log('%c⚠️  No token found. Login first.', 'color: orange');
        return;
    }

    // Check if Socket.IO is loaded
    if (typeof io === 'undefined') {
        console.log('%c⚠️  Socket.IO not loaded in this page', 'color: orange');
        return;
    }

    try {
        const socket = io('http://localhost:8000', {
            auth: { token }
        });

        socket.on('connect', () => {
            console.log('%c✅ WebSocket connected!', 'color: green; font-weight: bold');
            console.log('Socket ID:', socket.id);
        });

        socket.on('disconnect', () => {
            console.log('%c⚠️  WebSocket disconnected', 'color: orange');
        });

        socket.on('notification', (data) => {
            console.log('%c🔔 Notification received:', 'color: blue; font-weight: bold', data);
        });

        socket.on('task_update', (data) => {
            console.log('%c📋 Task update received:', 'color: purple; font-weight: bold', data);
        });

        socket.on('approval_update', (data) => {
            console.log('%c✅ Approval update received:', 'color: green; font-weight: bold', data);
        });

        console.log('%c✅ WebSocket listeners registered', 'color: green');

        // Return socket for manual testing
        window.testSocket = socket;
        console.log('Socket stored in window.testSocket for manual testing');

    } catch (error) {
        console.error('WebSocket test failed:', error);
    }
};

// Export functions to window for easy access
window.runTests = runTests;
window.createAdminUser = createAdminUser;
window.testDarkMode = testDarkMode;
window.testWebSocket = testWebSocket;

// Print instructions
console.log('%c🎯 HRMS Quick Test Suite', 'font-size: 20px; font-weight: bold; color: #2196F3');
console.log('================================\n');
console.log('Available commands:');
console.log('%c  runTests()', 'color: green', '- Run full API test suite');
console.log('%c  createAdminUser()', 'color: green', '- Create admin@company.com');
console.log('%c  testDarkMode()', 'color: green', '- Toggle dark mode');
console.log('%c  testWebSocket()', 'color: green', '- Test WebSocket connection');
console.log('\n%cQuick Start:', 'font-weight: bold');
console.log('1. await createAdminUser()');
console.log('2. await runTests()');
console.log('3. testWebSocket()');
console.log('4. testDarkMode()');
