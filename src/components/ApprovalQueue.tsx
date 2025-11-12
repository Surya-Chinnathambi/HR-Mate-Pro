import React, { useState, useEffect } from 'react';
import {
    Box,
    Grid,
    Card,
    CardContent,
    Typography,
    Button,
    TextField,
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
    Paper,
    Divider,
    Stack,
    Checkbox,
    FormControlLabel,
    Radio,
    RadioGroup,
    FormControl,
    FormLabel,
    Stepper,
    Step,
    StepLabel,
    StepContent,
    Accordion,
    AccordionSummary,
    AccordionDetails,
    Slider,
    Autocomplete,
} from '@mui/material';
import {
    CheckCircle as ApproveIcon,
    Cancel as RejectIcon,
    ExpandMore as ExpandMoreIcon,
    FilterList as FilterIcon,
    Refresh as RefreshIcon,
    AccessTime as TimeIcon,
    Warning as WarningIcon,
    TrendingUp as TrendingUpIcon,
    TrendingDown as TrendingDownIcon,
    Attachment as AttachmentIcon,
    Download as DownloadIcon,
} from '@mui/icons-material';
import {
    BarChart,
    Bar,
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip as RechartsTooltip,
    Legend,
    ResponsiveContainer,
} from 'recharts';
import { format, formatDistanceToNow, parseISO } from 'date-fns';
import apiClient from '../api/client';

// ============================================================================
// TYPE DEFINITIONS
// ============================================================================

interface ApprovalRequest {
    id: number;
    request_type: string;
    requester_id: number;
    requester_name: string;
    priority: string;
    current_level: number;
    total_levels: number;
    status: string;
    assigned_at: string;
    time_pending_hours: number;
    sla_hours: number;
    amount?: number;
    days_requested?: number;
    reason?: string;
    approval_steps: ApprovalStep[];
    attachments?: string[];
}

interface ApprovalStep {
    step_id: number;
    level: number;
    approver_id: number;
    approver_name: string;
    status: 'pending' | 'approved' | 'rejected' | 'escalated';
    assigned_at: string;
    reviewed_at?: string;
    comments?: string;
}

interface ApprovalMetrics {
    total_pending: number;
    avg_response_time_hours: number;
    approval_rate_percent: number;
    escalation_count: number;
    by_request_type: Record<string, {
        total: number;
        approved: number;
        rejected: number;
        pending: number;
    }>;
    response_time_trend: Array<{
        date: string;
        avg_hours: number;
    }>;
}

