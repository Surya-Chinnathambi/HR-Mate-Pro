import React, { useState, useEffect } from 'react';
import {
    Box,
    Grid,
    Card,
    CardContent,
    CardHeader,
    Typography,
    Button,
    TextField,
    Select,
    MenuItem,
    FormControl,
    InputLabel,
    Chip,
    Avatar,
    IconButton,
    Badge,
    Tooltip,
    CircularProgress,
    Alert,
    Tab,
    Tabs,
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    Paper,
    LinearProgress,
    Skeleton,
    Divider,
    Stack,
    ToggleButton,
    ToggleButtonGroup,
} from '@mui/material';
import {
    Refresh as RefreshIcon,
    Add as AddIcon,
    CheckCircle as ApproveIcon,
    Cancel as RejectIcon,
    Notifications as NotificationsIcon,
    Assignment as AssignmentIcon,
    TrendingUp as TrendingUpIcon,
    People as PeopleIcon,
    Warning as WarningIcon,
    AccessTime as TimeIcon,
    SmartToy as AIIcon,
    ExpandMore as ExpandMoreIcon,
    ExpandLess as ExpandLessIcon,
} from '@mui/icons-material';
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
import apiClient from '../api/client';

// ============================================================================
// TYPE DEFINITIONS
// ============================================================================

interface Employee {
    id: number;
    full_name: string;
    email: string;
    department?: string;
    position?: string;
    reporting_manager_id?: number;
    current_workload_hours: number;
    max_workload_hours: number;
    is_manager: boolean;
    avatar?: string;
}

interface WorkloadData {
    employee_id: number;
    name: string;
    current_workload_hours: number;
    max_workload_hours: number;
    utilization_percent: number;
    capacity_status: 'overloaded' | 'balanced' | 'available';
    available_hours: number;
    skills?: string;
    active_tasks?: Task[];
}

interface Task {
    task_id: number;
    title: string;
    priority: 'low' | 'medium' | 'high' | 'urgent';
    status: string;
    due_date?: string;
    estimated_hours?: number;
}

interface ApprovalRequest {
    id: number;
    request_type: string;
    requester_name: string;
    priority: string;
    current_level: number;
    total_levels: number;
    assigned_at: string;
    time_pending_hours: number;
    approval_steps: ApprovalStep[];
}

interface ApprovalStep {
    level: number;
    approver_name: string;
    status: string;
    reviewed_at?: string;
    assigned_at?: string;
}

interface Notification {
    id: number;
    title: string;
    message: string;
    type: string;
    created_at: string;
    is_read: boolean;
}

interface AssignmentForm {
    title: string;
    description: string;
    assigneeId: number;
    priority: 'low' | 'medium' | 'high' | 'urgent';
    dueDate: string;
    estimatedHours: number;
    projectName: string;
    tags: string[];
}

