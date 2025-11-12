interface AppsModuleProps {
  employee: any;
}

export function AppsModule({ employee }: AppsModuleProps) {
  const apps = [
    {
      id: 1,
      name: "Time Tracker",
      description: "Track your work hours and productivity",
      icon: "⏰",
      category: "Productivity",
      status: "Available"
    },
    {
      id: 2,
      name: "Document Manager",
      description: "Manage and share documents securely",
      icon: "📁",
      category: "Productivity",
      status: "Available"
    },
    {
      id: 3,
      name: "Team Chat",
      description: "Communicate with your team members",
      icon: "💬",
      category: "Communication",
      status: "Available"
    },
    {
      id: 4,
      name: "Calendar Sync",
      description: "Sync your calendar across devices",
      icon: "📅",
      category: "Productivity",
      status: "Coming Soon"
    },
    {
      id: 5,
      name: "Learning Hub",
      description: "Access training materials and courses",
      icon: "📚",
      category: "Learning",
      status: "Available"
    },
    {
      id: 6,
      name: "Wellness Tracker",
      description: "Monitor your health and wellness goals",
      icon: "🏃‍♂️",
      category: "Health",
      status: "Coming Soon"
    }
  ];

  const categories = [...new Set(apps.map(app => app.category))];

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-3xl font-bold text-gray-900">Apps</h2>
        <button className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors">
          Request App
        </button>
      </div>

      {/* App Categories */}
      {categories.map(category => (
        <div key={category} className="bg-white rounded-xl shadow-lg border border-gray-100">
          <div className="p-6 border-b border-gray-100">
            <h3 className="text-lg font-semibold text-gray-900">{category}</h3>
          </div>
          <div className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {apps.filter(app => app.category === category).map(app => (
                <div key={app.id} className="border rounded-lg p-4 hover:shadow-md transition-shadow">
                  <div className="flex items-start space-x-3">
                    <div className="text-3xl">{app.icon}</div>
                    <div className="flex-1">
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="font-medium text-gray-900">{app.name}</h4>
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${app.status === 'Available'
                            ? 'bg-green-100 text-green-800'
                            : 'bg-yellow-100 text-yellow-800'
                          }`}>
                          {app.status}
                        </span>
                      </div>
                      <p className="text-sm text-gray-600 mb-3">{app.description}</p>
                      <button
                        className={`w-full py-2 px-3 rounded-lg text-sm font-medium transition-colors ${app.status === 'Available'
                            ? 'bg-blue-600 text-white hover:bg-blue-700'
                            : 'bg-gray-100 text-gray-500 cursor-not-allowed'
                          }`}
                        disabled={app.status !== 'Available'}
                      >
                        {app.status === 'Available' ? 'Launch App' : 'Coming Soon'}
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      ))}

      {/* Quick Actions */}
      <div className="bg-white rounded-xl shadow-lg border border-gray-100">
        <div className="p-6 border-b border-gray-100">
          <h3 className="text-lg font-semibold text-gray-900 flex items-center">
            <span className="mr-2">⚡</span>
            Quick Actions
          </h3>
        </div>
        <div className="p-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <button className="flex flex-col items-center p-4 border rounded-lg hover:bg-gray-50 transition-colors">
              <span className="text-2xl mb-2">📊</span>
              <span className="text-sm font-medium">Reports</span>
            </button>
            <button className="flex flex-col items-center p-4 border rounded-lg hover:bg-gray-50 transition-colors">
              <span className="text-2xl mb-2">🔧</span>
              <span className="text-sm font-medium">Settings</span>
            </button>
            <button className="flex flex-col items-center p-4 border rounded-lg hover:bg-gray-50 transition-colors">
              <span className="text-2xl mb-2">📱</span>
              <span className="text-sm font-medium">Mobile App</span>
            </button>
            <button className="flex flex-col items-center p-4 border rounded-lg hover:bg-gray-50 transition-colors">
              <span className="text-2xl mb-2">❓</span>
              <span className="text-sm font-medium">Help</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