interface FilterState {
    status: string;
    requestTypes: string[];
    dateFrom: string;
    dateTo: string;
    requester: string;
    amountRange: [number, number];
    daysRange: [number, number];
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

const ApprovalQueue: React.FC = () => {
    // Tab State
    const [activeTab, setActiveTab] = useState(0);

    // Data State
    const [approvals, setApprovals] = useState<ApprovalRequest[]>([]);
    const [metrics, setMetrics] = useState<ApprovalMetrics | null>(null);
    const [loading, setLoading] = useState(true);
    const [expandedApprovals, setExpandedApprovals] = useState<Set<number>>(new Set());

    // Selection State
    const [selectedApprovals, setSelectedApprovals] = useState<Set<number>>(new Set());
    const [selectAll, setSelectAll] = useState(false);

    // Dialog State
    const [actionDialogOpen, setActionDialogOpen] = useState(false);
    const [actionType, setActionType] = useState<'approve' | 'reject'>('approve');
    const [selectedApproval, setSelectedApproval] = useState<ApprovalRequest | null>(null);
    const [actionComment, setActionComment] = useState('');
    const [isBulkAction, setIsBulkAction] = useState(false);

    // Filter State
    const [filters, setFilters] = useState<FilterState>({
        status: 'all',
        requestTypes: [],
        dateFrom: '',
        dateTo: '',
        requester: '',
        amountRange: [0, 10000],
        daysRange: [0, 30],
    });
    const [showFilters, setShowFilters] = useState(false);

    // ============================================================================
    // DATA FETCHING
    // ============================================================================

    useEffect(() => {
        fetchApprovals();
        fetchMetrics();
    }, [activeTab, filters]);

    const fetchApprovals = async () => {
        try {
            setLoading(true);
            const params: any = {};

            // Filter by tab
            if (activeTab === 1) params.request_type = 'LEAVE';
            if (activeTab === 2) params.request_type = 'EXPENSE';
            if (activeTab === 3) params.request_type = 'OVERTIME';

            // Apply filters
            if (filters.status !== 'all') params.status = filters.status;
            if (filters.dateFrom) params.date_from = filters.dateFrom;
            if (filters.dateTo) params.date_to = filters.dateTo;
            if (filters.requester) params.requester_name = filters.requester;

            const response = await apiClient.get('/approvals/pending', { params });
            setApprovals(response.data || []);
        } catch (error) {
            console.error('Error fetching approvals:', error);
        } finally {
            setLoading(false);
        }
    };

    const fetchMetrics = async () => {
        try {
            const response = await apiClient.get('/approvals/metrics');
            setMetrics(response.data);
        } catch (error) {
            console.error('Error fetching metrics:', error);
        }
    };

    const handleApprove = async () => {
        if (!actionComment || actionComment.length < 10) return;

        try {
            if (isBulkAction) {
                // Bulk approve
                await Promise.all(
                    Array.from(selectedApprovals).map((id) =>
                        apiClient.post(`/approvals/${id}/approve`, { comments: actionComment })
                    )
                );
                setSelectedApprovals(new Set());
            } else if (selectedApproval) {
                // Single approve
                await apiClient.post(`/approvals/${selectedApproval.id}/approve`, {
                    comments: actionComment,
                });
            }

            setActionDialogOpen(false);
            setActionComment('');
            fetchApprovals();
            fetchMetrics();
        } catch (error) {
            console.error('Error approving:', error);
        }
    };

    const handleReject = async () => {
        if (!actionComment || actionComment.length < 20) return;

        try {
            if (isBulkAction) {
                // Bulk reject
                await Promise.all(
                    Array.from(selectedApprovals).map((id) =>
                        apiClient.post(`/approvals/${id}/reject`, { comments: actionComment })
                    )
                );
                setSelectedApprovals(new Set());
            } else if (selectedApproval) {
                // Single reject
                await apiClient.post(`/approvals/${selectedApproval.id}/reject`, {
                    comments: actionComment,
                });
            }

            setActionDialogOpen(false);
            setActionComment('');
            fetchApprovals();
            fetchMetrics();
        } catch (error) {
            console.error('Error rejecting:', error);
        }
    };

    const openApproveDialog = (approval: ApprovalRequest | null, bulk = false) => {
        setSelectedApproval(approval);
        setActionType('approve');
        setIsBulkAction(bulk);
        setActionDialogOpen(true);
    };

    const openRejectDialog = (approval: ApprovalRequest | null, bulk = false) => {
        setSelectedApproval(approval);
        setActionType('reject');
        setIsBulkAction(bulk);
        setActionDialogOpen(true);
    };

    const toggleExpanded = (id: number) => {
        const newExpanded = new Set(expandedApprovals);
        if (newExpanded.has(id)) {
            newExpanded.delete(id);
        } else {
            newExpanded.add(id);
        }
        setExpandedApprovals(newExpanded);
    };

    const toggleSelection = (id: number) => {
        const newSelected = new Set(selectedApprovals);
        if (newSelected.has(id)) {
            newSelected.delete(id);
        } else {
            newSelected.add(id);
        }
        setSelectedApprovals(newSelected);
    };

    const handleSelectAll = () => {
        if (selectAll) {
            setSelectedApprovals(new Set());
        } else {
            setSelectedApprovals(new Set(approvals.map((a) => a.id)));
        }
        setSelectAll(!selectAll);
    };

    // ============================================================================
    // UTILITY FUNCTIONS
    // ============================================================================

    const getPriorityColor = (priority: string): string => {
        const colors: Record<string, string> = {
            urgent: '#d32f2f',
            high: '#f57c00',
            medium: '#1976d2',
            low: '#388e3c',
        };
        return colors[priority] || '#757575';
    };

    const getRequestTypeLabel = (type: string): string => {
        return type.replace('_', ' ').toUpperCase();
    };

    const getSLAStatus = (timePending: number, slaHours: number) => {
        const percentage = (timePending / slaHours) * 100;
        if (percentage >= 90) return { color: 'error', label: 'Critical', icon: <WarningIcon /> };
        if (percentage >= 70) return { color: 'warning', label: 'Warning', icon: <TimeIcon /> };
        return { color: 'success', label: 'On Track', icon: <TimeIcon /> };
    };

    const getFilteredApprovals = (): ApprovalRequest[] => {
        return approvals.filter((approval) => {
            // Status filter
            if (filters.status !== 'all' && approval.status !== filters.status) return false;

            // Request type filter
            if (filters.requestTypes.length > 0 && !filters.requestTypes.includes(approval.request_type)) {
                return false;
            }

            // Amount range filter
            if (approval.amount) {
                if (approval.amount < filters.amountRange[0] || approval.amount > filters.amountRange[1]) {
                    return false;
                }
            }

            // Days range filter
            if (approval.days_requested) {
                if (
                    approval.days_requested < filters.daysRange[0] ||
                    approval.days_requested > filters.daysRange[1]
                ) {
                    return false;
                }
            }

            return true;
        });
    };

    // ============================================================================
    // RENDER: METRICS DASHBOARD
    // ============================================================================

    const renderMetrics = () => {
        if (!metrics) return null;

        const approvalRateTrend = metrics.approval_rate_percent >= 80 ? 'up' : 'down';
        const responseTimeTrend = metrics.avg_response_time_hours <= 24 ? 'down' : 'up';

        return (
            <Grid container spacing={2} mb={3}>
                {/* Metric Cards */}
                <Grid size={{ xs: 12, md: 3 }}>
                    <Card>
                        <CardContent>
                            <Typography variant="caption" color="text.secondary">
                                Total Pending
                            </Typography>
                            <Typography variant="h4" color="primary">
                                {metrics.total_pending}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                                Awaiting your action
                            </Typography>
                        </CardContent>
                    </Card>
                </Grid>

                <Grid size={{ xs: 12, md: 3 }}>
                    <Card>
                        <CardContent>
                            <Typography variant="caption" color="text.secondary">
                                Avg Response Time
                            </Typography>
                            <Box display="flex" alignItems="center" gap={1}>
                                <Typography variant="h4">
                                    {Math.round(metrics.avg_response_time_hours)}h
                                </Typography>
                                {responseTimeTrend === 'down' ? (
                                    <TrendingDownIcon color="success" />
                                ) : (
                                    <TrendingUpIcon color="error" />
                                )}
                            </Box>
                            <Typography variant="caption" color="text.secondary">
                                Last 30 days
                            </Typography>
                        </CardContent>
                    </Card>
                </Grid>

                <Grid size={{ xs: 12, md: 3 }}>
                    <Card>
                        <CardContent>
                            <Typography variant="caption" color="text.secondary">
                                Approval Rate
                            </Typography>
                            <Box display="flex" alignItems="center" gap={1}>
                                <Typography variant="h4" color="success.main">
                                    {Math.round(metrics.approval_rate_percent)}%
                                </Typography>
                                {approvalRateTrend === 'up' ? (
                                    <TrendingUpIcon color="success" />
                                ) : (
                                    <TrendingDownIcon color="error" />
                                )}
                            </Box>
                            <Typography variant="caption" color="text.secondary">
                                Approved requests
                            </Typography>
                        </CardContent>
                    </Card>
                </Grid>

                <Grid size={{ xs: 12, md: 3 }}>
                    <Card>
                        <CardContent>
                            <Typography variant="caption" color="text.secondary">
                                Escalations
                            </Typography>
                            <Typography variant="h4" color="error.main">
                                {metrics.escalation_count}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                                SLA breached
                            </Typography>
                        </CardContent>
                    </Card>
                </Grid>

                {/* Charts */}
                <Grid size={{ xs: 12, md: 6 }}>
                    <Card>
                        <CardContent>
                            <Typography variant="subtitle2" gutterBottom fontWeight="bold">
                                Approvals by Type
                            </Typography>
                            <ResponsiveContainer width="100%" height={200}>
                                <BarChart
                                    data={Object.entries(metrics.by_request_type).map(([type, data]) => ({
                                        type: type.replace('_', ' '),
                                        approved: data.approved,
                                        rejected: data.rejected,
                                        pending: data.pending,
                                    }))}
                                >
                                    <CartesianGrid strokeDasharray="3 3" />
                                    <XAxis dataKey="type" />
                                    <YAxis />
                                    <RechartsTooltip />
                                    <Legend />
                                    <Bar dataKey="approved" fill="#4caf50" stackId="a" />
                                    <Bar dataKey="rejected" fill="#f44336" stackId="a" />
                                    <Bar dataKey="pending" fill="#ff9800" stackId="a" />
                                </BarChart>
                            </ResponsiveContainer>
                        </CardContent>
                    </Card>
                </Grid>

                <Grid size={{ xs: 12, md: 6 }}>
                    <Card>
                        <CardContent>
                            <Typography variant="subtitle2" gutterBottom fontWeight="bold">
                                Response Time Trend
                            </Typography>
                            <ResponsiveContainer width="100%" height={200}>
                                <LineChart data={metrics.response_time_trend}>
                                    <CartesianGrid strokeDasharray="3 3" />
                                    <XAxis dataKey="date" />
                                    <YAxis />
                                    <RechartsTooltip />
                                    <Legend />
                                    <Line
                                        type="monotone"
                                        dataKey="avg_hours"
                                        stroke="#1976d2"
                                        name="Avg Hours"
                                    />
                                </LineChart>
                            </ResponsiveContainer>
                        </CardContent>
                    </Card>
                </Grid>
            </Grid>
        );
    };

    // ============================================================================
    // RENDER: FILTERS
    // ============================================================================

    const renderFilters = () => (
        <Accordion expanded={showFilters} onChange={() => setShowFilters(!showFilters)}>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Box display="flex" alignItems="center" gap={1}>
                    <FilterIcon />
                    <Typography>Filters & Search</Typography>
                    {filters.requestTypes.length > 0 && (
                        <Chip label={`${filters.requestTypes.length} types`} size="small" color="primary" />
                    )}
                </Box>
            </AccordionSummary>
            <AccordionDetails>
                <Grid container spacing={3}>
                    {/* Status Filter */}
                    <Grid size={{ xs: 12, md: 3 }}>
                        <FormControl component="fieldset">
                            <FormLabel component="legend">Status</FormLabel>
                            <RadioGroup
                                value={filters.status}
                                onChange={(e) => setFilters({ ...filters, status: e.target.value })}
                            >
                                <FormControlLabel value="all" control={<Radio size="small" />} label="All" />
                                <FormControlLabel
                                    value="pending"
                                    control={<Radio size="small" />}
                                    label="Pending"
                                />
                                <FormControlLabel
                                    value="approved"
                                    control={<Radio size="small" />}
                                    label="Approved"
                                />
                                <FormControlLabel
                                    value="rejected"
                                    control={<Radio size="small" />}
                                    label="Rejected"
                                />
                            </RadioGroup>
                        </FormControl>
                    </Grid>

                    {/* Request Type Filter */}
                    <Grid size={{ xs: 12, md: 3 }}>
                        <FormControl component="fieldset">
                            <FormLabel component="legend">Request Type</FormLabel>
                            <Stack spacing={0.5}>
                                {['LEAVE', 'EXPENSE', 'OVERTIME', 'WFH'].map((type) => (
                                    <FormControlLabel
                                        key={type}
                                        control={
                                            <Checkbox
                                                size="small"
                                                checked={filters.requestTypes.includes(type)}
                                                onChange={(e) => {
                                                    if (e.target.checked) {
                                                        setFilters({
                                                            ...filters,
                                                            requestTypes: [...filters.requestTypes, type],
                                                        });
                                                    } else {
                                                        setFilters({
                                                            ...filters,
                                                            requestTypes: filters.requestTypes.filter((t) => t !== type),
                                                        });
                                                    }
                                                }}
                                            />
                                        }
                                        label={getRequestTypeLabel(type)}
                                    />
                                ))}
                            </Stack>
                        </FormControl>
                    </Grid>

                    {/* Date Range */}
                    <Grid size={{ xs: 12, md: 3 }}>
                        <FormLabel component="legend">Date Range</FormLabel>
                        <Stack spacing={1} mt={1}>
                            <TextField
                                label="From"
                                type="date"
                                size="small"
                                fullWidth
                                InputLabelProps={{ shrink: true }}
                                value={filters.dateFrom}
                                onChange={(e) => setFilters({ ...filters, dateFrom: e.target.value })}
                            />
                            <TextField
                                label="To"
                                type="date"
                                size="small"
                                fullWidth
                                InputLabelProps={{ shrink: true }}
                                value={filters.dateTo}
                                onChange={(e) => setFilters({ ...filters, dateTo: e.target.value })}
                            />
                        </Stack>
                    </Grid>

                    {/* Amount/Days Range */}
                    <Grid size={{ xs: 12, md: 3 }}>
                        <FormLabel component="legend">Ranges</FormLabel>
                        <Stack spacing={2} mt={1}>
                            <Box>
                                <Typography variant="caption" gutterBottom>
                                    Amount: ${filters.amountRange[0]} - ${filters.amountRange[1]}
                                </Typography>
                                <Slider
                                    value={filters.amountRange}
                                    onChange={(_, value) =>
                                        setFilters({ ...filters, amountRange: value as [number, number] })
                                    }
                                    valueLabelDisplay="auto"
                                    min={0}
                                    max={10000}
                                    step={100}
                                />
                            </Box>
                            <Box>
                                <Typography variant="caption" gutterBottom>
                                    Days: {filters.daysRange[0]} - {filters.daysRange[1]}
                                </Typography>
                                <Slider
                                    value={filters.daysRange}
                                    onChange={(_, value) =>
                                        setFilters({ ...filters, daysRange: value as [number, number] })
                                    }
                                    valueLabelDisplay="auto"
                                    min={0}
                                    max={30}
                                    step={1}
                                />
                            </Box>
                        </Stack>
                    </Grid>

                    {/* Actions */}
                    <Grid size={{ xs: 12 }}>
                        <Button
                            onClick={() =>
                                setFilters({
                                    status: 'all',
                                    requestTypes: [],
                                    dateFrom: '',
                                    dateTo: '',
                                    requester: '',
                                    amountRange: [0, 10000],
                                    daysRange: [0, 30],
                                })
                            }
                        >
                            Clear All Filters
                        </Button>
                    </Grid>
                </Grid>
            </AccordionDetails>
        </Accordion>
    );

    // ============================================================================
    // RENDER: APPROVAL LIST
    // ============================================================================

    const renderApprovalList = () => {
        const filteredApprovals = getFilteredApprovals();

        if (loading) {
            return (
                <Box display="flex" justifyContent="center" p={4}>
                    <CircularProgress />
                </Box>
            );
        }

        if (filteredApprovals.length === 0) {
            return (
                <Alert severity="success">
                    🎉 No pending approvals! You're all caught up.
                </Alert>
            );
        }

        return (
            <Stack spacing={2}>
                {filteredApprovals.map((approval) => {
                    const isExpanded = expandedApprovals.has(approval.id);
                    const isSelected = selectedApprovals.has(approval.id);
                    const slaStatus = getSLAStatus(approval.time_pending_hours, approval.sla_hours);

                    return (
                        <Card
                            key={approval.id}
                            sx={{
                                border: isSelected ? '2px solid' : '1px solid',
                                borderColor: isSelected ? 'primary.main' : 'divider',
                            }}
                        >
                            <CardContent>
                                {/* Header */}
                                <Box display="flex" alignItems="start" gap={2}>
                                    <Checkbox
                                        checked={isSelected}
                                        onChange={() => toggleSelection(approval.id)}
                                    />
                                    <Avatar sx={{ width: 48, height: 48 }}>
                                        {approval.requester_name.charAt(0)}
                                    </Avatar>
                                    <Box flex={1}>
                                        <Typography variant="h6" gutterBottom>
                                            {approval.requester_name}
                                        </Typography>
                                        <Box display="flex" flexWrap="wrap" gap={1}>
                                            <Chip
                                                label={getRequestTypeLabel(approval.request_type)}
                                                size="small"
                                                variant="outlined"
                                            />
                                            <Chip
                                                label={approval.priority.toUpperCase()}
                                                size="small"
                                                sx={{
                                                    bgcolor: getPriorityColor(approval.priority),
                                                    color: 'white',
                                                }}
                                            />
                                            {approval.amount && (
                                                <Chip label={`$${approval.amount}`} size="small" color="primary" />
                                            )}
                                            {approval.days_requested && (
                                                <Chip
                                                    label={`${approval.days_requested} days`}
                                                    size="small"
                                                    color="primary"
                                                />
                                            )}
                                        </Box>
                                    </Box>
                                    <Box textAlign="right">
                                        <Typography variant="caption" color="text.secondary" display="block">
                                            {formatDistanceToNow(parseISO(approval.assigned_at))} ago
                                        </Typography>
                                        <Chip
                                            icon={slaStatus.icon}
                                            label={`${Math.round(approval.time_pending_hours)}h / ${approval.sla_hours}h`}
                                            size="small"
                                            color={slaStatus.color as any}
                                            sx={{ mt: 0.5 }}
                                        />
                                    </Box>
                                </Box>

                                {/* Summary */}
                                <Box mt={2} mb={2}>
                                    <Typography variant="body2">
                                        <strong>Summary:</strong>{' '}
                                        {approval.request_type === 'LEAVE'
                                            ? `${approval.days_requested} days leave request`
                                            : approval.request_type === 'EXPENSE'
                                                ? `$${approval.amount} expense claim`
                                                : approval.request_type === 'OVERTIME'
                                                    ? `${approval.days_requested} hours overtime`
                                                    : 'Request details'}
                                    </Typography>
                                    {approval.reason && (
                                        <Typography variant="body2" color="text.secondary" mt={0.5}>
                                            <strong>Reason:</strong> {approval.reason}
                                        </Typography>
                                    )}
                                </Box>

                                {/* Progress */}
                                <Box mb={2}>
                                    <Box display="flex" justifyContent="space-between" mb={0.5}>
                                        <Typography variant="caption">
                                            Approval Level {approval.current_level} / {approval.total_levels}
                                        </Typography>
                                    </Box>
                                    <Box display="flex" gap={1}>
                                        {approval.approval_steps.map((step) => (
                                            <Chip
                                                key={step.step_id}
                                                label={`L${step.level}`}
                                                size="small"
                                                color={
                                                    step.status === 'approved'
                                                        ? 'success'
                                                        : step.status === 'pending'
                                                            ? 'warning'
                                                            : 'error'
                                                }
                                            />
                                        ))}
                                    </Box>
                                </Box>

                                {/* Actions */}
                                <Box display="flex" gap={1}>
                                    <Button
                                        variant="contained"
                                        color="success"
                                        startIcon={<ApproveIcon />}
                                        onClick={() => openApproveDialog(approval)}
                                    >
                                        Approve
                                    </Button>
                                    <Button
                                        variant="outlined"
                                        color="error"
                                        startIcon={<RejectIcon />}
                                        onClick={() => openRejectDialog(approval)}
                                    >
                                        Reject
                                    </Button>
                                    <Button
                                        variant="text"
                                        endIcon={isExpanded ? <ExpandMoreIcon /> : <ExpandMoreIcon />}
                                        onClick={() => toggleExpanded(approval.id)}
                                    >
                                        {isExpanded ? 'Less' : 'More'} Details
                                    </Button>
                                </Box>

                                {/* Expanded Details */}
                                {isExpanded && (
                                    <Box mt={3}>
                                        <Divider sx={{ mb: 2 }} />
                                        <Typography variant="subtitle2" gutterBottom fontWeight="bold">
                                            Approval Chain
                                        </Typography>
                                        <Stepper orientation="vertical" activeStep={approval.current_level - 1}>
                                            {approval.approval_steps.map((step) => (
                                                <Step key={step.step_id} completed={step.status === 'approved'}>
                                                    <StepLabel
                                                        error={step.status === 'rejected'}
                                                        StepIconProps={{
                                                            sx: {
                                                                color:
                                                                    step.status === 'approved'
                                                                        ? 'success.main'
                                                                        : step.status === 'rejected'
                                                                            ? 'error.main'
                                                                            : undefined,
                                                            },
                                                        }}
                                                    >
                                                        <Typography variant="body2">
                                                            <strong>Level {step.level}:</strong> {step.approver_name}
                                                        </Typography>
                                                    </StepLabel>
                                                    <StepContent>
                                                        <Typography variant="caption" color="text.secondary">
                                                            Status: {step.status.toUpperCase()}
                                                        </Typography>
                                                        {step.reviewed_at && (
                                                            <Typography variant="caption" color="text.secondary" display="block">
                                                                Reviewed: {format(parseISO(step.reviewed_at), 'MMM dd, yyyy HH:mm')}
                                                            </Typography>
                                                        )}
                                                        {step.comments && (
                                                            <Paper sx={{ p: 1, mt: 1, bgcolor: 'grey.50' }}>
                                                                <Typography variant="body2">{step.comments}</Typography>
                                                            </Paper>
                                                        )}
                                                    </StepContent>
                                                </Step>
                                            ))}
                                        </Stepper>

                                        {approval.attachments && approval.attachments.length > 0 && (
                                            <Box mt={2}>
                                                <Typography variant="subtitle2" gutterBottom fontWeight="bold">
                                                    <AttachmentIcon fontSize="small" sx={{ mr: 1, verticalAlign: 'middle' }} />
                                                    Attachments ({approval.attachments.length})
                                                </Typography>
                                                <Stack direction="row" spacing={1}>
                                                    {approval.attachments.map((attachment, idx) => (
                                                        <Button
                                                            key={idx}
                                                            variant="outlined"
                                                            size="small"
                                                            startIcon={<DownloadIcon />}
                                                        >
                                                            Document {idx + 1}
                                                        </Button>
                                                    ))}
                                                </Stack>
                                            </Box>
                                        )}
                                    </Box>
                                )}
                            </CardContent>
                        </Card>
                    );
                })}
            </Stack>
        );
    };

    // ============================================================================
    // RENDER: ACTION DIALOG
    // ============================================================================

    const renderActionDialog = () => {
        const minLength = actionType === 'approve' ? 10 : 20;
        const isValid = actionComment.length >= minLength;

        return (
            <Dialog open={actionDialogOpen} onClose={() => setActionDialogOpen(false)} maxWidth="sm" fullWidth>
                <DialogTitle>
                    {actionType === 'approve' ? '✅ Approve Request' : '❌ Reject Request'}
                </DialogTitle>
                <DialogContent>
                    <Stack spacing={2} mt={1}>
                        {isBulkAction ? (
                            <Alert severity={actionType === 'approve' ? 'success' : 'error'}>
                                You are about to {actionType} {selectedApprovals.size} requests with the same comment.
                            </Alert>
                        ) : selectedApproval ? (
                            <Alert severity={actionType === 'approve' ? 'success' : 'error'}>
                                You are about to {actionType} the {selectedApproval.request_type} request from{' '}
                                {selectedApproval.requester_name}.
                            </Alert>
                        ) : null}

                        <TextField
                            label={
                                actionType === 'approve'
                                    ? `Comments (min ${minLength} chars)`
                                    : `Rejection Reason (min ${minLength} chars)`
                            }
                            fullWidth
                            multiline
                            rows={5}
                            value={actionComment}
                            onChange={(e) => setActionComment(e.target.value)}
                            required
                            error={actionComment.length > 0 && !isValid}
                            helperText={
                                actionComment.length > 0 && !isValid
                                    ? `Minimum ${minLength} characters required`
                                    : `${actionComment.length} / ${minLength}`
                            }
                            placeholder={
                                actionType === 'approve'
                                    ? 'Add your approval comments and any suggestions...'
                                    : 'Please explain in detail why this request is being rejected...'
                            }
                        />

                        {actionType === 'reject' && (
                            <Alert severity="warning">
                                <strong>Warning:</strong> Rejecting this request will send it back to the requester.
                                Please provide a clear and detailed reason.
                            </Alert>
                        )}
                    </Stack>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setActionDialogOpen(false)}>Cancel</Button>
                    <Button
                        variant="contained"
                        color={actionType === 'approve' ? 'success' : 'error'}
                        onClick={actionType === 'approve' ? handleApprove : handleReject}
                        disabled={!isValid}
                    >
                        {actionType === 'approve' ? 'Approve' : 'Reject'}
                        {isBulkAction && ` (${selectedApprovals.size})`}
                    </Button>
                </DialogActions>
            </Dialog>
        );
    };

