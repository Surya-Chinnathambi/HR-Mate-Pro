import { useState } from "react";

interface ThemePickerModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentTheme: string;
  onThemeChange: (theme: string) => void;
}

export function ThemePickerModal({ isOpen, onClose, currentTheme, onThemeChange }: ThemePickerModalProps) {
  const themes = [
    {
      id: "blue-purple",
      name: "Ocean Blue",
      primary: "from-blue-600 to-purple-600",
      secondary: "from-blue-500 to-purple-500",
      colors: ["#3B82F6", "#8B5CF6"]
    },
    {
      id: "green-teal",
      name: "Forest Green",
      primary: "from-green-600 to-teal-600",
      secondary: "from-green-500 to-teal-500",
      colors: ["#10B981", "#14B8A6"]
    },
    {
      id: "orange-red",
      name: "Sunset Orange",
      primary: "from-orange-600 to-red-600",
      secondary: "from-orange-500 to-red-500",
      colors: ["#F97316", "#EF4444"]
    },
    {
      id: "pink-rose",
      name: "Cherry Blossom",
      primary: "from-pink-600 to-rose-600",
      secondary: "from-pink-500 to-rose-500",
      colors: ["#EC4899", "#F43F5E"]
    },
    {
      id: "indigo-purple",
      name: "Royal Purple",
      primary: "from-indigo-600 to-purple-600",
      secondary: "from-indigo-500 to-purple-500",
      colors: ["#4F46E5", "#8B5CF6"]
    },
    {
      id: "cyan-blue",
      name: "Sky Blue",
      primary: "from-cyan-600 to-blue-600",
      secondary: "from-cyan-500 to-blue-500",
      colors: ["#0891B2", "#3B82F6"]
    },
    {
      id: "emerald-green",
      name: "Emerald",
      primary: "from-emerald-600 to-green-600",
      secondary: "from-emerald-500 to-green-500",
      colors: ["#059669", "#10B981"]
    },
    {
      id: "violet-fuchsia",
      name: "Mystic Violet",
      primary: "from-violet-600 to-fuchsia-600",
      secondary: "from-violet-500 to-fuchsia-500",
      colors: ["#7C3AED", "#C026D3"]
    }
  ];

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl animate-fadeIn">
        {/* Header */}
        <div className="p-6 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold text-gray-900 flex items-center">
              <span className="mr-2">🎨</span>
              Choose Color Theme
            </h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Theme Grid */}
        <div className="p-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {themes.map((theme) => (
              <button
                key={theme.id}
                onClick={() => {
                  onThemeChange(theme.id);
                  onClose();
                }}
                className={`relative p-4 rounded-xl border-2 transition-all duration-200 hover:scale-105 ${
                  currentTheme === theme.id 
                    ? 'border-blue-500 shadow-lg' 
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                {/* Theme Preview */}
                <div className={`w-full h-16 bg-gradient-to-r ${theme.primary} rounded-lg mb-3 shadow-md`}>
                  <div className="flex items-center justify-center h-full">
                    <div className="flex space-x-1">
                      {theme.colors.map((color, index) => (
                        <div
                          key={index}
                          className="w-3 h-3 rounded-full"
                          style={{ backgroundColor: color }}
                        />
                      ))}
                    </div>
                  </div>
                </div>

                {/* Theme Name */}
                <p className="text-sm font-medium text-gray-900 text-center">
                  {theme.name}
                </p>

                {/* Selected Indicator */}
                {currentTheme === theme.id && (
                  <div className="absolute -top-2 -right-2 w-6 h-6 bg-blue-500 rounded-full flex items-center justify-center">
                    <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                )}
              </button>
            ))}
          </div>

          {/* Preview Section */}
          <div className="mt-6 p-4 bg-gray-50 rounded-xl">
            <h3 className="text-sm font-medium text-gray-700 mb-3">Preview</h3>
            <div className="flex items-center space-x-4">
              <div className={`w-12 h-12 bg-gradient-to-r ${themes.find(t => t.id === currentTheme)?.primary || themes[0].primary} rounded-xl flex items-center justify-center shadow-md`}>
                <span className="text-white font-bold">HR</span>
              </div>
              <div>
                <p className="font-semibold text-gray-900">HRMS Dashboard</p>
                <p className="text-sm text-gray-600">With {themes.find(t => t.id === currentTheme)?.name || themes[0].name} theme</p>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-gray-200">
          <div className="flex justify-end space-x-3">
            <button
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
