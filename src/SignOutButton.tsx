```

"use client";
import { useEffect, useState, useCallback } from "react";
import { toast } from "sonner";

export function SignOutButton() {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);

  // derive auth state from presence of access token
  useEffect(() => {
    const check = () => setIsAuthenticated(!!localStorage.getItem("access_token"));
    check();
    // keep it in sync if other tabs log in/out
    window.addEventListener("storage", check);
    return () => window.removeEventListener("storage", check);
  }, []);

  const signOut = useCallback(() => {
    try {
      localStorage.removeItem("access_token");
      // if you’re using refresh tokens, clear them too:
      localStorage.removeItem("refresh_token");
      setIsAuthenticated(false);
      toast.success("Signed out successfully.");
      // optional: redirect after sign out
      // window.location.href = "/login";
    } catch (err) {
      toast.error("Failed to sign out. Please try again.");
    }
  }, []);

  if (!isAuthenticated) return null;

  return (
    <button
      className="px-4 py-2 rounded bg-white text-secondary border border-gray-200 font-semibold hover:bg-gray-50 hover:text-secondary-hover transition-colors shadow-sm hover:shadow"
      onClick={signOut}
    >
      Sign out
    </button>
  );
}
```