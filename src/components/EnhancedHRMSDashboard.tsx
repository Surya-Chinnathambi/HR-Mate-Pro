import { useState, useEffect, useMemo } from "react";
import apiClient from "../api/client";
import {
  Home, Clock, Calendar, TrendingUp, CreditCard, Headphones, Grid,
  Users, DollarSign, FileText, Building, MessageCircle,
  ChevronDown, ChevronRight, User, Lock, LogOut, Palette, Moon, Sun,
  Archive, Bell, BarChart3, Target, ThumbsUp, Menu, X, Sparkles
} from "lucide-react";

// Import all your existing components
import { EmployeeDashboardContent } from "./EmployeeDashboardContent";
import { ProfileModule } from "./ProfileModule";
import { PayrollModule } from "./PayrollModule";
import { MyFinancesModule } from "./MyFinancesModule";
import { AppsModule } from "./AppsModule";
import { EngageModule } from "./EngageModule";
import { AICommandCenter } from "./AICommandCenter";
import { ChangePasswordModal } from "./ChangePasswordModal";
import { ThemePickerModal } from "./ThemePickerModal";

// Phase 2: Core Communication & Work Modules
import { EnhancedWorkInbox } from "./EnhancedWorkInbox";
import { EnhancedMessagingModule } from "./EnhancedMessagingModule";
import { EnhancedBroadcastsModule } from "./EnhancedBroadcastsModule";
import EnhancedAttendanceModule from "./EnhancedAttendanceModule";
import EnhancedLeaveModule from "./EnhancedLeaveModule";

// Phase 3: Manager & Analytics Modules
import EnhancedMyTeamModule from "./EnhancedMyTeamModule";
import EnhancedAnalyticsDashboard from "./EnhancedAnalyticsDashboard";

// Phase 4: Additional Modules
import EnhancedPerformanceModule from "./EnhancedPerformanceModule";
import EnhancedExpensesModule from "./EnhancedExpensesModule";
import EnhancedHelpdeskModule from "./EnhancedHelpdeskModule";
import EnhancedOrganizationTreeModule from "./EnhancedOrganizationTreeModule";
import EnhancedCompanyPoliciesModule from "./EnhancedCompanyPoliciesModule";

// Supporting Component
import { NotificationBell } from "./NotificationBell";

interface MenuItem {
  id: string;
  label: string;
  icon: any;
  component?: React.ComponentType<any>;
  subItems?: MenuItem[];
  badge?: number | string;
  color?: string;
}

interface EnhancedHRMSDashboardProps {
  user?: any;
  onLogout?: () => void;
}

