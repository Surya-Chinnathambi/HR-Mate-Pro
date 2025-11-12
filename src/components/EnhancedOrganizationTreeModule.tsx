import React, { useState, useEffect } from 'react';
import {
    Users,
    Building,
    ChevronRight,
    ChevronDown,
    User,
    Mail,
    Phone,
    Briefcase,
    MapPin,
    Search,
    Filter,
    Loader,
    Download
} from 'lucide-react';
import toast from 'react-hot-toast';
import { api } from '../api/client';

interface Employee {
    employee_id: string;
    first_name: string;
    last_name: string;
    email: string;
    phone?: string;
    position: string;
    department: string;
    role: string;
    manager_id?: string;
    manager_name?: string;
    location?: string;
    avatar_url?: string;
    subordinates?: Employee[];
}

interface Department {
    department_id: string;
    name: string;
    head_id?: string;
    head_name?: string;
    employee_count: number;
    employees: Employee[];
}

const EnhancedOrganizationTreeModule: React.FC = () => {
    const [view, setView] = useState<'tree' | 'directory' | 'departments'>('tree');
    const [employees, setEmployees] = useState<Employee[]>([]);
    const [departments, setDepartments] = useState<Department[]>([]);
    const [orgTree, setOrgTree] = useState<Employee[]>([]);
    const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set());
    const [selectedEmployee, setSelectedEmployee] = useState<Employee | null>(null);
    const [loading, setLoading] = useState(false);
    const [searchQuery, setSearchQuery] = useState('');
    const [filterDepartment, setFilterDepartment] = useState<string>('all');

    // Load employees
    const loadEmployees = async () => {
        try {
            setLoading(true);
            const response = await api.employees.getAll();
            setEmployees(response.data || []);
        } catch (error: any) {
            console.error('Error loading employees:', error);
            toast.error('Failed to load employees');
        } finally {
            setLoading(false);
        }
    };

    // Load departments
    const loadDepartments = async () => {
        try {
            setLoading(true);
            const response = await api.organization.getDepartments();
            setDepartments(response.data || []);
        } catch (error: any) {
            console.error('Error loading departments:', error);
            toast.error('Failed to load departments');
        } finally {
            setLoading(false);
        }
    };

    // Load organization tree
    const loadOrgTree = async () => {
        try {
            setLoading(true);
            const response = await api.organization.getTree();
            setOrgTree(response.data || []);
        } catch (error: any) {
            console.error('Error loading org tree:', error);
            toast.error('Failed to load organization tree');
        } finally {
            setLoading(false);
        }
    };

    // Initial load
    useEffect(() => {
        loadEmployees();
        loadDepartments();
        loadOrgTree();
    }, []);

    // Toggle node expansion
    const toggleNode = (employeeId: string) => {
        const newExpanded = new Set(expandedNodes);
        if (newExpanded.has(employeeId)) {
            newExpanded.delete(employeeId);
        } else {
            newExpanded.add(employeeId);
        }
        setExpandedNodes(newExpanded);
    };

    // Render tree node
    const renderTreeNode = (employee: Employee, level: number = 0) => {
        const hasSubordinates = employee.subordinates && employee.subordinates.length > 0;
        const isExpanded = expandedNodes.has(employee.employee_id);

        return (
            <div key={employee.employee_id} className="ml-0">
                <div
                    className={`flex items-center gap-2 p-3 rounded-lg cursor-pointer transition-colors ${selectedEmployee?.employee_id === employee.employee_id
                            ? 'bg-blue-50 border border-blue-200'
                            : 'hover:bg-gray-50'
                        }`}
                    style={{ marginLeft: `${level * 24}px` }}
                    onClick={() => setSelectedEmployee(employee)}
                >
                    {hasSubordinates ? (
                        <button
                            onClick={(e) => {
                                e.stopPropagation();
                                toggleNode(employee.employee_id);
                            }}
                            className="p-1 hover:bg-gray-200 rounded"
                        >
                            {isExpanded ? (
                                <ChevronDown className="w-4 h-4 text-gray-600" />
                            ) : (
                                <ChevronRight className="w-4 h-4 text-gray-600" />
                            )}
                        </button>
                    ) : (
                        <div className="w-6" />
                    )}
                    <div className="w-10 h-10 bg-blue-600 text-white rounded-full flex items-center justify-center font-semibold text-sm">
                        {employee.first_name[0]}{employee.last_name[0]}
                    </div>
                    <div className="flex-1">
                        <p className="font-semibold text-gray-900">
                            {employee.first_name} {employee.last_name}
                        </p>
                        <p className="text-sm text-gray-600">{employee.position}</p>
                    </div>
                    <div className="text-right">
                        <p className="text-xs text-gray-600">{employee.department}</p>
                        {hasSubordinates && (
                            <p className="text-xs text-blue-600">{employee.subordinates?.length} reports</p>
                        )}
                    </div>
                </div>
                {hasSubordinates && isExpanded && (
                    <div className="mt-1">
                        {employee.subordinates?.map(sub => renderTreeNode(sub, level + 1))}
                    </div>
                )}
            </div>
        );
    };

    // Filter employees
    const filteredEmployees = employees.filter(emp => {
        const matchesSearch = !searchQuery ||
            `${emp.first_name} ${emp.last_name}`.toLowerCase().includes(searchQuery.toLowerCase()) ||
            emp.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
            emp.position.toLowerCase().includes(searchQuery.toLowerCase());
        const matchesDepartment = filterDepartment === 'all' || emp.department === filterDepartment;
        return matchesSearch && matchesDepartment;
    });

    return (
        <div className="max-w-7xl mx-auto p-4 space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
                        <Building className="w-8 h-8 text-blue-600" />
                        Organization
                    </h1>
                    <p className="text-gray-600 mt-1">Explore company hierarchy and directory</p>
                </div>

                <button
                    onClick={() => toast.success('Export feature coming soon!')}
                    className="p-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
                    title="Export"
                >
                    <Download className="w-5 h-5" />
                </button>
            </div>

            {/* View tabs */}
            <div className="flex gap-2">
                <button
                    onClick={() => setView('tree')}
                    className={`px-4 py-2 rounded-lg transition-colors ${view === 'tree' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                        }`}
                >
                    <Users className="w-5 h-5 inline mr-2" />
                    Org Tree
                </button>
                <button
                    onClick={() => setView('directory')}
                    className={`px-4 py-2 rounded-lg transition-colors ${view === 'directory' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                        }`}
                >
                    <User className="w-5 h-5 inline mr-2" />
                    Directory
                </button>
                <button
                    onClick={() => setView('departments')}
                    className={`px-4 py-2 rounded-lg transition-colors ${view === 'departments' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                        }`}
                >
                    <Building className="w-5 h-5 inline mr-2" />
                    Departments
                </button>
            </div>

            {/* Tree View */}
            {view === 'tree' && (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* Tree navigation */}
                    <div className="lg:col-span-2 bg-white rounded-lg border border-gray-200 p-4">
                        <h2 className="text-xl font-semibold text-gray-900 mb-4">Organization Hierarchy</h2>
                        {loading ? (
                            <div className="flex items-center justify-center p-8">
                                <Loader className="w-6 h-6 animate-spin text-blue-600" />
                            </div>
                        ) : orgTree.length === 0 ? (
                            <div className="text-center p-8 text-gray-500">
                                <Users className="w-12 h-12 mx-auto mb-2 text-gray-400" />
                                <p>No organization data available</p>
                            </div>
                        ) : (
                            <div className="space-y-2 max-h-[600px] overflow-y-auto">
                                {orgTree.map(emp => renderTreeNode(emp))}
                            </div>
                        )}
                    </div>

                    {/* Employee details */}
                    <div className="bg-white rounded-lg border border-gray-200 p-6">
                        {selectedEmployee ? (
                            <div className="space-y-4">
                                <div className="text-center">
                                    <div className="w-20 h-20 bg-blue-600 text-white rounded-full flex items-center justify-center font-bold text-2xl mx-auto mb-3">
                                        {selectedEmployee.first_name[0]}{selectedEmployee.last_name[0]}
                                    </div>
                                    <h3 className="text-xl font-bold text-gray-900">
                                        {selectedEmployee.first_name} {selectedEmployee.last_name}
                                    </h3>
                                    <p className="text-gray-600">{selectedEmployee.position}</p>
                                </div>

                                <div className="space-y-3 border-t border-gray-200 pt-4">
                                    <div className="flex items-center gap-2 text-sm">
                                        <Mail className="w-5 h-5 text-gray-400" />
                                        <a href={`mailto:${selectedEmployee.email}`} className="text-blue-600 hover:text-blue-700">
                                            {selectedEmployee.email}
                                        </a>
                                    </div>
                                    {selectedEmployee.phone && (
                                        <div className="flex items-center gap-2 text-sm">
                                            <Phone className="w-5 h-5 text-gray-400" />
                                            <span className="text-gray-900">{selectedEmployee.phone}</span>
                                        </div>
                                    )}
                                    <div className="flex items-center gap-2 text-sm">
                                        <Briefcase className="w-5 h-5 text-gray-400" />
                                        <span className="text-gray-900">{selectedEmployee.department}</span>
                                    </div>
                                    {selectedEmployee.location && (
                                        <div className="flex items-center gap-2 text-sm">
                                            <MapPin className="w-5 h-5 text-gray-400" />
                                            <span className="text-gray-900">{selectedEmployee.location}</span>
                                        </div>
                                    )}
                                    {selectedEmployee.manager_name && (
                                        <div className="flex items-center gap-2 text-sm">
                                            <User className="w-5 h-5 text-gray-400" />
                                            <span className="text-gray-700">Reports to: <span className="font-medium text-gray-900">{selectedEmployee.manager_name}</span></span>
                                        </div>
                                    )}
                                </div>
                            </div>
                        ) : (
                            <div className="text-center p-8 text-gray-500">
                                <User className="w-12 h-12 mx-auto mb-2 text-gray-400" />
                                <p>Select an employee to view details</p>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Directory View */}
            {view === 'directory' && (
                <div className="space-y-4">
                    {/* Filters */}
                    <div className="flex gap-4">
                        <div className="flex-1 relative">
                            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
                            <input
                                type="text"
                                placeholder="Search employees..."
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                            />
                        </div>
                        <select
                            value={filterDepartment}
                            onChange={(e) => setFilterDepartment(e.target.value)}
                            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                        >
                            <option value="all">All Departments</option>
                            {Array.from(new Set(employees.map(e => e.department))).map(dept => (
                                <option key={dept} value={dept}>{dept}</option>
                            ))}
                        </select>
                    </div>

                    {/* Employee grid */}
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {loading ? (
                            <div className="col-span-full flex items-center justify-center p-8">
                                <Loader className="w-6 h-6 animate-spin text-blue-600" />
                            </div>
                        ) : filteredEmployees.length === 0 ? (
                            <div className="col-span-full text-center p-8 text-gray-500">
                                <Users className="w-12 h-12 mx-auto mb-2 text-gray-400" />
                                <p>No employees found</p>
                            </div>
                        ) : (
                            filteredEmployees.map(employee => (
                                <div key={employee.employee_id} className="bg-white rounded-lg border border-gray-200 p-4 hover:shadow-md transition-shadow">
                                    <div className="flex items-start gap-3">
                                        <div className="w-12 h-12 bg-blue-600 text-white rounded-full flex items-center justify-center font-semibold flex-shrink-0">
                                            {employee.first_name[0]}{employee.last_name[0]}
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <h3 className="font-semibold text-gray-900 truncate">
                                                {employee.first_name} {employee.last_name}
                                            </h3>
                                            <p className="text-sm text-gray-600 truncate">{employee.position}</p>
                                            <p className="text-xs text-gray-500 mt-1">{employee.department}</p>
                                        </div>
                                    </div>
                                    <div className="mt-3 space-y-2">
                                        <div className="flex items-center gap-2 text-sm">
                                            <Mail className="w-4 h-4 text-gray-400 flex-shrink-0" />
                                            <a href={`mailto:${employee.email}`} className="text-blue-600 hover:text-blue-700 truncate">
                                                {employee.email}
                                            </a>
                                        </div>
                                        {employee.phone && (
                                            <div className="flex items-center gap-2 text-sm">
                                                <Phone className="w-4 h-4 text-gray-400 flex-shrink-0" />
                                                <span className="text-gray-900">{employee.phone}</span>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </div>
            )}

            {/* Departments View */}
            {view === 'departments' && (
                <div className="space-y-4">
                    {loading ? (
                        <div className="flex items-center justify-center p-8">
                            <Loader className="w-6 h-6 animate-spin text-blue-600" />
                        </div>
                    ) : departments.length === 0 ? (
                        <div className="text-center p-8 text-gray-500">
                            <Building className="w-12 h-12 mx-auto mb-2 text-gray-400" />
                            <p>No departments found</p>
                        </div>
                    ) : (
                        departments.map(dept => (
                            <div key={dept.department_id} className="bg-white rounded-lg border border-gray-200">
                                <div className="p-4 border-b border-gray-200 bg-gray-50">
                                    <div className="flex items-center justify-between">
                                        <div className="flex items-center gap-3">
                                            <Building className="w-6 h-6 text-blue-600" />
                                            <div>
                                                <h3 className="text-lg font-semibold text-gray-900">{dept.name}</h3>
                                                {dept.head_name && (
                                                    <p className="text-sm text-gray-600">Head: {dept.head_name}</p>
                                                )}
                                            </div>
                                        </div>
                                        <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-medium">
                                            {dept.employee_count} employees
                                        </span>
                                    </div>
                                </div>
                                <div className="p-4">
                                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                                        {dept.employees.map(employee => (
                                            <div key={employee.employee_id} className="flex items-center gap-2 p-2 border border-gray-200 rounded-lg hover:bg-gray-50">
                                                <div className="w-8 h-8 bg-blue-600 text-white rounded-full flex items-center justify-center font-semibold text-xs flex-shrink-0">
                                                    {employee.first_name[0]}{employee.last_name[0]}
                                                </div>
                                                <div className="flex-1 min-w-0">
                                                    <p className="text-sm font-medium text-gray-900 truncate">
                                                        {employee.first_name} {employee.last_name}
                                                    </p>
                                                    <p className="text-xs text-gray-600 truncate">{employee.position}</p>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            )}
        </div>
    );
};

export default EnhancedOrganizationTreeModule;
