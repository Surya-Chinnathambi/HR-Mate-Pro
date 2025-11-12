import React, { useState, useEffect } from 'react';
import {
    Box,
    Card,
    CardContent,
    Typography,
    Grid,
    Paper,
    Select,
    MenuItem,
    FormControl,
    InputLabel,
    Button,
    Tabs,
    Tab,
    Chip,
    CircularProgress,
    Alert,
    IconButton,
    Tooltip,
    Divider,
    Stack,
} from '@mui/material';
import {
    BarChart,
    Bar,
    LineChart,
    Line,
    PieChart,
    Pie,
    AreaChart,
    Area,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip as RechartsTooltip,
    Legend,
    ResponsiveContainer,
    Cell,
} from 'recharts';
import {
    TrendingUp,
    TrendingDown,
    Download,
    Refresh,
    CalendarToday,
    Assessment,
    People,
    CheckCircle,
    AccessTime,
} from '@mui/icons-material';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { format, subDays, subMonths } from 'date-fns';
import apiClient from '../api/client';

// Color palette for charts
const COLORS = {
    primary: '#1976d2',
    secondary: '#dc004e',
    success: '#4caf50',
    warning: '#ff9800',
    error: '#f44336',
    info: '#2196f3',
    purple: '#9c27b0',
    teal: '#009688',
};

const CHART_COLORS = [
    COLORS.primary,
    COLORS.secondary,
    COLORS.success,
    COLORS.warning,
    COLORS.error,
    COLORS.info,
    COLORS.purple,
    COLORS.teal,
];

interface TabPanelProps {
    children?: React.ReactNode;
    index: number;
    value: number;
}

