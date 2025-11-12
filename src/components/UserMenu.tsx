import { useState, useRef, useEffect } from "react";

interface UserMenuProps {
  employee: any;
  onViewProfile: () => void;
  onChangePassword: () => void;
  onThemePicker: () => void;
  onLogout: () => void;
  isDarkMode: boolean;
  onToggleDarkMode: () => void;
}

export function UserMenu({
  employee,
  onViewProfile,
  onChangePassword,
  onThemePicker,
  onLogout,
  isDarkMode,
  onToggleDarkMode
}: UserMenuProps) {
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const menuItems = [
    {
      icon: "👤",
      label: "View Profile",
      onClick: () => {
        onViewProfile();
        setIsOpen(false);
      }
    },
    {
      icon: "🔐",
      label: "Change Password",
      onClick: () => {
        onChangePassword();
        setIsOpen(false);
      }
    },
    {
      icon: "🎨",
      label: "Color Theme",
      onClick: () => {
        onThemePicker();
        setIsOpen(false);
      }
    },
    {
      icon: isDarkMode ? "☀️" : "🌙",
      label: isDarkMode ? "Light Mode" : "Dark Mode",
      onClick: () => {
        onToggleDarkMode();
        setIsOpen(false);
      }
    },
    {
      icon: "🚪",
      label: "Logout",
      onClick: () => {
        onLogout();
        setIsOpen(false);
      },
      danger: true
    }
  ];

  return (
    <div className="relative" ref={menuRef}>
      {/* User Profile Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center space-x-3 bg-white/50 rounded-2xl p-2 shadow-md hover:bg-white/80 transition-all duration-200 hover:shadow-lg"
      >
        <div className="w-10 h-10 bg-gradient-to-r from-blue-500 to-purple-500 rounded-xl flex items-center justify-center shadow-md">
          <span className="text-white font-bold text-sm">
            {(employee?.first_name || employee?.firstName || 'U').charAt(0)}{(employee?.last_name || employee?.lastName || '').charAt(0) || ''}
          </span>
        </div>
        <div className="hidden md:block">
          <p className="font-semibold text-gray-900 text-sm">
            {employee?.first_name || employee?.firstName || ''} {employee?.last_name || employee?.lastName || ''}
          </p>
          <p className="text-xs text-gray-600">{employee?.designation}</p>
          <span className="text-xs text-gray-500">{employee?.employee_id || employee?.employeeId}</span>
        </div>
        <div className="text-gray-400">
          <svg className={`w-4 h-4 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute right-0 top-full mt-2 w-64 bg-white/95 backdrop-blur-md rounded-2xl shadow-2xl border border-white/20 py-2 z-50 animate-fadeIn">
          {/* User Info Header */}
          <div className="px-4 py-3 border-b border-gray-200">
            <div className="flex items-center space-x-3">
              <div className="w-12 h-12 bg-gradient-to-r from-blue-500 to-purple-500 rounded-xl flex items-center justify-center shadow-md">
                <span className="text-white font-bold">
                  {(employee?.first_name || employee?.firstName || 'U').charAt(0)}{(employee?.last_name || employee?.lastName || '').charAt(0) || ''}
                </span>
              </div>
              <div>
                <p className="font-semibold text-gray-900">
                  {employee?.first_name || employee?.firstName || ''} {employee?.last_name || employee?.lastName || ''}
                </p>
                <p className="text-sm text-gray-600">{employee?.designation}</p>
                <p className="text-xs text-gray-500">{employee?.email}</p>
              </div>
            </div>
          </div>

          {/* Menu Items */}
          <div className="py-2">
            {menuItems.map((item, index) => (
              <button
                key={index}
                onClick={item.onClick}
                className={`w-full flex items-center space-x-3 px-4 py-3 text-left transition-all duration-200 ${item.danger
                    ? 'hover:bg-red-50 text-red-600 hover:text-red-700'
                    : 'hover:bg-gray-50 text-gray-700 hover:text-gray-900'
                  }`}
              >
                <span className="text-lg">{item.icon}</span>
                <span className="font-medium">{item.label}</span>
              </button>
            ))}
          </div>

          {/* Footer */}
          <div className="px-4 py-2 border-t border-gray-200">
            <p className="text-xs text-gray-500 text-center">
              Employee ID: {employee?.employee_id || employee?.employeeId}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