interface AISuggestion {
    employee_id: number;
    name: string;
    score: number;
    utilization_percent: number;
    available_hours: number;
    skills: string;
    reasons: string[];
    recommendation: string;
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

const ManagerDashboard: React.FC = () => {
    // State Management
    const [loading, setLoading] = useState(true);
    const [teamWorkload, setTeamWorkload] = useState<WorkloadData[]>([]);
    const [pendingApprovals, setPendingApprovals] = useState<ApprovalRequest[]>([]);
    const [notifications, setNotifications] = useState<Notification[]>([]);
    const [teamAnalytics, setTeamAnalytics] = useState<any>(null);
    const [activeTab, setActiveTab] = useState(0);
    const [selectedEmployee, setSelectedEmployee] = useState<number | null>(null);
    const [expandedApprovals, setExpandedApprovals] = useState<Set<number>>(new Set());

    // Assignment Form State
    const [assignmentDialogOpen, setAssignmentDialogOpen] = useState(false);
    const [assignmentForm, setAssignmentForm] = useState<AssignmentForm>({
        title: '',
        description: '',
        assigneeId: 0,
        priority: 'medium',
        dueDate: '',
        estimatedHours: 8,
        projectName: '',
        tags: [],
    });
    const [aiSuggestions, setAiSuggestions] = useState<AISuggestion[]>([]);
    const [loadingSuggestions, setLoadingSuggestions] = useState(false);

    // Approval Action State
    const [approvalDialogOpen, setApprovalDialogOpen] = useState(false);
    const [selectedApproval, setSelectedApproval] = useState<ApprovalRequest | null>(null);
    const [approvalAction, setApprovalAction] = useState<'approve' | 'reject'>('approve');
    const [approvalComment, setApprovalComment] = useState('');

    // ============================================================================
    // DATA FETCHING
    // ============================================================================

    useEffect(() => {
        fetchDashboardData();
        const interval = setInterval(fetchDashboardData, 30000); // Refresh every 30 seconds
        return () => clearInterval(interval);
    }, []);

    const fetchDashboardData = async () => {
        try {
            setLoading(true);
            const [workloadRes, approvalsRes, notificationsRes, analyticsRes] = await Promise.all([
                apiClient.get('/work-assignments/analytics/workload', { params: { includeDetails: true } }),
                apiClient.get('/approvals/pending'),
                apiClient.get('/notifications', { params: { limit: 10 } }),
                apiClient.get('/approvals/metrics'),
            ]);

            setTeamWorkload(workloadRes.data.team_workload || []);
            setPendingApprovals(approvalsRes.data || []);
            setNotifications(notificationsRes.data || []);
            setTeamAnalytics(analyticsRes.data || null);
        } catch (error) {
            console.error('Error fetching dashboard data:', error);
        } finally {
            setLoading(false);
        }
    };

    const getAISuggestions = async () => {
        if (!assignmentForm.description) return;

        setLoadingSuggestions(true);
        try {
            const response = await apiClient.post('/ai/chat', {
                message: `suggestWorkAssignment(taskDescription="${assignmentForm.description}", estimatedHours=${assignmentForm.estimatedHours}, priority="${assignmentForm.priority}", topN=3)`,
            });

            if (response.data.suggestions) {
                setAiSuggestions(response.data.suggestions);
            }
        } catch (error) {
            console.error('Error getting AI suggestions:', error);
        } finally {
            setLoadingSuggestions(false);
        }
    };

    const handleAssignWork = async () => {
        try {
            await apiClient.post('/work-assignments/', {
                title: assignmentForm.title,
                description: assignmentForm.description,
                assignee_id: assignmentForm.assigneeId,
                priority: assignmentForm.priority,
                due_date: assignmentForm.dueDate,
                estimated_hours: assignmentForm.estimatedHours,
                project_name: assignmentForm.projectName,
                tags: assignmentForm.tags,
            });

            setAssignmentDialogOpen(false);
            setAssignmentForm({
                title: '',
                description: '',
                assigneeId: 0,
                priority: 'medium',
                dueDate: '',
                estimatedHours: 8,
                projectName: '',
                tags: [],
            });
            setAiSuggestions([]);
            fetchDashboardData();
        } catch (error) {
            console.error('Error assigning work:', error);
        }
    };

    const handleApprovalAction = async () => {
        if (!selectedApproval || !approvalComment || approvalComment.length < 10) return;

        try {
            const endpoint = approvalAction === 'approve'
                ? `/approvals/${selectedApproval.id}/approve`
                : `/approvals/${selectedApproval.id}/reject`;

            await apiClient.post(endpoint, { comments: approvalComment });

            setApprovalDialogOpen(false);
            setSelectedApproval(null);
            setApprovalComment('');
            fetchDashboardData();
        } catch (error) {
            console.error('Error processing approval:', error);
        }
    };

    // ============================================================================
    // UTILITY FUNCTIONS
    // ============================================================================

    const getCapacityColor = (utilizationPercent: number): string => {
        if (utilizationPercent > 80) return '#ef5350'; // Red - Overloaded
        if (utilizationPercent > 60) return '#ffa726'; // Orange - Balanced
        return '#66bb6a'; // Green - Available
    };

    const getPriorityColor = (priority: string): string => {
        const colors: Record<string, string> = {
            urgent: '#d32f2f',
            high: '#f57c00',
            medium: '#1976d2',
            low: '#388e3c',
        };
        return colors[priority] || '#757575';
    };

    const formatTimeAgo = (dateString: string): string => {
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffHours = Math.floor(diffMs / (1000 * 60 * 60));

        if (diffHours < 1) return 'Just now';
        if (diffHours < 24) return `${diffHours}h ago`;
        const diffDays = Math.floor(diffHours / 24);
        return `${diffDays}d ago`;
    };

    // ============================================================================
    // RENDER: TEAM HIERARCHY & WORKLOAD SECTION
    // ============================================================================

    const renderTeamHierarchy = () => (
        <Card sx={{ height: '100%' }}>
            <CardHeader
                title={
                    <Box display="flex" alignItems="center" gap={1}>
                        <PeopleIcon />
                        <Typography variant="h6">Team Workload Overview</Typography>
                    </Box>
                }
                action={
                    <IconButton onClick={fetchDashboardData}>
                        <RefreshIcon />
                    </IconButton>
                }
            />
            <CardContent>
                {loading ? (
                    <Stack spacing={2}>
                        {[1, 2, 3].map((i) => (
                            <Skeleton key={i} variant="rectangular" height={80} />
                        ))}
                    </Stack>
                ) : (
                    <Grid container spacing={2}>
                        {teamWorkload.map((member) => (
                            <Grid item xs={12} md={6} key={member.employee_id}>
                                <Card
                                    variant="outlined"
                                    sx={{
                                        border: `2px solid ${getCapacityColor(member.utilization_percent)}`,
                                        cursor: 'pointer',
                                        '&:hover': { boxShadow: 3 },
                                    }}
                                    onClick={() => setSelectedEmployee(
                                        selectedEmployee === member.employee_id ? null : member.employee_id
                                    )}
                                >
                                    <CardContent>
                                        <Box display="flex" alignItems="center" gap={2} mb={2}>
                                            <Avatar sx={{ bgcolor: getCapacityColor(member.utilization_percent) }}>
                                                {member.name.charAt(0)}
                                            </Avatar>
                                            <Box flex={1}>
                                                <Typography variant="subtitle1" fontWeight="bold">
                                                    {member.name}
                                                </Typography>
                                                <Typography variant="caption" color="text.secondary">
                                                    {member.skills || 'No skills listed'}
                                                </Typography>
                                            </Box>
                                            <Chip
                                                label={`${Math.round(member.utilization_percent)}%`}
                                                size="small"
                                                sx={{
                                                    bgcolor: getCapacityColor(member.utilization_percent),
                                                    color: 'white',
                                                    fontWeight: 'bold',
                                                }}
                                            />
                                        </Box>

                                        <Box mb={1}>
                                            <Box display="flex" justifyContent="space-between" mb={0.5}>
                                                <Typography variant="caption">Workload</Typography>
                                                <Typography variant="caption">
                                                    {member.current_workload_hours}h / {member.max_workload_hours}h
                                                </Typography>
                                            </Box>
                                            <LinearProgress
                                                variant="determinate"
                                                value={Math.min(member.utilization_percent, 100)}
                                                sx={{
                                                    height: 8,
                                                    borderRadius: 1,
                                                    bgcolor: 'grey.200',
                                                    '& .MuiLinearProgress-bar': {
                                                        bgcolor: getCapacityColor(member.utilization_percent),
                                                    },
                                                }}
                                            />
                                        </Box>

                                        <Box display="flex" gap={1} flexWrap="wrap">
                                            <Chip
                                                label={member.capacity_status.toUpperCase()}
                                                size="small"
                                                color={
                                                    member.capacity_status === 'overloaded' ? 'error' :
                                                        member.capacity_status === 'available' ? 'success' : 'warning'
                                                }
                                            />
                                            <Chip
                                                label={`${member.available_hours}h available`}
                                                size="small"
                                                variant="outlined"
                                            />
                                        </Box>

                                        {selectedEmployee === member.employee_id && member.active_tasks && (
                                            <Box mt={2}>
                                                <Divider sx={{ my: 1 }} />
                                                <Typography variant="caption" fontWeight="bold">
                                                    Active Tasks ({member.active_tasks.length})
                                                </Typography>
                                                <Stack spacing={0.5} mt={1}>
                                                    {member.active_tasks.map((task) => (
                                                        <Box
                                                            key={task.task_id}
                                                            sx={{
                                                                p: 1,
                                                                bgcolor: 'grey.50',
                                                                borderRadius: 1,
                                                                borderLeft: `3px solid ${getPriorityColor(task.priority)}`,
                                                            }}
                                                        >
                                                            <Typography variant="caption" display="block">
                                                                {task.title}
                                                            </Typography>
                                                            <Box display="flex" gap={0.5} mt={0.5}>
                                                                <Chip label={task.priority} size="small" sx={{ height: 16, fontSize: '0.7rem' }} />
                                                                <Chip label={task.status} size="small" sx={{ height: 16, fontSize: '0.7rem' }} />
                                                                {task.estimated_hours && (
                                                                    <Chip
                                                                        label={`${task.estimated_hours}h`}
                                                                        size="small"
                                                                        sx={{ height: 16, fontSize: '0.7rem' }}
                                                                    />
                                                                )}
                                                            </Box>
                                                        </Box>
                                                    ))}
                                                </Stack>
                                            </Box>
                                        )}
                                    </CardContent>
                                </Card>
                            </Grid>
                        ))}

                        {teamWorkload.length === 0 && (
                            <Grid item xs={12}>
                                <Alert severity="info">No team members found. Make sure employees have reporting_manager_id set to your employee ID.</Alert>
                            </Grid>
                        )}
                    </Grid>
                )}
            </CardContent>
        </Card>
    );

    // ============================================================================
    // RENDER: APPROVAL QUEUE SECTION
    // ============================================================================

    const renderApprovalQueue = () => (
        <Card>
            <CardHeader
                title={
                    <Box display="flex" alignItems="center" gap={1}>
                        <AssignmentIcon />
                        <Typography variant="h6">Pending Approvals</Typography>
                        <Badge badgeContent={pendingApprovals.length} color="error" sx={{ ml: 1 }} />
                    </Box>
                }
                action={
                    <IconButton onClick={fetchDashboardData}>
                        <RefreshIcon />
                    </IconButton>
                }
            />
            <CardContent>
                {loading ? (
                    <Stack spacing={1}>
                        {[1, 2, 3].map((i) => (
                            <Skeleton key={i} variant="rectangular" height={60} />
                        ))}
                    </Stack>
                ) : pendingApprovals.length === 0 ? (
                    <Alert severity="success">🎉 No pending approvals! You're all caught up.</Alert>
                ) : (
                    <TableContainer>
                        <Table size="small">
                            <TableHead>
                                <TableRow>
                                    <TableCell>Requester</TableCell>
                                    <TableCell>Type</TableCell>
                                    <TableCell>Priority</TableCell>
                                    <TableCell>Level</TableCell>
                                    <TableCell>Pending</TableCell>
                                    <TableCell align="right">Actions</TableCell>
                                </TableRow>
                            </TableHead>
                            <TableBody>
                                {pendingApprovals.map((approval) => (
                                    <React.Fragment key={approval.id}>
                                        <TableRow hover>
                                            <TableCell>
                                                <Box display="flex" alignItems="center" gap={1}>
                                                    <Avatar sx={{ width: 32, height: 32 }}>
                                                        {approval.requester_name.charAt(0)}
                                                    </Avatar>
                                                    <Typography variant="body2">{approval.requester_name}</Typography>
                                                </Box>
                                            </TableCell>
                                            <TableCell>
                                                <Chip
                                                    label={approval.request_type.replace('_', ' ')}
                                                    size="small"
                                                    variant="outlined"
                                                />
                                            </TableCell>
                                            <TableCell>
                                                <Chip
                                                    label={approval.priority}
                                                    size="small"
                                                    sx={{
                                                        bgcolor: getPriorityColor(approval.priority),
                                                        color: 'white',
                                                    }}
                                                />
                                            </TableCell>
                                            <TableCell>
                                                <Typography variant="caption">
                                                    {approval.current_level} / {approval.total_levels}
                                                </Typography>
                                            </TableCell>
                                            <TableCell>
                                                <Tooltip title={`Assigned ${formatTimeAgo(approval.assigned_at)}`}>
                                                    <Chip
                                                        icon={<TimeIcon />}
                                                        label={`${Math.round(approval.time_pending_hours)}h`}
                                                        size="small"
                                                        color={approval.time_pending_hours > 24 ? 'error' : 'default'}
                                                    />
                                                </Tooltip>
                                            </TableCell>
                                            <TableCell align="right">
                                                <IconButton
                                                    size="small"
                                                    onClick={() => {
                                                        const newExpanded = new Set(expandedApprovals);
                                                        if (newExpanded.has(approval.id)) {
                                                            newExpanded.delete(approval.id);
                                                        } else {
                                                            newExpanded.add(approval.id);
                                                        }
                                                        setExpandedApprovals(newExpanded);
                                                    }}
                                                >
                                                    {expandedApprovals.has(approval.id) ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                                                </IconButton>
                                                <Tooltip title="Approve">
                                                    <IconButton
                                                        size="small"
                                                        color="success"
                                                        onClick={() => {
                                                            setSelectedApproval(approval);
                                                            setApprovalAction('approve');
                                                            setApprovalDialogOpen(true);
                                                        }}
                                                    >
                                                        <ApproveIcon />
                                                    </IconButton>
                                                </Tooltip>
                                                <Tooltip title="Reject">
                                                    <IconButton
                                                        size="small"
                                                        color="error"
                                                        onClick={() => {
                                                            setSelectedApproval(approval);
                                                            setApprovalAction('reject');
                                                            setApprovalDialogOpen(true);
                                                        }}
                                                    >
                                                        <RejectIcon />
                                                    </IconButton>
                                                </Tooltip>
                                            </TableCell>
                                        </TableRow>

                                        {expandedApprovals.has(approval.id) && (
                                            <TableRow>
                                                <TableCell colSpan={6} sx={{ bgcolor: 'grey.50' }}>
                                                    <Typography variant="caption" fontWeight="bold" gutterBottom>
                                                        Approval Chain:
                                                    </Typography>
                                                    <Stack direction="row" spacing={1} flexWrap="wrap">
                                                        {approval.approval_steps.map((step, idx) => (
                                                            <Chip
                                                                key={idx}
                                                                label={`${step.level}. ${step.approver_name} - ${step.status.toUpperCase()}`}
                                                                size="small"
                                                                color={
                                                                    step.status === 'approved' ? 'success' :
                                                                        step.status === 'pending' ? 'warning' : 'error'
                                                                }
                                                                sx={{ mt: 0.5 }}
                                                            />
                                                        ))}
                                                    </Stack>
                                                </TableCell>
                                            </TableRow>
                                        )}
                                    </React.Fragment>
                                ))}
                            </TableBody>
                        </Table>
                    </TableContainer>
                )}
            </CardContent>
        </Card>
    );

    // ============================================================================
    // RENDER: WORK ASSIGNMENT FORM
    // ============================================================================

    const renderWorkAssignmentForm = () => (
        <Card>
            <CardHeader
                title={
                    <Box display="flex" alignItems="center" gap={1}>
                        <AddIcon />
                        <Typography variant="h6">Assign Work</Typography>
                    </Box>
                }
                action={
                    <Button
                        variant="contained"
                        startIcon={<AddIcon />}
                        onClick={() => setAssignmentDialogOpen(true)}
                    >
                        New Assignment
                    </Button>
                }
            />
            <CardContent>
                <Alert severity="info" icon={<AIIcon />}>
                    Click "New Assignment" to create a task with AI-powered employee suggestions based on skills and workload.
                </Alert>
            </CardContent>
        </Card>
    );

    // ============================================================================
    // RENDER: TEAM ANALYTICS
    // ============================================================================

    const renderTeamAnalytics = () => {
        if (!teamAnalytics) return null;

        const utilizationData = teamWorkload.map((member) => ({
            name: member.name.split(' ')[0],
            actual: member.current_workload_hours,
            capacity: member.max_workload_hours,
        }));

        const approvalData = teamAnalytics.by_request_type
            ? Object.entries(teamAnalytics.by_request_type).map(([type, data]: [string, any]) => ({
                type,
                total: data.total,
                approved: data.approved,
                rejected: data.rejected,
            }))
            : [];

        return (
            <Grid container spacing={2}>
                <Grid item xs={12} md={6}>
                    <Card>
                        <CardHeader title="Team Utilization" />
                        <CardContent>
                            <ResponsiveContainer width="100%" height={250}>
                                <BarChart data={utilizationData}>
                                    <CartesianGrid strokeDasharray="3 3" />
                                    <XAxis dataKey="name" />
                                    <YAxis />
                                    <RechartsTooltip />
                                    <Legend />
                                    <Bar dataKey="actual" fill="#1976d2" name="Current Hours" />
                                    <Bar dataKey="capacity" fill="#e0e0e0" name="Max Capacity" />
                                </BarChart>
                            </ResponsiveContainer>
                        </CardContent>
                    </Card>
                </Grid>

                <Grid item xs={12} md={6}>
                    <Card>
                        <CardHeader title="Approval Statistics" />
                        <CardContent>
                            <Grid container spacing={2}>
                                <Grid item xs={6}>
                                    <Paper sx={{ p: 2, textAlign: 'center' }}>
                                        <Typography variant="h4" color="primary">
                                            {teamAnalytics.pending || 0}
                                        </Typography>
                                        <Typography variant="caption">Pending</Typography>
                                    </Paper>
                                </Grid>
                                <Grid item xs={6}>
                                    <Paper sx={{ p: 2, textAlign: 'center' }}>
                                        <Typography variant="h4" color="success.main">
                                            {teamAnalytics.approved || 0}
                                        </Typography>
                                        <Typography variant="caption">Approved</Typography>
                                    </Paper>
                                </Grid>
                                <Grid item xs={6}>
                                    <Paper sx={{ p: 2, textAlign: 'center' }}>
                                        <Typography variant="h4" color="error.main">
                                            {teamAnalytics.rejected || 0}
                                        </Typography>
                                        <Typography variant="caption">Rejected</Typography>
                                    </Paper>
                                </Grid>
                                <Grid item xs={6}>
                                    <Paper sx={{ p: 2, textAlign: 'center' }}>
                                        <Typography variant="h4">
                                            {teamAnalytics.avg_response_time_hours
                                                ? `${Math.round(teamAnalytics.avg_response_time_hours)}h`
                                                : 'N/A'}
                                        </Typography>
                                        <Typography variant="caption">Avg Response Time</Typography>
                                    </Paper>
                                </Grid>
                            </Grid>

                            {approvalData.length > 0 && (
                                <Box mt={2}>
                                    <ResponsiveContainer width="100%" height={200}>
                                        <BarChart data={approvalData}>
                                            <CartesianGrid strokeDasharray="3 3" />
                                            <XAxis dataKey="type" />
                                            <YAxis />
                                            <RechartsTooltip />
                                            <Legend />
                                            <Bar dataKey="approved" fill="#4caf50" stackId="a" />
                                            <Bar dataKey="rejected" fill="#f44336" stackId="a" />
                                        </BarChart>
                                    </ResponsiveContainer>
                                </Box>
                            )}
                        </CardContent>
                    </Card>
                </Grid>
            </Grid>
        );
    };

    // ============================================================================
    // RENDER: NOTIFICATIONS PANEL
    // ============================================================================

    const renderNotifications = () => (
        <Card>
            <CardHeader
                title={
                    <Box display="flex" alignItems="center" gap={1}>
                        <Badge badgeContent={notifications.filter(n => !n.is_read).length} color="error">
                            <NotificationsIcon />
                        </Badge>
                        <Typography variant="h6">Recent Notifications</Typography>
                    </Box>
                }
            />
            <CardContent>
                {notifications.length === 0 ? (
                    <Alert severity="info">No notifications</Alert>
                ) : (
                    <Stack spacing={1} maxHeight={300} sx={{ overflowY: 'auto' }}>
                        {notifications.slice(0, 10).map((notification) => (
                            <Paper
                                key={notification.id}
                                sx={{
                                    p: 1.5,
                                    bgcolor: notification.is_read ? 'transparent' : 'action.hover',
                                    cursor: 'pointer',
                                    '&:hover': { bgcolor: 'action.selected' },
                                }}
                            >
                                <Box display="flex" justifyContent="space-between" alignItems="start">
                                    <Box flex={1}>
                                        <Typography variant="subtitle2" fontWeight="bold">
                                            {notification.title}
                                        </Typography>
                                        <Typography variant="body2" color="text.secondary">
                                            {notification.message}
                                        </Typography>
                                    </Box>
                                    <Typography variant="caption" color="text.secondary">
                                        {formatTimeAgo(notification.created_at)}
                                    </Typography>
                                </Box>
                            </Paper>
                        ))}
                    </Stack>
                )}
            </CardContent>
        </Card>
    );

    // ============================================================================
    // RENDER: DIALOGS
    // ============================================================================

    const renderAssignmentDialog = () => (
        <Dialog
            open={assignmentDialogOpen}
            onClose={() => setAssignmentDialogOpen(false)}
            maxWidth="md"
            fullWidth
        >
            <DialogTitle>Assign New Work</DialogTitle>
            <DialogContent>
                <Stack spacing={2} mt={1}>
                    <TextField
                        label="Task Title"
                        fullWidth
                        value={assignmentForm.title}
                        onChange={(e) => setAssignmentForm({ ...assignmentForm, title: e.target.value })}
                        required
                    />

                    <TextField
                        label="Description"
                        fullWidth
                        multiline
                        rows={3}
                        value={assignmentForm.description}
                        onChange={(e) => setAssignmentForm({ ...assignmentForm, description: e.target.value })}
                        required
                    />

                    <Button
                        variant="outlined"
                        startIcon={loadingSuggestions ? <CircularProgress size={20} /> : <AIIcon />}
                        onClick={getAISuggestions}
                        disabled={!assignmentForm.description || loadingSuggestions}
                    >
                        Get AI Suggestions
                    </Button>

                    {aiSuggestions.length > 0 && (
                        <Box>
                            <Typography variant="subtitle2" gutterBottom>
                                🤖 AI Recommendations:
                            </Typography>
                            <Stack spacing={1}>
                                {aiSuggestions.map((suggestion) => (
                                    <Paper
                                        key={suggestion.employee_id}
                                        sx={{
                                            p: 2,
                                            cursor: 'pointer',
                                            border: assignmentForm.assigneeId === suggestion.employee_id ? 2 : 0,
                                            borderColor: 'primary.main',
                                            '&:hover': { bgcolor: 'action.hover' },
                                        }}
                                        onClick={() => setAssignmentForm({ ...assignmentForm, assigneeId: suggestion.employee_id })}
                                    >
                                        <Box display="flex" justifyContent="space-between" alignItems="start">
                                            <Box>
                                                <Typography variant="subtitle2" fontWeight="bold">
                                                    {suggestion.name}
                                                </Typography>
                                                <Typography variant="caption" color="text.secondary">
                                                    {suggestion.skills}
                                                </Typography>
                                                <Box mt={0.5}>
                                                    {suggestion.reasons.map((reason, idx) => (
                                                        <Chip key={idx} label={reason} size="small" sx={{ mr: 0.5, mt: 0.5 }} />
                                                    ))}
                                                </Box>
                                            </Box>
                                            <Chip
                                                label={`Score: ${Math.round(suggestion.score)}`}
                                                color={suggestion.score >= 70 ? 'success' : suggestion.score >= 50 ? 'primary' : 'default'}
                                            />
                                        </Box>
                                    </Paper>
                                ))}
                            </Stack>
                        </Box>
                    )}

                    <FormControl fullWidth>
                        <InputLabel>Assignee</InputLabel>
                        <Select
                            value={assignmentForm.assigneeId}
                            onChange={(e) => setAssignmentForm({ ...assignmentForm, assigneeId: Number(e.target.value) })}
                            required
                        >
                            <MenuItem value={0}>Select Employee</MenuItem>
                            {teamWorkload.map((member) => (
                                <MenuItem key={member.employee_id} value={member.employee_id}>
                                    {member.name} ({member.utilization_percent}% capacity)
                                </MenuItem>
                            ))}
                        </Select>
                    </FormControl>

                    <Grid container spacing={2}>
                        <Grid item xs={6}>
                            <FormControl fullWidth>
                                <InputLabel>Priority</InputLabel>
                                <Select
                                    value={assignmentForm.priority}
                                    onChange={(e) => setAssignmentForm({ ...assignmentForm, priority: e.target.value as any })}
                                >
                                    <MenuItem value="low">Low</MenuItem>
                                    <MenuItem value="medium">Medium</MenuItem>
                                    <MenuItem value="high">High</MenuItem>
                                    <MenuItem value="urgent">Urgent</MenuItem>
                                </Select>
                            </FormControl>
                        </Grid>
                        <Grid item xs={6}>
                            <TextField
                                label="Estimated Hours"
                                type="number"
                                fullWidth
                                value={assignmentForm.estimatedHours}
                                onChange={(e) => setAssignmentForm({ ...assignmentForm, estimatedHours: Number(e.target.value) })}
                            />
                        </Grid>
                    </Grid>

                    <TextField
                        label="Due Date"
                        type="date"
                        fullWidth
                        InputLabelProps={{ shrink: true }}
                        value={assignmentForm.dueDate}
                        onChange={(e) => setAssignmentForm({ ...assignmentForm, dueDate: e.target.value })}
                    />

                    <TextField
                        label="Project Name (Optional)"
                        fullWidth
                        value={assignmentForm.projectName}
                        onChange={(e) => setAssignmentForm({ ...assignmentForm, projectName: e.target.value })}
                    />
                </Stack>
            </DialogContent>
            <DialogActions>
                <Button onClick={() => setAssignmentDialogOpen(false)}>Cancel</Button>
                <Button
                    variant="contained"
                    onClick={handleAssignWork}
                    disabled={!assignmentForm.title || !assignmentForm.description || !assignmentForm.assigneeId}
                >
                    Assign Work
                </Button>
            </DialogActions>
        </Dialog>
    );

    const renderApprovalDialog = () => (
        <Dialog open={approvalDialogOpen} onClose={() => setApprovalDialogOpen(false)} maxWidth="sm" fullWidth>
            <DialogTitle>
                {approvalAction === 'approve' ? '✅ Approve Request' : '❌ Reject Request'}
            </DialogTitle>
            <DialogContent>
                <Stack spacing={2} mt={1}>
                    {selectedApproval && (
                        <Alert severity={approvalAction === 'approve' ? 'success' : 'error'}>
                            You are about to {approvalAction} the {selectedApproval.request_type} request from {selectedApproval.requester_name}.
                        </Alert>
                    )}

                    <TextField
                        label={approvalAction === 'approve' ? 'Comments (min 10 chars)' : 'Rejection Reason (min 10 chars)'}
                        fullWidth
                        multiline
                        rows={4}
                        value={approvalComment}
                        onChange={(e) => setApprovalComment(e.target.value)}
                        required
                        error={approvalComment.length > 0 && approvalComment.length < 10}
                        helperText={approvalComment.length > 0 && approvalComment.length < 10 ? 'Minimum 10 characters required' : ''}
                    />
                </Stack>
            </DialogContent>
            <DialogActions>
                <Button onClick={() => setApprovalDialogOpen(false)}>Cancel</Button>
                <Button
                    variant="contained"
                    color={approvalAction === 'approve' ? 'success' : 'error'}
                    onClick={handleApprovalAction}
                    disabled={approvalComment.length < 10}
                >
                    {approvalAction === 'approve' ? 'Approve' : 'Reject'}
                </Button>
            </DialogActions>
        </Dialog>
    );

    // ============================================================================
    // MAIN RENDER
    // ============================================================================

    return (
        <Box sx={{ p: 3 }}>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
                <Typography variant="h4" fontWeight="bold">
                    Manager Dashboard
                </Typography>
                <Box display="flex" gap={2}>
                    <Chip
                        icon={<WarningIcon />}
                        label={`${teamWorkload.filter(m => m.capacity_status === 'overloaded').length} Overloaded`}
                        color="error"
                    />
                    <Chip
                        icon={<TrendingUpIcon />}
                        label={`${teamWorkload.filter(m => m.capacity_status === 'available').length} Available`}
                        color="success"
                    />
                    <Button
                        variant="outlined"
                        startIcon={<RefreshIcon />}
                        onClick={fetchDashboardData}
                    >
                        Refresh
                    </Button>
                </Box>
            </Box>

            <Grid container spacing={3}>
                {/* Top Row: Team Workload */}
                <Grid item xs={12}>
                    {renderTeamHierarchy()}
                </Grid>

                {/* Second Row: Approvals & Assignments */}
                <Grid item xs={12} md={8}>
                    {renderApprovalQueue()}
                </Grid>
                <Grid item xs={12} md={4}>
                    {renderWorkAssignmentForm()}
                    <Box mt={2}>
                        {renderNotifications()}
                    </Box>
                </Grid>

                {/* Third Row: Analytics */}
                <Grid item xs={12}>
                    {renderTeamAnalytics()}
                </Grid>
            </Grid>

            {/* Dialogs */}
            {renderAssignmentDialog()}
            {renderApprovalDialog()}
        </Box>
    );
};

export default ManagerDashboard;
