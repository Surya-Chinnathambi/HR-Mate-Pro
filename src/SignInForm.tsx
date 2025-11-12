```

"use client";
import apiClient from "./api/client";
import { useState } from "react";
import { toast } from "sonner";
import { motion } from "framer-motion";
import { LogIn, UserPlus, Ghost } from "lucide-react";

export function SignInForm() {
  const [flow, setFlow] = useState<"signIn" | "signUp">("signIn");
  const [submitting, setSubmitting] = useState(false);

  const handleAuth = async (email: string, password: string) => {
    if (flow === "signIn") {
      // LOGIN — x-www-form-urlencoded (FastAPI OAuth2-compatible)
      const formData = new FormData();
      formData.append("username", email);
      formData.append("password", password);

      const response = await apiClient.post("/auth/login", formData, {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
      });

      localStorage.setItem("access_token", response.data.access_token);
      if (response.data.refresh_token) {
        localStorage.setItem("refresh_token", response.data.refresh_token);
      }
      toast.success("Welcome back!");
      // optional: redirect
      // window.location.href = "/";
      return;
    }

    // SIGN UP — adjust endpoint/body to match your FastAPI implementation
    // If your FastAPI expects JSON:
    const response = await apiClient.post("/auth/register", {
      email,
      password,
    });

    // Option A: your API logs in on successful sign-up and returns tokens
    if (response.data?.access_token) {
      localStorage.setItem("access_token", response.data.access_token);
      if (response.data.refresh_token) {
        localStorage.setItem("refresh_token", response.data.refresh_token);
      }
      toast.success("Account created. You’re signed in!");
      // window.location.href = "/";
      return;
    }

    // Option B: require a separate login after sign-up
    toast.success("Account created. Please sign in.");
    setFlow("signIn");
  };

  return (
    <div className="flex items-center justify-center w-full min-h-screen bg-gray-100 dark:bg-gray-900">
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: "easeOut" }}
        className="w-full max-w-md p-8 space-y-6 bg-white rounded-2xl shadow-xl dark:bg-gray-800"
      >
        <h2 className="text-3xl font-bold text-center text-gray-900 dark:text-white">
          {flow === "signIn" ? "Welcome Back" : "Create Account"}
        </h2>

        <form
          className="space-y-6"
          onSubmit={async (e) => {
            e.preventDefault();
            if (submitting) return;
            setSubmitting(true);

            const form = e.target as HTMLFormElement;
            const email = (form.elements.namedItem("email") as HTMLInputElement)
              .value;
            const password = (
              form.elements.namedItem("password") as HTMLInputElement
            ).value;

            try {
              await handleAuth(email, password);
            } catch (error: any) {
              // basic error mapping; tweak to your API’s shape
              const msg =
                error?.response?.data?.detail ??
                (flow === "signIn"
                  ? "Could not sign in. Check your credentials."
                  : "Could not sign up. Do you already have an account?");
              toast.error(msg);
            } finally {
              setSubmitting(false);
            }
          }}
        >
          <div>
            <label htmlFor="email" className="sr-only">
              Email
            </label>
            <input
              id="email"
              className="w-full px-4 py-3 text-gray-900 bg-gray-100 border-transparent rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white dark:bg-gray-700 dark:text-white dark:focus:bg-gray-600"
              type="email"
              name="email"
              placeholder="Email"
              required
              disabled={submitting}
              autoComplete="email"
            />
          </div>

          <div>
            <label htmlFor="password" className="sr-only">
              Password
            </label>
            <input
              id="password"
              className="w-full px-4 py-3 text-gray-900 bg-gray-100 border-transparent rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white dark:bg-gray-700 dark:text-white dark:focus:bg-gray-600"
              type="password"
              name="password"
              placeholder="Password"
              required
              disabled={submitting}
              autoComplete={flow === "signIn" ? "current-password" : "new-password"}
            />
          </div>

          <button
            className="w-full flex justify-center items-center gap-2 py-3 px-4 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
            type="submit"
            disabled={submitting}
          >
            {flow === "signIn" ? <LogIn size={18} /> : <UserPlus size={18} />}
            {flow === "signIn" ? "Sign in" : "Sign up"}
          </button>

          <div className="text-center text-sm text-gray-600 dark:text-gray-400">
            <span>
              {flow === "signIn"
                ? "Don't have an account? "
                : "Already have an account? "}
            </span>
            <button
              type="button"
              className="font-medium text-blue-600 hover:underline focus:outline-none dark:text-blue-400"
              onClick={() => setFlow(flow === "signIn" ? "signUp" : "signIn")}
            >
              {flow === "signIn" ? "Sign up" : "Sign in"}
            </button>
          </div>
        </form>

        <div className="flex items-center justify-center">
          <hr className="w-full border-t border-gray-300 dark:border-gray-600" />
          <span className="px-4 text-sm font-medium text-gray-500 dark:text-gray-400">
            OR
          </span>
          <hr className="w-full border-t border-gray-300 dark:border-gray-600" />
        </div>

        {/* Anonymous sign-in usually isn't part of a typical FastAPI flow.
            Disable it or wire it to a guest token endpoint if you have one. */}
        <button
          className="w-full flex justify-center items-center gap-2 py-3 px-4 bg-gray-200 text-gray-800 rounded-lg font-semibold dark:bg-gray-700 dark:text-white"
          type="button"
          disabled
          title="Anonymous sign-in not available"
        >
          <Ghost size={18} />
          Sign in anonymously (disabled)
        </button>
      </motion.div>
    </div>
  );
}
```