export function EnhancedHRMSDashboard({ user, onLogout }: EnhancedHRMSDashboardProps = {}) {
  const [activeModule, setActiveModule] = useState("dashboard");
  const [isAIOpen, setIsAIOpen] = useState(false);
  const [currentTime, setCurrentTime] = useState(new Date());
  const [isChangePasswordOpen, setIsChangePasswordOpen] = useState(false);
  const [isThemePickerOpen, setIsThemePickerOpen] = useState(false);
  const [currentTheme, setCurrentTheme] = useState("blue-purple");
  const [isDarkMode, setIsDarkMode] = useState(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [isSidebarExpanded, setIsSidebarExpanded] = useState(false);
  const [openMenu, setOpenMenu] = useState<string | null>(null);
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);

  // Replace Convex hooks with REST API calls
  const [employee, setEmployee] = useState<any | null>(null);
  const [notifications, setNotifications] = useState<any>(null);
  const [userRole, setUserRole] = useState<'employee' | 'manager' | 'hr'>('employee');

  useEffect(() => {
    let mounted = true;

    const fetchData = async () => {
      try {
        const [empRes, notifRes] = await Promise.all([
          apiClient.get('/employees/current'),
          apiClient.get('/realtime/notifications')
        ]);

        if (!mounted) return;

        // Use snake_case fields from backend directly (Option B)
        const emp = empRes?.data ?? null;
        setEmployee(emp);

        // Set user role and default module based on employee role
        if (emp?.role) {
          const role = emp.role.toLowerCase();
          console.log('🔍 Employee Role Debug:', {
            raw: emp.role,
            lowercase: role,
            willSetAs: role as 'employee' | 'manager' | 'hr'
          });
          setUserRole(role as 'employee' | 'manager' | 'hr');

          // Set default dashboard based on role
          if (role === 'manager') {
            console.log('✅ Setting manager default module: my-team');
            setActiveModule('my-team');
          } else if (role === 'hr') {
            console.log('✅ Setting HR default module: analytics');
            setActiveModule('analytics');
          } else {
            console.log('✅ Setting employee default module: dashboard');
            setActiveModule('dashboard');
          }
        } else {
          console.log('⚠️ No role found on employee object:', emp);
        }

        const notifs = notifRes?.data ?? { notifications: [], unreadCount: 0 };
        setNotifications(notifs);
      } catch (err: any) {
        if (err.response?.status === 404) {
          // Employee not found — keep employee as null and let UI handle setup
          setEmployee(null);
        } else {
          console.error('Failed to fetch initial data', err);
        }
      }
    };

    fetchData();

    return () => { mounted = false; };
  }, []);

  // Update time every second
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Menu structure - Enhanced with all 12 new modules
  const menuItems: MenuItem[] = [
    {
      id: "dashboard",
      label: "Home",
      icon: Home,
      component: EmployeeDashboardContent,
      color: "from-blue-500 to-cyan-500"
    },
    {
      id: "work-inbox",
      label: "Work Inbox",
      icon: Target,
      badge: notifications?.unreadCount,
      component: EnhancedWorkInbox,
      color: "from-orange-500 to-red-500"
    },
    {
      id: "communications",
      label: "Communications",
      icon: MessageCircle,
      color: "from-pink-500 to-rose-500",
      subItems: [
        { id: "messages", label: "Messages", icon: MessageCircle, component: EnhancedMessagingModule },
        { id: "broadcasts", label: "Broadcasts", icon: Bell, component: EnhancedBroadcastsModule },
        { id: "engage", label: "Engage", icon: ThumbsUp, component: EngageModule }
      ]
    },
    {
      id: "me",
      label: "Me",
      icon: User,
      color: "from-purple-500 to-pink-500",
      subItems: [
        { id: "attendance", label: "Attendance", icon: Clock, component: EnhancedAttendanceModule },
        { id: "leave", label: "Leave", icon: Calendar, component: EnhancedLeaveModule },
        { id: "performance", label: "Performance", icon: TrendingUp, component: EnhancedPerformanceModule },
        { id: "expenses", label: "Expenses & Travel", icon: CreditCard, component: EnhancedExpensesModule },
        { id: "helpdesk", label: "Helpdesk", icon: Headphones, component: EnhancedHelpdeskModule },
        { id: "apps", label: "Apps", icon: Grid, component: AppsModule }
      ]
    },
    {
      id: "my-team",
      label: "My Team",
      icon: Users,
      color: "from-indigo-500 to-purple-500",
      component: EnhancedMyTeamModule,
      subItems: [
        { id: "team-dashboard", label: "Team Dashboard", icon: BarChart3, component: EnhancedMyTeamModule }
      ]
    },
    {
      id: "analytics",
      label: "Analytics",
      icon: BarChart3,
      color: "from-cyan-500 to-blue-500",
      component: EnhancedAnalyticsDashboard
    },
    {
      id: "my-finances",
      label: "My Finances",
      icon: DollarSign,
      color: "from-green-500 to-teal-500",
      subItems: [
        { id: "payroll", label: "Payroll", icon: DollarSign, component: PayrollModule },
        { id: "tax-docs", label: "Tax Docs", icon: FileText, component: MyFinancesModule }
      ]
    },
    {
      id: "org",
      label: "Organization",
      icon: Building,
      color: "from-emerald-500 to-green-500",
      component: EnhancedOrganizationTreeModule,
      subItems: [
        { id: "org-tree", label: "Organization Tree", icon: Building, component: EnhancedOrganizationTreeModule }
      ]
    },
    {
      id: "policies",
      label: "Company Policies",
      icon: FileText,
      component: EnhancedCompanyPoliciesModule,
      color: "from-slate-500 to-gray-600"
    }
  ];

  // All menus visible to all roles - no filtering needed
  // Role-based data filtering happens within each component (Analytics, etc.)
  const filteredMenuItems = useMemo(() => {
    console.log('🔄 Menu items - All visible for role:', userRole);
    // All users see all menus
    return menuItems;
  }, [userRole]);

  const handleMenuClick = (menuId: string) => {
    if (openMenu === menuId) {
      setOpenMenu(null);
    } else {
      setOpenMenu(menuId);
    }
  };

  const handleModuleChange = (moduleId: string) => {
    setActiveModule(moduleId);
  };

  const getPageTitle = () => {
    for (const item of filteredMenuItems) {
      if (item.id === activeModule) return item.label;
      if (item.subItems) {
        const subItem = item.subItems.find(sub => sub.id === activeModule);
        if (subItem) return subItem.label;
      }
    }
    return "Dashboard";
  };

  // Your existing render logic
  const renderActiveModule = () => {
    // Handle profile module specially
    if (activeModule === "profile") {
      return employee ? <ProfileModule employee={employee} /> : <div>Loading...</div>;
    }

    const activeItem = filteredMenuItems.find(item => item.id === activeModule) ||
      filteredMenuItems.flatMap(item => item.subItems || []).find(item => item.id === activeModule);

    if (!activeItem?.component) {
      // Default dashboard based on role
      if (userRole === 'manager') {
        return <EnhancedMyTeamModule />;
      } else if (userRole === 'hr') {
        return <EnhancedAnalyticsDashboard />;
      }
      return <EmployeeDashboardContent employee={employee || null} />;
    }

    const Component = activeItem.component;

    // Pass employee prop only to components that accept it
    if (Component === EmployeeDashboardContent || Component === ProfileModule) {
      return <Component employee={employee || null} />;
    }

    // Render without props for other components
    return <Component />;
  };

  // Loading state
  if (!employee) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-800 font-semibold text-lg mb-2">Setting up your workspace...</p>
          <p className="text-gray-600 text-sm">Creating your employee profile • Usually takes 5-10 seconds</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`min-h-screen ${isDarkMode ? 'dark' : ''}`}>
      <div className="min-h-screen bg-gradient-to-br from-gray-50 via-blue-50 to-indigo-50 dark:bg-gradient-to-br dark:from-gray-950 dark:via-gray-900 dark:to-gray-950 transition-colors duration-300">

        {/* Top Header */}
        <header className="fixed top-0 left-0 right-0 h-20 bg-white/80 dark:bg-gray-900/80 backdrop-blur-xl border-b border-gray-200 dark:border-gray-800 z-50 shadow-lg">
          <div className="h-full px-6 flex items-center justify-between">
            {/* Left - Logo & Menu Toggle */}
            <div className="flex items-center space-x-4">
              <button
                onClick={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
                className="p-2 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-800 transition-all duration-200"
              >
                {isSidebarCollapsed ? (
                  <Menu className="w-6 h-6 text-gray-600 dark:text-gray-300" />
                ) : (
                  <X className="w-6 h-6 text-gray-600 dark:text-gray-300" />
                )}
              </button>
              <div className="flex items-center space-x-3">
                <div className="w-12 h-12 bg-gradient-to-r from-blue-600 to-purple-600 rounded-2xl flex items-center justify-center shadow-lg">
                  <span className="text-white text-2xl font-bold">H</span>
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h1 className="text-xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                      HRMS Pro
                    </h1>
                    {/* Role Badge */}
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wide ${userRole === 'hr'
                      ? 'bg-gradient-to-r from-red-500 to-orange-500 text-white'
                      : userRole === 'manager'
                        ? 'bg-gradient-to-r from-blue-500 to-cyan-500 text-white'
                        : 'bg-gradient-to-r from-gray-400 to-gray-500 text-white'
                      }`}>
                      {userRole}
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 dark:text-gray-400">Human Resource Management</p>
                </div>
              </div>
            </div>

            {/* Center - Time & Date */}
            <div className="hidden md:flex items-center text-center">
              <div>
                <div className="text-2xl font-bold text-gray-900 dark:text-white">
                  {currentTime.toLocaleTimeString('en-US', {
                    hour: '2-digit',
                    minute: '2-digit',
                    hour12: true
                  })}
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400">
                  {currentTime.toLocaleDateString('en-US', {
                    weekday: 'short',
                    month: 'short',
                    day: 'numeric'
                  })}
                </div>
              </div>
            </div>

            {/* Right - Actions & User Menu */}
            <div className="flex items-center space-x-3">
              {/* AI Assistant Button */}
              <button
                onClick={() => setIsAIOpen(true)}
                className="relative bg-gradient-to-r from-purple-600 to-pink-600 text-white p-3 rounded-xl hover:from-purple-700 hover:to-pink-700 transition-all duration-200 shadow-lg hover:shadow-xl transform hover:scale-105"
              >
                <Sparkles className="w-5 h-5" />
                <div className="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
              </button>

              {/* Notifications */}
              <NotificationBell />

              {/* User Profile Menu */}
              <div className="relative">
                <button
                  onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
                  className="flex items-center space-x-3 p-2 pr-4 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-800 transition-all duration-200"
                >
                  <img
                    src={employee.avatar || `https://api.dicebear.com/7.x/avataaars/svg?seed=${employee.first_name}`}
                    alt={employee.first_name}
                    className="w-10 h-10 rounded-full border-2 border-blue-500 shadow-md"
                  />
                  <div className="text-left hidden lg:block">
                    <p className="text-sm font-semibold text-gray-900 dark:text-white">
                      {employee.first_name} {employee.last_name}
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      {employee.designation}
                    </p>
                  </div>
                  <ChevronDown className={`w-4 h-4 text-gray-500 dark:text-gray-400 transition-transform ${isUserMenuOpen ? 'rotate-180' : ''}`} />
                </button>

                {/* User Dropdown */}
                {isUserMenuOpen && (
                  <div className="absolute right-0 mt-2 w-64 bg-white dark:bg-gray-900 rounded-2xl shadow-2xl border border-gray-200 dark:border-gray-800 py-2 z-50">
                    <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-800">
                      <p className="text-sm font-semibold text-gray-900 dark:text-white">
                        {employee.first_name} {employee.last_name}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        {employee.email}
                      </p>
                    </div>

                    <button
                      onClick={() => {
                        handleModuleChange("profile");
                        setIsUserMenuOpen(false);
                      }}
                      className="w-full flex items-center space-x-3 px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors text-gray-700 dark:text-gray-300"
                    >
                      <User className="w-4 h-4" />
                      <span className="text-sm">View Profile</span>
                    </button>

                    <button
                      onClick={() => {
                        setIsChangePasswordOpen(true);
                        setIsUserMenuOpen(false);
                      }}
                      className="w-full flex items-center space-x-3 px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors text-gray-700 dark:text-gray-300"
                    >
                      <Lock className="w-4 h-4" />
                      <span className="text-sm">Change Password</span>
                    </button>

                    <button
                      onClick={() => {
                        setIsThemePickerOpen(true);
                        setIsUserMenuOpen(false);
                      }}
                      className="w-full flex items-center space-x-3 px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors text-gray-700 dark:text-gray-300"
                    >
                      <Palette className="w-4 h-4" />
                      <span className="text-sm">Color Theme Picker</span>
                    </button>

                    <button
                      onClick={() => {
                        setIsDarkMode(!isDarkMode);
                        setIsUserMenuOpen(false);
                      }}
                      className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors text-gray-700 dark:text-gray-300"
                    >
                      <div className="flex items-center space-x-3">
                        {isDarkMode ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
                        <span className="text-sm">{isDarkMode ? 'Light Mode' : 'Dark Mode'}</span>
                      </div>
                      <div className={`w-10 h-5 rounded-full transition-colors ${isDarkMode ? 'bg-blue-600' : 'bg-gray-300'} relative`}>
                        <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform ${isDarkMode ? 'translate-x-5' : 'translate-x-0.5'}`}></div>
                      </div>
                    </button>

                    <div className="border-t border-gray-200 dark:border-gray-800 mt-2"></div>

                    <button
                      onClick={() => {
                        console.log("Logout");
                        onLogout?.();
                      }}
                      className="w-full flex items-center space-x-3 px-4 py-3 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors text-red-600 dark:text-red-400"
                    >
                      <LogOut className="w-4 h-4" />
                      <span className="text-sm font-semibold">Logout</span>
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        </header>

        {/* Sidebar */}
        <aside
          onMouseEnter={() => setIsSidebarExpanded(true)}
          onMouseLeave={() => setIsSidebarExpanded(false)}
          className={`fixed left-0 top-20 h-[calc(100vh-5rem)] bg-white/60 dark:bg-gray-900/60 backdrop-blur-xl border-r border-gray-200 dark:border-gray-800 transition-all duration-300 z-40 overflow-y-auto shadow-xl ${isSidebarCollapsed ? '-translate-x-full' : 'translate-x-0'
            } ${isSidebarExpanded ? 'w-80' : 'w-20'}`}
        >
          <nav className="p-4 space-y-2">
            {filteredMenuItems.map((item) => {
              const Icon = item.icon;
              const isOpen = openMenu === item.id;
              const hasSubItems = item.subItems && item.subItems.length > 0;
              const isActive = item.id === activeModule ||
                (item.subItems?.some(sub => sub.id === activeModule));

              return (
                <div key={item.id}>
                  {/* Main Menu Item */}
                  <button
                    onClick={() => {
                      if (hasSubItems) {
                        handleMenuClick(item.id);
                      } else {
                        handleModuleChange(item.id);
                      }
                    }}
                    className={`w-full flex items-center justify-between px-4 py-3.5 rounded-xl transition-all duration-200 group ${isActive
                      ? `bg-gradient-to-r ${item.color} text-white shadow-lg`
                      : 'text-gray-700 dark:text-gray-300 hover:bg-white/80 dark:hover:bg-gray-800 hover:shadow-md'
                      }`}
                  >
                    <div className="flex items-center space-x-3">
                      <Icon className="w-5 h-5 flex-shrink-0" />
                      <span className={`font-semibold text-sm whitespace-nowrap transition-all duration-300 ${isSidebarExpanded ? 'opacity-100' : 'opacity-0 w-0'
                        }`}>{item.label}</span>
                    </div>

                    <div className={`flex items-center space-x-2 transition-all duration-300 ${isSidebarExpanded ? 'opacity-100' : 'opacity-0 w-0'
                      }`}>
                      {item.badge && (
                        <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${isActive
                          ? 'bg-white text-blue-600'
                          : 'bg-red-500 text-white'
                          }`}>
                          {item.badge}
                        </span>
                      )}
                      {hasSubItems && (
                        <ChevronRight className={`w-4 h-4 transition-transform duration-200 ${isOpen ? 'rotate-90' : ''
                          }`} />
                      )}
                    </div>
                  </button>

                  {/* Submenu */}
                  {hasSubItems && isOpen && isSidebarExpanded && (
                    <div className="mt-2 ml-4 space-y-1 animate-in slide-in-from-top-2 duration-200">
                      {item.subItems?.map((subItem) => {
                        const SubIcon = subItem.icon;
                        const isSubActive = subItem.id === activeModule;

                        return (
                          <button
                            key={subItem.id}
                            onClick={() => handleModuleChange(subItem.id)}
                            className={`w-full flex items-center justify-between px-4 py-2.5 rounded-xl transition-all duration-200 ${isSubActive
                              ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 font-medium shadow-sm'
                              : 'text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-gray-200'
                              }`}
                          >
                            <div className="flex items-center space-x-3">
                              <SubIcon className="w-4 h-4" />
                              <span className="text-sm">{subItem.label}</span>
                            </div>

                            {subItem.badge && (
                              <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${isSubActive
                                ? 'bg-blue-600 text-white'
                                : 'bg-red-500 text-white'
                                }`}>
                                {subItem.badge}
                              </span>
                            )}
                          </button>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })}
          </nav>

          {/* Sidebar Footer - Today's Overview */}
          {isSidebarExpanded && (
            <div className="p-4 border-t border-gray-200 dark:border-gray-800">
              <div className="bg-gradient-to-r from-blue-600 to-purple-600 rounded-2xl p-5 text-white shadow-lg">
                <h3 className="font-bold text-base mb-3">Today's Overview</h3>
                <div className="space-y-2.5 text-sm">
                  <div className="flex justify-between items-center">
                    <span className="opacity-90">Status:</span>
                    <span className="font-semibold bg-white/20 px-3 py-1 rounded-full">Present</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="opacity-90">Hours:</span>
                    <span className="font-semibold">8.2h</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="opacity-90">Leave Balance:</span>
                    <span className="font-semibold">12 days</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </aside>

        {/* Main Content */}
        <main
          className={`pt-20 transition-all duration-300 ${isSidebarCollapsed ? 'ml-0' : isSidebarExpanded ? 'ml-80' : 'ml-20'
            }`}
        >
          <div className="p-8">
            <div className="mb-8">
              <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-2">
                {getPageTitle()}
              </h1>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Welcome back, {employee.first_name} {employee.last_name}
              </p>
            </div>

            {renderActiveModule()}
          </div>
        </main>

        {/* Overlay for mobile */}
        {!isSidebarCollapsed && (
          <div
            className="fixed inset-0 bg-black/50 z-30 lg:hidden top-20"
            onClick={() => setIsSidebarCollapsed(true)}
          />
        )}

        {/* AI Command Center Modal */}
        {isAIOpen && (
          <AICommandCenter
            onClose={() => setIsAIOpen(false)}
            employee={employee}
          />
        )}

        {/* Change Password Modal */}
        <ChangePasswordModal
          isOpen={isChangePasswordOpen}
          onClose={() => setIsChangePasswordOpen(false)}
          onSubmit={async (currentPassword: string, newPassword: string) => {
            console.log("Password change:", { currentPassword, newPassword });
          }}
        />

        {/* Theme Picker Modal */}
        <ThemePickerModal
          isOpen={isThemePickerOpen}
          onClose={() => setIsThemePickerOpen(false)}
          currentTheme={currentTheme}
          onThemeChange={setCurrentTheme}
        />
      </div>
    </div>
  );
}