import { useState, useEffect, useRef } from "react";
import apiClient from "../api/client";
import {
    User,
    Mail,
    Phone,
    Calendar,
    MapPin,
    Briefcase,
    Save,
    X,
    Edit2,
    Check,
    Camera,
    Upload,
    Loader,
    AlertCircle,
    CheckCircle,
} from "lucide-react";

interface ProfileModuleProps {
    employee: any;
    onUpdate?: () => void;
}

export function ProfileModuleEnhanced({ employee, onUpdate }: ProfileModuleProps) {
    const [isEditing, setIsEditing] = useState(false);
    const [loading, setLoading] = useState(false);
    const [uploadingAvatar, setUploadingAvatar] = useState(false);
    const [success, setSuccess] = useState(false);
    const [error, setError] = useState("");
    const [avatarPreview, setAvatarPreview] = useState<string | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const [formData, setFormData] = useState({
        first_name: employee.first_name || "",
        last_name: employee.last_name || "",
        phone: employee.phone || "",
        personal_email: employee.personal_email || "",
        designation: employee.designation || "",
        date_of_birth: employee.date_of_birth || "",
        gender: employee.gender || "",
        marital_status: employee.marital_status || "",
        nationality: employee.nationality || "",
        bio: employee.bio || "",
    });

    useEffect(() => {
        if (employee.avatar) {
            setAvatarPreview(`http://localhost:8000${employee.avatar}`);
        }
    }, [employee.avatar]);

    const handleChange = (
        e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
    ) => {
        const { name, value } = e.target;
        setFormData((prev) => ({ ...prev, [name]: value }));
    };

    const handleAvatarClick = () => {
        fileInputRef.current?.click();
    };

    const handleAvatarChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        // Validate file type
        if (!file.type.startsWith("image/")) {
            setError("Please select an image file");
            return;
        }

        // Validate file size (5MB)
        if (file.size > 5 * 1024 * 1024) {
            setError("Image size must be less than 5MB");
            return;
        }

        // Preview image
        const reader = new FileReader();
        reader.onloadend = () => {
            setAvatarPreview(reader.result as string);
        };
        reader.readAsDataURL(file);

        // Upload image
        setUploadingAvatar(true);
        setError("");

        try {
            const formData = new FormData();
            formData.append("file", file);

            const response = await apiClient.post("/employees/upload-avatar", formData, {
                headers: {
                    "Content-Type": "multipart/form-data",
                },
            });

            setSuccess(true);
            setTimeout(() => setSuccess(false), 3000);
            if (onUpdate) onUpdate();
        } catch (err: any) {
            console.error("Failed to upload avatar", err);
            setError(err.response?.data?.detail || "Failed to upload avatar");
            // Reset preview on error
            if (employee.avatar) {
                setAvatarPreview(`http://localhost:8000${employee.avatar}`);
            } else {
                setAvatarPreview(null);
            }
        } finally {
            setUploadingAvatar(false);
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError("");
        setSuccess(false);

        try {
            await apiClient.put(`/employees/${employee.id}`, formData);
            setSuccess(true);
            setIsEditing(false);
            setTimeout(() => setSuccess(false), 3000);
            if (onUpdate) onUpdate();
        } catch (err: any) {
            console.error("Failed to update profile", err);
            setError(err.response?.data?.detail || "Failed to update profile. Please try again.");
        } finally {
            setLoading(false);
        }
    };

    const handleCancel = () => {
        setFormData({
            first_name: employee.first_name || "",
            last_name: employee.last_name || "",
            phone: employee.phone || "",
            personal_email: employee.personal_email || "",
            designation: employee.designation || "",
            date_of_birth: employee.date_of_birth || "",
            gender: employee.gender || "",
            marital_status: employee.marital_status || "",
            nationality: employee.nationality || "",
            bio: employee.bio || "",
        });
        setIsEditing(false);
        setError("");
    };

    const getAvatarUrl = () => {
        if (avatarPreview) return avatarPreview;
        if (employee.avatar) return `http://localhost:8000${employee.avatar}`;
        return `https://api.dicebear.com/7.x/avataaars/svg?seed=${employee.first_name}`;
    };

    return (
        <div className="space-y-6">
            {/* Success/Error Messages */}
            {success && (
                <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-xl p-4 flex items-center space-x-3">
                    <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400 flex-shrink-0" />
                    <p className="text-green-800 dark:text-green-200">Profile updated successfully!</p>
                </div>
            )}

            {error && (
                <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-4 flex items-center space-x-3">
                    <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0" />
                    <p className="text-red-800 dark:text-red-200">{error}</p>
                </div>
            )}

            {/* Header with Cover Photo */}
            <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-lg overflow-hidden">
                <div className="h-32 bg-gradient-to-r from-blue-600 to-purple-600"></div>
                <div className="px-8 pb-8">
                    <div className="flex items-end justify-between -mt-16">
                        <div className="flex items-end space-x-6">
                            {/* Profile Picture with Upload */}
                            <div className="relative group">
                                <img
                                    src={getAvatarUrl()}
                                    alt={`${employee.first_name} ${employee.last_name}`}
                                    className="w-32 h-32 rounded-2xl border-4 border-white dark:border-gray-800 shadow-xl object-cover"
                                />
                                <button
                                    onClick={handleAvatarClick}
                                    disabled={uploadingAvatar}
                                    className="absolute inset-0 bg-black/50 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex items-center justify-center"
                                >
                                    {uploadingAvatar ? (
                                        <Loader className="w-6 h-6 text-white animate-spin" />
                                    ) : (
                                        <Camera className="w-6 h-6 text-white" />
                                    )}
                                </button>
                                <input
                                    ref={fileInputRef}
                                    type="file"
                                    accept="image/*"
                                    onChange={handleAvatarChange}
                                    className="hidden"
                                />
                            </div>

                            {/* Name and Title */}
                            <div className="pb-2">
                                <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
                                    {employee.first_name} {employee.last_name}
                                </h1>
                                <p className="text-gray-600 dark:text-gray-400">{employee.designation}</p>
                                <p className="text-sm text-gray-500 dark:text-gray-500">
                                    Employee ID: {employee.employee_id}
                                </p>
                            </div>
                        </div>

                        {/* Edit Button */}
                        {!isEditing && (
                            <button
                                onClick={() => setIsEditing(true)}
                                className="flex items-center space-x-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-xl transition-all duration-200 shadow-lg hover:shadow-xl transform hover:scale-105"
                            >
                                <Edit2 className="w-4 h-4" />
                                <span>Edit Profile</span>
                            </button>
                        )}
                    </div>
                </div>
            </div>

            {/* Profile Information */}
            <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-lg p-8">
                <form onSubmit={handleSubmit} className="space-y-6">
                    {/* Personal Information */}
                    <div>
                        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4 flex items-center space-x-2">
                            <User className="w-5 h-5 text-blue-600" />
                            <span>Personal Information</span>
                        </h2>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            {/* First Name */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                    First Name
                                </label>
                                {isEditing ? (
                                    <input
                                        type="text"
                                        name="first_name"
                                        value={formData.first_name}
                                        onChange={handleChange}
                                        className="w-full px-4 py-3 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200"
                                        required
                                    />
                                ) : (
                                    <p className="text-gray-900 dark:text-white px-4 py-3">{employee.first_name}</p>
                                )}
                            </div>

                            {/* Last Name */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                    Last Name
                                </label>
                                {isEditing ? (
                                    <input
                                        type="text"
                                        name="last_name"
                                        value={formData.last_name}
                                        onChange={handleChange}
                                        className="w-full px-4 py-3 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200"
                                        required
                                    />
                                ) : (
                                    <p className="text-gray-900 dark:text-white px-4 py-3">{employee.last_name}</p>
                                )}
                            </div>

                            {/* Email */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                    <Mail className="w-4 h-4 inline mr-1" />
                                    Work Email
                                </label>
                                <p className="text-gray-900 dark:text-white px-4 py-3">{employee.email}</p>
                            </div>

                            {/* Personal Email */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                    Personal Email
                                </label>
                                {isEditing ? (
                                    <input
                                        type="email"
                                        name="personal_email"
                                        value={formData.personal_email}
                                        onChange={handleChange}
                                        className="w-full px-4 py-3 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200"
                                    />
                                ) : (
                                    <p className="text-gray-900 dark:text-white px-4 py-3">
                                        {employee.personal_email || "Not provided"}
                                    </p>
                                )}
                            </div>

                            {/* Phone */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                    <Phone className="w-4 h-4 inline mr-1" />
                                    Phone Number
                                </label>
                                {isEditing ? (
                                    <input
                                        type="tel"
                                        name="phone"
                                        value={formData.phone}
                                        onChange={handleChange}
                                        className="w-full px-4 py-3 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200"
                                    />
                                ) : (
                                    <p className="text-gray-900 dark:text-white px-4 py-3">
                                        {employee.phone || "Not provided"}
                                    </p>
                                )}
                            </div>

                            {/* Date of Birth */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                    <Calendar className="w-4 h-4 inline mr-1" />
                                    Date of Birth
                                </label>
                                {isEditing ? (
                                    <input
                                        type="date"
                                        name="date_of_birth"
                                        value={formData.date_of_birth}
                                        onChange={handleChange}
                                        className="w-full px-4 py-3 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200"
                                    />
                                ) : (
                                    <p className="text-gray-900 dark:text-white px-4 py-3">
                                        {employee.date_of_birth || "Not provided"}
                                    </p>
                                )}
                            </div>

                            {/* Gender */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                    Gender
                                </label>
                                {isEditing ? (
                                    <select
                                        name="gender"
                                        value={formData.gender}
                                        onChange={handleChange}
                                        className="w-full px-4 py-3 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200"
                                    >
                                        <option value="">Select Gender</option>
                                        <option value="MALE">Male</option>
                                        <option value="FEMALE">Female</option>
                                        <option value="OTHER">Other</option>
                                    </select>
                                ) : (
                                    <p className="text-gray-900 dark:text-white px-4 py-3">
                                        {employee.gender || "Not provided"}
                                    </p>
                                )}
                            </div>

                            {/* Marital Status */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                    Marital Status
                                </label>
                                {isEditing ? (
                                    <select
                                        name="marital_status"
                                        value={formData.marital_status}
                                        onChange={handleChange}
                                        className="w-full px-4 py-3 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200"
                                    >
                                        <option value="">Select Status</option>
                                        <option value="single">Single</option>
                                        <option value="married">Married</option>
                                        <option value="divorced">Divorced</option>
                                        <option value="widowed">Widowed</option>
                                    </select>
                                ) : (
                                    <p className="text-gray-900 dark:text-white px-4 py-3">
                                        {employee.marital_status || "Not provided"}
                                    </p>
                                )}
                            </div>

                            {/* Nationality */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                    <MapPin className="w-4 h-4 inline mr-1" />
                                    Nationality
                                </label>
                                {isEditing ? (
                                    <input
                                        type="text"
                                        name="nationality"
                                        value={formData.nationality}
                                        onChange={handleChange}
                                        className="w-full px-4 py-3 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200"
                                    />
                                ) : (
                                    <p className="text-gray-900 dark:text-white px-4 py-3">
                                        {employee.nationality || "Not provided"}
                                    </p>
                                )}
                            </div>

                            {/* Designation */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                    <Briefcase className="w-4 h-4 inline mr-1" />
                                    Designation
                                </label>
                                {isEditing ? (
                                    <input
                                        type="text"
                                        name="designation"
                                        value={formData.designation}
                                        onChange={handleChange}
                                        className="w-full px-4 py-3 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200"
                                    />
                                ) : (
                                    <p className="text-gray-900 dark:text-white px-4 py-3">{employee.designation}</p>
                                )}
                            </div>
                        </div>
                    </div>

                    {/* Bio */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                            Bio
                        </label>
                        {isEditing ? (
                            <textarea
                                name="bio"
                                value={formData.bio}
                                onChange={handleChange}
                                rows={4}
                                className="w-full px-4 py-3 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200 resize-none"
                                placeholder="Tell us about yourself..."
                            />
                        ) : (
                            <p className="text-gray-900 dark:text-white px-4 py-3">
                                {employee.bio || "No bio provided"}
                            </p>
                        )}
                    </div>

                    {/* Action Buttons */}
                    {isEditing && (
                        <div className="flex items-center justify-end space-x-4 pt-6 border-t border-gray-200 dark:border-gray-700">
                            <button
                                type="button"
                                onClick={handleCancel}
                                disabled={loading}
                                className="px-6 py-3 rounded-xl border-2 border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 transition-all duration-200 flex items-center space-x-2"
                            >
                                <X className="w-4 h-4" />
                                <span>Cancel</span>
                            </button>

                            <button
                                type="submit"
                                disabled={loading}
                                className="px-6 py-3 rounded-xl bg-blue-600 hover:bg-blue-700 text-white transition-all duration-200 flex items-center space-x-2 shadow-lg hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                {loading ? (
                                    <>
                                        <Loader className="w-4 h-4 animate-spin" />
                                        <span>Saving...</span>
                                    </>
                                ) : (
                                    <>
                                        <Save className="w-4 h-4" />
                                        <span>Save Changes</span>
                                    </>
                                )}
                            </button>
                        </div>
                    )}
                </form>
            </div>
        </div>
    );
}

export default ProfileModuleEnhanced;