    // ============================================================================
    // MAIN RENDER
    // ============================================================================

    return (
        <Box sx={{ p: 3 }}>
            {/* Header */}
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
                <Typography variant="h4" fontWeight="bold">
                    Approval Queue
                </Typography>
                <Box display="flex" gap={2}>
                    {selectedApprovals.size > 0 && (
                        <>
                            <Button
                                variant="contained"
                                color="success"
                                startIcon={<ApproveIcon />}
                                onClick={() => openApproveDialog(null, true)}
                            >
                                Bulk Approve ({selectedApprovals.size})
                            </Button>
                            <Button
                                variant="outlined"
                                color="error"
                                startIcon={<RejectIcon />}
                                onClick={() => openRejectDialog(null, true)}
                            >
                                Bulk Reject ({selectedApprovals.size})
                            </Button>
                            <Button onClick={() => setSelectedApprovals(new Set())}>Clear Selection</Button>
                        </>
                    )}
                    <Button variant="outlined" startIcon={<RefreshIcon />} onClick={fetchApprovals}>
                        Refresh
                    </Button>
                </Box>
            </Box>

            {/* Metrics Dashboard */}
            {renderMetrics()}

            {/* Tabs */}
            <Box mb={2}>
                <Tabs value={activeTab} onChange={(_, newValue) => setActiveTab(newValue)}>
                    <Tab label="All Requests" />
                    <Tab label="Leave Requests" />
                    <Tab label="Expense Claims" />
                    <Tab label="Overtime Requests" />
                </Tabs>
            </Box>

            {/* Filters */}
            <Box mb={2}>{renderFilters()}</Box>

            {/* Bulk Actions Bar */}
            {approvals.length > 0 && (
                <Box mb={2} display="flex" alignItems="center" gap={2}>
                    <FormControlLabel
                        control={<Checkbox checked={selectAll} onChange={handleSelectAll} />}
                        label="Select All"
                    />
                    {selectedApprovals.size > 0 && (
                        <Chip label={`${selectedApprovals.size} selected`} color="primary" />
                    )}
                </Box>
            )}

            {/* Approval List */}
            {renderApprovalList()}

            {/* Action Dialog */}
            {renderActionDialog()}
        </Box>
    );
};

export default ApprovalQueue;