function TabPanel(props: TabPanelProps) {
    const { children, value, index, ...other } = props;
    return (
        <div role="tabpanel" hidden={value !== index} {...other}>
            {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
        </div>
    );
}

const AnalyticsDashboard: React.FC = () => {
    // State management
    const [activeTab, setActiveTab] = useState(0);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Date range state
    const [startDate, setStartDate] = useState<Date>(subDays(new Date(), 30));
    const [endDate, setEndDate] = useState<Date>(new Date());
    const [datePreset, setDatePreset] = useState('30days');

    // Filter state
    const [selectedDepartment, setSelectedDepartment] = useState<number | 'all'>('all');
    const [departments, setDepartments] = useState<any[]>([]);

    // Analytics data state
    const [productivityData, setProductivityData] = useState<any>(null);
    const [approvalData, setApprovalData] = useState<any>(null);
    const [workloadData, setWorkloadData] = useState<any>(null);
    const [trendsData, setTrendsData] = useState<any>(null);
    const [departmentComparison, setDepartmentComparison] = useState<any[]>([]);

    // Fetch all analytics data
    const fetchAnalytics = async () => {
        setLoading(true);
        setError(null);

        try {
            const params = {
                start_date: startDate.toISOString(),
                end_date: endDate.toISOString(),
                ...(selectedDepartment !== 'all' && { department_id: selectedDepartment }),
            };

            // Fetch all analytics endpoints in parallel
            const [productivity, approvals, workload, trends, deptComparison] = await Promise.all([
                apiClient.get('/analytics/productivity', { params }),
                apiClient.get('/analytics/approvals', { params }),
                apiClient.get('/analytics/workload', {
                    params: selectedDepartment !== 'all' ? { department_id: selectedDepartment } : {},
                }),
                apiClient.get('/analytics/trends', {
                    params: { ...params, metric_type: 'tasks', granularity: 'daily' },
                }),
                apiClient.get('/analytics/departments', { params }),
            ]);

            setProductivityData(productivity.data);
            setApprovalData(approvals.data);
            setWorkloadData(workload.data);
            setTrendsData(trends.data);
            setDepartmentComparison(deptComparison.data);

        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to fetch analytics');
            console.error('Analytics fetch error:', err);
        } finally {
            setLoading(false);
        }
    };

    // Fetch departments for filter
    useEffect(() => {
        const fetchDepartments = async () => {
            try {
                const response = await apiClient.get('/employees/departments');
                setDepartments(response.data || []);
            } catch (err) {
                console.error('Failed to fetch departments:', err);
            }
        };
        fetchDepartments();
    }, []);

    // Initial data fetch
    useEffect(() => {
        fetchAnalytics();
    }, [startDate, endDate, selectedDepartment]);

    // Handle date preset selection
    const handleDatePreset = (preset: string) => {
        setDatePreset(preset);
        const today = new Date();

        switch (preset) {
            case '7days':
                setStartDate(subDays(today, 7));
                setEndDate(today);
                break;
            case '30days':
                setStartDate(subDays(today, 30));
                setEndDate(today);
                break;
            case '90days':
                setStartDate(subDays(today, 90));
                setEndDate(today);
                break;
            case '6months':
                setStartDate(subMonths(today, 6));
                setEndDate(today);
                break;
            case '1year':
                setStartDate(subMonths(today, 12));
                setEndDate(today);
                break;
        }
    };

    // Export functionality (placeholder)
    const handleExport = (format: 'pdf' | 'excel' | 'csv') => {
        alert(`Export as ${format.toUpperCase()} - Feature coming soon!`);
        // TODO: Implement actual export logic
    };

    // Render metric card
    const renderMetricCard = (
        title: string,
        value: string | number,
        subtitle?: string,
        trend?: number,
        icon?: React.ReactNode,
        color?: string
    ) => (
        <Card elevation={2}>
            <CardContent>
                <Box display="flex" justifyContent="space-between" alignItems="start">
                    <Box flex={1}>
                        <Typography variant="body2" color="textSecondary" gutterBottom>
                            {title}
                        </Typography>
                        <Typography variant="h4" fontWeight="bold" color={color || 'primary'}>
                            {value}
                        </Typography>
                        {subtitle && (
                            <Typography variant="body2" color="textSecondary" mt={0.5}>
                                {subtitle}
                            </Typography>
                        )}
                        {trend !== undefined && (
                            <Box display="flex" alignItems="center" mt={1}>
                                {trend >= 0 ? (
                                    <TrendingUp color="success" fontSize="small" />
                                ) : (
                                    <TrendingDown color="error" fontSize="small" />
                                )}
                                <Typography
                                    variant="caption"
                                    color={trend >= 0 ? 'success.main' : 'error.main'}
                                    ml={0.5}
                                >
                                    {Math.abs(trend)}% vs last period
                                </Typography>
                            </Box>
                        )}
                    </Box>
                    {icon && (
                        <Box
                            sx={{
                                backgroundColor: `${color || COLORS.primary}20`,
                                borderRadius: 2,
                                p: 1.5,
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                            }}
                        >
                            {icon}
                        </Box>
                    )}
                </Box>
            </CardContent>
        </Card>
    );

    return (
        <LocalizationProvider dateAdapter={AdapterDateFns}>
            <Box sx={{ p: 3 }}>
                {/* Header */}
                <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
                    <Box>
                        <Typography variant="h4" fontWeight="bold" gutterBottom>
                            Analytics Dashboard
                        </Typography>
                        <Typography variant="body2" color="textSecondary">
                            Comprehensive insights and performance metrics
                        </Typography>
                    </Box>

                    <Stack direction="row" spacing={1}>
                        <Tooltip title="Refresh Data">
                            <IconButton onClick={fetchAnalytics} disabled={loading}>
                                <Refresh />
                            </IconButton>
                        </Tooltip>
                        <Button
                            variant="outlined"
                            startIcon={<Download />}
                            onClick={() => handleExport('pdf')}
                        >
                            Export PDF
                        </Button>
                        <Button
                            variant="outlined"
                            startIcon={<Download />}
                            onClick={() => handleExport('excel')}
                        >
                            Export Excel
                        </Button>
                    </Stack>
                </Box>

                {/* Filters */}
                <Paper elevation={1} sx={{ p: 2, mb: 3 }}>
                    <Grid container spacing={2} alignItems="center">
                        {/* Date Presets */}
                        <Grid size={{ xs: 12, md: 4 }}>
                            <FormControl fullWidth size="small">
                                <InputLabel>Date Range</InputLabel>
                                <Select
                                    value={datePreset}
                                    onChange={(e) => handleDatePreset(e.target.value)}
                                    label="Date Range"
                                >
                                    <MenuItem value="7days">Last 7 Days</MenuItem>
                                    <MenuItem value="30days">Last 30 Days</MenuItem>
                                    <MenuItem value="90days">Last 90 Days</MenuItem>
                                    <MenuItem value="6months">Last 6 Months</MenuItem>
                                    <MenuItem value="1year">Last Year</MenuItem>
                                    <MenuItem value="custom">Custom Range</MenuItem>
                                </Select>
                            </FormControl>
                        </Grid>

                        {/* Custom Date Range */}
                        {datePreset === 'custom' && (
                            <>
                                <Grid size={{ xs: 12, md: 3 }}>
                                    <DatePicker
                                        label="Start Date"
                                        value={startDate}
                                        onChange={(date) => date && setStartDate(date)}
                                        slotProps={{ textField: { fullWidth: true, size: 'small' } }}
                                    />
                                </Grid>
                                <Grid size={{ xs: 12, md: 3 }}>
                                    <DatePicker
                                        label="End Date"
                                        value={endDate}
                                        onChange={(date) => date && setEndDate(date)}
                                        slotProps={{ textField: { fullWidth: true, size: 'small' } }}
                                    />
                                </Grid>
                            </>
                        )}

                        {/* Department Filter */}
                        <Grid size={{ xs: 12, md: datePreset === 'custom' ? 2 : 4 }}>
                            <FormControl fullWidth size="small">
                                <InputLabel>Department</InputLabel>
                                <Select
                                    value={selectedDepartment}
                                    onChange={(e) => setSelectedDepartment(e.target.value as number | 'all')}
                                    label="Department"
                                >
                                    <MenuItem value="all">All Departments</MenuItem>
                                    {departments.map((dept) => (
                                        <MenuItem key={dept.department_id} value={dept.department_id}>
                                            {dept.name}
                                        </MenuItem>
                                    ))}
                                </Select>
                            </FormControl>
                        </Grid>

                        <Grid size={{ xs: 12, md: datePreset === 'custom' ? 12 : 4 }}>
                            <Typography variant="caption" color="textSecondary">
                                Showing data from {format(startDate, 'MMM dd, yyyy')} to {format(endDate, 'MMM dd, yyyy')}
                            </Typography>
                        </Grid>
                    </Grid>
                </Paper>

                {/* Loading & Error States */}
                {loading && (
                    <Box display="flex" justifyContent="center" alignItems="center" py={10}>
                        <CircularProgress />
                    </Box>
                )}

                {error && (
                    <Alert severity="error" sx={{ mb: 3 }}>
                        {error}
                    </Alert>
                )}

                {/* Main Content */}
                {!loading && !error && productivityData && (
                    <>
                        {/* Tabs */}
                        <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
                            <Tabs value={activeTab} onChange={(_, val) => setActiveTab(val)}>
                                <Tab label="Overview" icon={<Assessment />} iconPosition="start" />
                                <Tab label="Productivity" icon={<CheckCircle />} iconPosition="start" />
                                <Tab label="Approvals" icon={<AccessTime />} iconPosition="start" />
                                <Tab label="Workload" icon={<People />} iconPosition="start" />
                                <Tab label="Departments" icon={<Assessment />} iconPosition="start" />
                            </Tabs>
                        </Box>

                        {/* Overview Tab */}
                        <TabPanel value={activeTab} index={0}>
                            <Grid container spacing={3}>
                                {/* Key Metrics Row */}
                                <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                                    {renderMetricCard(
                                        'Total Tasks',
                                        productivityData.total_tasks,
                                        `${productivityData.completed_tasks} completed`,
                                        undefined,
                                        <Assessment sx={{ fontSize: 40, color: COLORS.primary }} />,
                                        COLORS.primary
                                    )}
                                </Grid>
                                <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                                    {renderMetricCard(
                                        'Completion Rate',
                                        `${productivityData.completion_rate.toFixed(1)}%`,
                                        'Tasks completed on time',
                                        undefined,
                                        <CheckCircle sx={{ fontSize: 40, color: COLORS.success }} />,
                                        COLORS.success
                                    )}
                                </Grid>
                                <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                                    {renderMetricCard(
                                        'Avg Completion Time',
                                        `${productivityData.avg_completion_time_hours.toFixed(1)}h`,
                                        'Hours to complete',
                                        undefined,
                                        <AccessTime sx={{ fontSize: 40, color: COLORS.warning }} />,
                                        COLORS.warning
                                    )}
                                </Grid>
                                <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                                    {renderMetricCard(
                                        'Approval Rate',
                                        `${approvalData?.approval_rate.toFixed(1)}%`,
                                        `${approvalData?.total_approvals} processed`,
                                        undefined,
                                        <TrendingUp sx={{ fontSize: 40, color: COLORS.info }} />,
                                        COLORS.info
                                    )}
                                </Grid>

                                {/* Task Trends Chart */}
                                <Grid size={{ xs: 12, md: 8 }}>
                                    <Card elevation={2}>
                                        <CardContent>
                                            <Typography variant="h6" gutterBottom>
                                                Task Trends Over Time
                                            </Typography>
                                            <ResponsiveContainer width="100%" height={300}>
                                                <AreaChart data={trendsData}>
                                                    <defs>
                                                        <linearGradient id="colorCreated" x1="0" y1="0" x2="0" y2="1">
                                                            <stop offset="5%" stopColor={COLORS.primary} stopOpacity={0.8} />
                                                            <stop offset="95%" stopColor={COLORS.primary} stopOpacity={0} />
                                                        </linearGradient>
                                                        <linearGradient id="colorCompleted" x1="0" y1="0" x2="0" y2="1">
                                                            <stop offset="5%" stopColor={COLORS.success} stopOpacity={0.8} />
                                                            <stop offset="95%" stopColor={COLORS.success} stopOpacity={0} />
                                                        </linearGradient>
                                                    </defs>
                                                    <CartesianGrid strokeDasharray="3 3" />
                                                    <XAxis
                                                        dataKey="date"
                                                        tickFormatter={(date) => format(new Date(date), 'MMM dd')}
                                                    />
                                                    <YAxis />
                                                    <RechartsTooltip />
                                                    <Legend />
                                                    <Area
                                                        type="monotone"
                                                        dataKey="created"
                                                        stroke={COLORS.primary}
                                                        fillOpacity={1}
                                                        fill="url(#colorCreated)"
                                                        name="Created"
                                                    />
                                                    <Area
                                                        type="monotone"
                                                        dataKey="completed"
                                                        stroke={COLORS.success}
                                                        fillOpacity={1}
                                                        fill="url(#colorCompleted)"
                                                        name="Completed"
                                                    />
                                                </AreaChart>
                                            </ResponsiveContainer>
                                        </CardContent>
                                    </Card>
                                </Grid>

                                {/* Task Distribution Pie Chart */}
                                <Grid size={{ xs: 12, md: 4 }}>
                                    <Card elevation={2}>
                                        <CardContent>
                                            <Typography variant="h6" gutterBottom>
                                                Tasks by Status
                                            </Typography>
                                            <ResponsiveContainer width="100%" height={300}>
                                                <PieChart>
                                                    <Pie
                                                        data={Object.entries(productivityData.tasks_by_status).map(([key, value]) => ({
                                                            name: key,
                                                            value,
                                                        }))}
                                                        cx="50%"
                                                        cy="50%"
                                                        labelLine={false}
                                                        label={({ name, percent }) => `${name}: ${((percent || 0) * 100).toFixed(0)}%`}
                                                        outerRadius={80}
                                                        fill="#8884d8"
                                                        dataKey="value"
                                                    >
                                                        {Object.entries(productivityData.tasks_by_status).map((_, index) => (
                                                            <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                                                        ))}
                                                    </Pie>
                                                    <RechartsTooltip />
                                                </PieChart>
                                            </ResponsiveContainer>
                                        </CardContent>
                                    </Card>
                                </Grid>

                                {/* Workload Distribution */}
                                <Grid size={{ xs: 12 }}>
                                    <Card elevation={2}>
                                        <CardContent>
                                            <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                                                <Typography variant="h6">
                                                    Workload Distribution
                                                </Typography>
                                                <Chip
                                                    label={`Balance Score: ${workloadData?.balance_score.toFixed(0)}/100`}
                                                    color={workloadData?.balance_score > 70 ? 'success' : 'warning'}
                                                />
                                            </Box>
                                            <ResponsiveContainer width="100%" height={300}>
                                                <BarChart
                                                    data={Object.entries(workloadData?.utilization_distribution || {}).map(
                                                        ([range, count]) => ({ range, count })
                                                    )}
                                                >
                                                    <CartesianGrid strokeDasharray="3 3" />
                                                    <XAxis dataKey="range" />
                                                    <YAxis />
                                                    <RechartsTooltip />
                                                    <Legend />
                                                    <Bar dataKey="count" fill={COLORS.primary} name="Employees" />
                                                </BarChart>
                                            </ResponsiveContainer>
                                        </CardContent>
                                    </Card>
                                </Grid>
                            </Grid>
                        </TabPanel>

                        {/* Productivity Tab */}
                        <TabPanel value={activeTab} index={1}>
                            <Grid container spacing={3}>
                                {/* Metrics */}
                                <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                                    {renderMetricCard(
                                        'Overdue Tasks',
                                        `${productivityData.overdue_percentage.toFixed(1)}%`,
                                        `${Math.round((productivityData.overdue_percentage / 100) * productivityData.total_tasks)} tasks`,
                                        undefined,
                                        undefined,
                                        COLORS.error
                                    )}
                                </Grid>
                                <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                                    {renderMetricCard(
                                        'High Priority',
                                        productivityData.tasks_by_priority?.HIGH || 0,
                                        'Active high priority tasks',
                                        undefined,
                                        undefined,
                                        COLORS.warning
                                    )}
                                </Grid>
                                <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                                    {renderMetricCard(
                                        'In Progress',
                                        productivityData.tasks_by_status?.IN_PROGRESS || 0,
                                        'Currently active',
                                        undefined,
                                        undefined,
                                        COLORS.info
                                    )}
                                </Grid>
                                <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                                    {renderMetricCard(
                                        'Blocked Tasks',
                                        productivityData.tasks_by_status?.BLOCKED || 0,
                                        'Require attention',
                                        undefined,
                                        undefined,
                                        COLORS.error
                                    )}
                                </Grid>

                                {/* Team Member Performance Table */}
                                <Grid size={{ xs: 12 }}>
                                    <Card elevation={2}>
                                        <CardContent>
                                            <Typography variant="h6" gutterBottom>
                                                Team Member Performance
                                            </Typography>
                                            <Box sx={{ overflowX: 'auto' }}>
                                                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                                                    <thead>
                                                        <tr style={{ backgroundColor: '#f5f5f5' }}>
                                                            <th style={{ padding: '12px', textAlign: 'left' }}>Employee ID</th>
                                                            <th style={{ padding: '12px', textAlign: 'right' }}>Total Assigned</th>
                                                            <th style={{ padding: '12px', textAlign: 'right' }}>Completed</th>
                                                            <th style={{ padding: '12px', textAlign: 'right' }}>In Progress</th>
                                                            <th style={{ padding: '12px', textAlign: 'right' }}>Overdue</th>
                                                            <th style={{ padding: '12px', textAlign: 'right' }}>Completion Rate</th>
                                                        </tr>
                                                    </thead>
                                                    <tbody>
                                                        {productivityData.team_member_performance?.map((member: any, idx: number) => (
                                                            <tr key={member.employee_id} style={{ borderBottom: '1px solid #e0e0e0' }}>
                                                                <td style={{ padding: '12px' }}>{member.employee_id}</td>
                                                                <td style={{ padding: '12px', textAlign: 'right' }}>{member.total_assigned}</td>
                                                                <td style={{ padding: '12px', textAlign: 'right', color: COLORS.success }}>
                                                                    {member.completed}
                                                                </td>
                                                                <td style={{ padding: '12px', textAlign: 'right' }}>{member.in_progress}</td>
                                                                <td style={{ padding: '12px', textAlign: 'right', color: COLORS.error }}>
                                                                    {member.overdue}
                                                                </td>
                                                                <td style={{ padding: '12px', textAlign: 'right' }}>
                                                                    <Chip
                                                                        label={`${member.completion_rate.toFixed(1)}%`}
                                                                        size="small"
                                                                        color={member.completion_rate >= 80 ? 'success' : member.completion_rate >= 60 ? 'warning' : 'error'}
                                                                    />
                                                                </td>
                                                            </tr>
                                                        ))}
                                                    </tbody>
                                                </table>
                                            </Box>
                                        </CardContent>
                                    </Card>
                                </Grid>
                            </Grid>
                        </TabPanel>

                        {/* Approvals Tab */}
                        <TabPanel value={activeTab} index={2}>
                            <Grid container spacing={3}>
                                {/* Approval Metrics */}
                                <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                                    {renderMetricCard(
                                        'Total Processed',
                                        approvalData?.total_approvals || 0,
                                        'Approvals processed',
                                        undefined,
                                        undefined,
                                        COLORS.primary
                                    )}
                                </Grid>
                                <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                                    {renderMetricCard(
                                        'Avg Turnaround',
                                        `${approvalData?.avg_turnaround_hours.toFixed(1)}h`,
                                        'Hours to approve',
                                        undefined,
                                        undefined,
                                        COLORS.info
                                    )}
                                </Grid>
                                <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                                    {renderMetricCard(
                                        'SLA Compliance',
                                        `${approvalData?.sla_compliance_rate.toFixed(1)}%`,
                                        'Within SLA',
                                        undefined,
                                        undefined,
                                        COLORS.success
                                    )}
                                </Grid>
                                <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                                    {renderMetricCard(
                                        'Escalation Rate',
                                        `${approvalData?.escalation_rate.toFixed(1)}%`,
                                        'Escalated approvals',
                                        undefined,
                                        undefined,
                                        COLORS.warning
                                    )}
                                </Grid>

                                {/* Turnaround by Type Chart */}
                                <Grid size={{ xs: 12, md: 6 }}>
                                    <Card elevation={2}>
                                        <CardContent>
                                            <Typography variant="h6" gutterBottom>
                                                Turnaround Time by Request Type
                                            </Typography>
                                            <ResponsiveContainer width="100%" height={300}>
                                                <BarChart
                                                    data={Object.entries(approvalData?.turnaround_by_type || {}).map(
                                                        ([type, data]: [string, any]) => ({
                                                            type,
                                                            avgHours: data.avg_hours,
                                                            count: data.count,
                                                        })
                                                    )}
                                                >
                                                    <CartesianGrid strokeDasharray="3 3" />
                                                    <XAxis dataKey="type" />
                                                    <YAxis label={{ value: 'Hours', angle: -90, position: 'insideLeft' }} />
                                                    <RechartsTooltip />
                                                    <Legend />
                                                    <Bar dataKey="avgHours" fill={COLORS.info} name="Avg Hours" />
                                                </BarChart>
                                            </ResponsiveContainer>
                                        </CardContent>
                                    </Card>
                                </Grid>

                                {/* Approver Performance */}
                                <Grid size={{ xs: 12, md: 6 }}>
                                    <Card elevation={2}>
                                        <CardContent>
                                            <Typography variant="h6" gutterBottom>
                                                Top Approvers (by volume)
                                            </Typography>
                                            <ResponsiveContainer width="100%" height={300}>
                                                <BarChart
                                                    data={(approvalData?.approver_performance || [])
                                                        .sort((a: any, b: any) => b.total_reviews - a.total_reviews)
                                                        .slice(0, 10)
                                                        .map((approver: any) => ({
                                                            id: `Emp ${approver.approver_id}`,
                                                            reviews: approver.total_reviews,
                                                            rate: approver.approval_rate,
                                                        }))}
                                                    layout="vertical"
                                                >
                                                    <CartesianGrid strokeDasharray="3 3" />
                                                    <XAxis type="number" />
                                                    <YAxis dataKey="id" type="category" width={80} />
                                                    <RechartsTooltip />
                                                    <Legend />
                                                    <Bar dataKey="reviews" fill={COLORS.primary} name="Total Reviews" />
                                                </BarChart>
                                            </ResponsiveContainer>
                                        </CardContent>
                                    </Card>
                                </Grid>
                            </Grid>
                        </TabPanel>

                        {/* Workload Tab */}
                        <TabPanel value={activeTab} index={3}>
                            <Grid container spacing={3}>
                                {/* Workload Metrics */}
                                <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                                    {renderMetricCard(
                                        'Avg Utilization',
                                        `${workloadData?.avg_utilization.toFixed(1)}%`,
                                        `${workloadData?.total_employees} employees`,
                                        undefined,
                                        undefined,
                                        COLORS.primary
                                    )}
                                </Grid>
                                <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                                    {renderMetricCard(
                                        'Overloaded',
                                        workloadData?.overloaded_employees?.length || 0,
                                        '>80% utilization',
                                        undefined,
                                        undefined,
                                        COLORS.error
                                    )}
                                </Grid>
                                <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                                    {renderMetricCard(
                                        'Underutilized',
                                        workloadData?.underutilized_employees?.length || 0,
                                        '<50% utilization',
                                        undefined,
                                        undefined,
                                        COLORS.warning
                                    )}
                                </Grid>
                                <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                                    {renderMetricCard(
                                        'Balance Score',
                                        `${workloadData?.balance_score.toFixed(0)}/100`,
                                        'Workload balance',
                                        undefined,
                                        undefined,
                                        workloadData?.balance_score > 70 ? COLORS.success : COLORS.warning
                                    )}
                                </Grid>

                                {/* Overloaded Employees List */}
                                {workloadData?.overloaded_employees?.length > 0 && (
                                    <Grid size={{ xs: 12, md: 6 }}>
                                        <Card elevation={2}>
                                            <CardContent>
                                                <Typography variant="h6" gutterBottom color="error">
                                                    Overloaded Employees (&gt;80%)
                                                </Typography>
                                                <Box sx={{ maxHeight: 300, overflowY: 'auto' }}>
                                                    {workloadData.overloaded_employees.map((emp: any) => (
                                                        <Box
                                                            key={emp.employee_id}
                                                            sx={{
                                                                p: 2,
                                                                mb: 1,
                                                                backgroundColor: '#fff3e0',
                                                                borderRadius: 1,
                                                                borderLeft: `4px solid ${COLORS.error}`,
                                                            }}
                                                        >
                                                            <Box display="flex" justifyContent="space-between">
                                                                <Typography variant="body1" fontWeight="bold">
                                                                    {emp.name}
                                                                </Typography>
                                                                <Chip
                                                                    label={`${emp.utilization.toFixed(1)}%`}
                                                                    color="error"
                                                                    size="small"
                                                                />
                                                            </Box>
                                                            <Typography variant="caption" color="textSecondary">
                                                                Current workload: {emp.current_workload_hours}h
                                                            </Typography>
                                                        </Box>
                                                    ))}
                                                </Box>
                                            </CardContent>
                                        </Card>
                                    </Grid>
                                )}

                                {/* Underutilized Employees List */}
                                {workloadData?.underutilized_employees?.length > 0 && (
                                    <Grid size={{ xs: 12, md: 6 }}>
                                        <Card elevation={2}>
                                            <CardContent>
                                                <Typography variant="h6" gutterBottom color="primary">
                                                    Underutilized Employees (&lt;50%)
                                                </Typography>
                                                <Box sx={{ maxHeight: 300, overflowY: 'auto' }}>
                                                    {workloadData.underutilized_employees.map((emp: any) => (
                                                        <Box
                                                            key={emp.employee_id}
                                                            sx={{
                                                                p: 2,
                                                                mb: 1,
                                                                backgroundColor: '#e3f2fd',
                                                                borderRadius: 1,
                                                                borderLeft: `4px solid ${COLORS.info}`,
                                                            }}
                                                        >
                                                            <Box display="flex" justifyContent="space-between">
                                                                <Typography variant="body1" fontWeight="bold">
                                                                    {emp.name}
                                                                </Typography>
                                                                <Chip
                                                                    label={`${emp.utilization.toFixed(1)}%`}
                                                                    color="info"
                                                                    size="small"
                                                                />
                                                            </Box>
                                                            <Typography variant="caption" color="textSecondary">
                                                                Current workload: {emp.current_workload_hours}h
                                                            </Typography>
                                                        </Box>
                                                    ))}
                                                </Box>
                                            </CardContent>
                                        </Card>
                                    </Grid>
                                )}
                            </Grid>
                        </TabPanel>

                        {/* Departments Tab */}
                        <TabPanel value={activeTab} index={4}>
                            <Grid container spacing={3}>
                                <Grid size={{ xs: 12 }}>
                                    <Card elevation={2}>
                                        <CardContent>
                                            <Typography variant="h6" gutterBottom>
                                                Department Performance Comparison
                                            </Typography>
                                            <ResponsiveContainer width="100%" height={400}>
                                                <BarChart data={departmentComparison}>
                                                    <CartesianGrid strokeDasharray="3 3" />
                                                    <XAxis dataKey="department_name" />
                                                    <YAxis />
                                                    <RechartsTooltip />
                                                    <Legend />
                                                    <Bar dataKey="completed_tasks" fill={COLORS.success} name="Completed Tasks" />
                                                    <Bar dataKey="total_approvals" fill={COLORS.info} name="Approvals" />
                                                </BarChart>
                                            </ResponsiveContainer>
                                        </CardContent>
                                    </Card>
                                </Grid>

                                <Grid size={{ xs: 12 }}>
                                    <Card elevation={2}>
                                        <CardContent>
                                            <Typography variant="h6" gutterBottom>
                                                Department Metrics Table
                                            </Typography>
                                            <Box sx={{ overflowX: 'auto' }}>
                                                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                                                    <thead>
                                                        <tr style={{ backgroundColor: '#f5f5f5' }}>
                                                            <th style={{ padding: '12px', textAlign: 'left' }}>Department</th>
                                                            <th style={{ padding: '12px', textAlign: 'right' }}>Employees</th>
                                                            <th style={{ padding: '12px', textAlign: 'right' }}>Total Tasks</th>
                                                            <th style={{ padding: '12px', textAlign: 'right' }}>Completed</th>
                                                            <th style={{ padding: '12px', textAlign: 'right' }}>Completion Rate</th>
                                                            <th style={{ padding: '12px', textAlign: 'right' }}>Approvals</th>
                                                            <th style={{ padding: '12px', textAlign: 'right' }}>Avg Utilization</th>
                                                        </tr>
                                                    </thead>
                                                    <tbody>
                                                        {departmentComparison.map((dept: any) => (
                                                            <tr key={dept.department_id} style={{ borderBottom: '1px solid #e0e0e0' }}>
                                                                <td style={{ padding: '12px', fontWeight: 'bold' }}>
                                                                    {dept.department_name}
                                                                </td>
                                                                <td style={{ padding: '12px', textAlign: 'right' }}>
                                                                    {dept.employee_count}
                                                                </td>
                                                                <td style={{ padding: '12px', textAlign: 'right' }}>
                                                                    {dept.total_tasks}
                                                                </td>
                                                                <td style={{ padding: '12px', textAlign: 'right', color: COLORS.success }}>
                                                                    {dept.completed_tasks}
                                                                </td>
                                                                <td style={{ padding: '12px', textAlign: 'right' }}>
                                                                    <Chip
                                                                        label={`${dept.completion_rate.toFixed(1)}%`}
                                                                        size="small"
                                                                        color={
                                                                            dept.completion_rate >= 80
                                                                                ? 'success'
                                                                                : dept.completion_rate >= 60
                                                                                    ? 'warning'
                                                                                    : 'error'
                                                                        }
                                                                    />
                                                                </td>
                                                                <td style={{ padding: '12px', textAlign: 'right' }}>
                                                                    {dept.total_approvals}
                                                                </td>
                                                                <td style={{ padding: '12px', textAlign: 'right' }}>
                                                                    <Chip
                                                                        label={`${dept.avg_utilization.toFixed(1)}%`}
                                                                        size="small"
                                                                        color={
                                                                            dept.avg_utilization > 80
                                                                                ? 'error'
                                                                                : dept.avg_utilization >= 60
                                                                                    ? 'success'
                                                                                    : 'warning'
                                                                        }
                                                                    />
                                                                </td>
                                                            </tr>
                                                        ))}
                                                    </tbody>
                                                </table>
                                            </Box>
                                        </CardContent>
                                    </Card>
                                </Grid>
                            </Grid>
                        </TabPanel>
                    </>
                )}
            </Box>
        </LocalizationProvider >
    );
};

export default AnalyticsDashboard;
