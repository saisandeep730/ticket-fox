"use client";

import React, { useState } from "react";
import {
  LogIn,
  Mail,
  Lock,
  X,
  UserPlus,
  Flame,
  AlertCircle,
  Loader2,
  KeyRound,
  ArrowLeft,
  CheckCircle2,
} from "lucide-react";
import {
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
} from "firebase/auth";
import { auth, firebaseConfigured } from "../lib/firebase";
import {
  requestEmailVerification,
  requestPasswordResetEmail,
} from "../lib/auth-actions";

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  onGoogleSignIn: () => void;
  onShowToast: (msg: string, type?: "success" | "error" | "info") => void;
}

type AuthMode = "signin" | "signup" | "reset";

export default function AuthModal({
  isOpen,
  onClose,
  onGoogleSignIn,
  onShowToast,
}: AuthModalProps) {
  const [mode, setMode] = useState<AuthMode>("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [resetSent, setResetSent] = useState(false);

  if (!isOpen) return null;

  const switchMode = (next: AuthMode) => {
    setMode(next);
    setError("");
    setResetSent(false);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (mode === "reset") {
      if (!email.trim()) {
        setError("Enter the email address on your account.");
        return;
      }
      setError("");
      setLoading(true);

      try {
        if (!firebaseConfigured || !auth) {
          onShowToast("Running in local demo mode. Reset link simulated.", "success");
          setResetSent(true);
          return;
        }

        // The backend mints the Firebase action link and delivers it through
        // Resend from our verified domain. We deliberately do NOT fall back to
        // Firebase's own sendPasswordResetEmail(): that would deliver Firebase's
        // default template from *.firebaseapp.com, which is exactly what this
        // integration exists to prevent. A failure surfaces as an error instead.
        await requestPasswordResetEmail(email.trim());
        setResetSent(true);
        onShowToast("Password reset link sent. Check your inbox.", "success");
      } catch (err: any) {
        console.error("Password reset error:", err);
        const code = err?.code as string | undefined;
        if (code === "auth/user-not-found") {
          setError("No account found with that email address.");
        } else if (code === "auth/invalid-email") {
          setError("That email address doesn't look right.");
        } else if (code === "auth/too-many-requests") {
          setError("Too many attempts. Please wait a moment and try again.");
        } else {
          setError(err.message?.replace("Firebase: ", "") || "Could not send the reset link.");
        }
      } finally {
        setLoading(false);
      }
      return;
    }

    if (!email.trim() || !password.trim()) {
      setError("Please fill in both email and password.");
      return;
    }
    setError("");
    setLoading(true);

    try {
      if (!firebaseConfigured || !auth) {
        onShowToast("Running in local demo mode. Sign-in complete!", "success");
        onClose();
        return;
      }

      if (mode === "signin") {
        await signInWithEmailAndPassword(auth, email.trim(), password);
        onShowToast("Signed in successfully!", "success");
      } else {
        await createUserWithEmailAndPassword(auth, email.trim(), password);
        onShowToast("Account created successfully! Welcome to TicketFox.", "success");
        // Best-effort branded verification email; never block sign-up on it.
        requestEmailVerification(email.trim()).catch((err) =>
          console.warn("Verification email could not be sent:", err)
        );
      }
      onClose();
    } catch (err: any) {
      console.error("Auth error:", err);
      const msg = err.message?.replace("Firebase: ", "") || "Authentication failed.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const isReset = mode === "reset";

  return (
    <div role="dialog" aria-modal="true" className="modal-backdrop">
      <div className="modal-panel modal-panel--md">
        <div className="modal-body modal-stack">
          {/* Close Button */}
          <button onClick={onClose} aria-label="Close dialog" className="modal-close">
            <X className="w-4 h-4" aria-hidden="true" />
          </button>

          {/* Brand Header */}
          <div className="modal-brand">
            <div className="modal-brand-icon">
              {isReset ? (
                <KeyRound className="w-6 h-6" aria-hidden="true" />
              ) : (
                <Flame className="w-6 h-6" aria-hidden="true" />
              )}
            </div>
            <h3 className="modal-title">
              {isReset
                ? "Reset Your Password"
                : mode === "signin"
                  ? "Welcome Back to TicketFox"
                  : "Create TicketFox Account"}
            </h3>
            <p className="modal-subtitle">
              {isReset
                ? "We'll email you a secure link to set a new password"
                : "Sync your real-time cinema ticket watches across all your devices"}
            </p>
          </div>

          {/* Google Sign-In + divider (hidden while resetting) */}
          {!isReset && (
            <div className="modal-stack">
              <button type="button" onClick={onGoogleSignIn} className="modal-google">
                <svg className="w-4 h-4 shrink-0" viewBox="0 0 24 24" aria-hidden="true">
                  <path
                    fill="#4285F4"
                    d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                  />
                  <path
                    fill="#34A853"
                    d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                  />
                  <path
                    fill="#FBBC05"
                    d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
                  />
                  <path
                    fill="#EA4335"
                    d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
                  />
                </svg>
                <span>Continue with Google</span>
              </button>

              <div className="modal-divider">
                <span>Or with email</span>
              </div>
            </div>
          )}

          {/* Mode Toggle Tabs (hidden while resetting) */}
          {!isReset && (
            <div className="modal-tabs">
              <button
                type="button"
                onClick={() => switchMode("signin")}
                className={`modal-tab${mode === "signin" ? " is-active" : ""}`}
              >
                Sign In
              </button>
              <button
                type="button"
                onClick={() => switchMode("signup")}
                className={`modal-tab${mode === "signup" ? " is-active" : ""}`}
              >
                Create Account
              </button>
            </div>
          )}

          {error && (
            <div className="modal-error">
              <AlertCircle className="w-4 h-4 shrink-0" aria-hidden="true" />
              <span>{error}</span>
            </div>
          )}

          {isReset && resetSent ? (
            <div className="modal-stack">
              <div className="modal-success">
                <CheckCircle2 className="w-4 h-4 shrink-0" aria-hidden="true" />
                <span>
                  If an account exists for <strong>{email.trim()}</strong>, a reset link is on its
                  way. Check your inbox and spam folder.
                </span>
              </div>

              <button type="button" onClick={() => switchMode("signin")} className="modal-submit">
                <ArrowLeft className="w-4 h-4" aria-hidden="true" />
                <span>Back to sign in</span>
              </button>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="modal-stack">
              <div>
                <label className="field-label flex items-center gap-1.5">
                  <Mail className="w-3.5 h-3.5 text-muted" aria-hidden="true" />
                  <span>Email Address</span>
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@example.com"
                  className="field-input"
                  autoComplete="email"
                  required
                />
              </div>

              {!isReset && (
                <div>
                  <div className="field-label-row">
                    <label className="field-label flex items-center gap-1.5">
                      <Lock className="w-3.5 h-3.5 text-muted" aria-hidden="true" />
                      <span>Password</span>
                    </label>
                    {mode === "signin" && (
                      <button
                        type="button"
                        onClick={() => switchMode("reset")}
                        className="modal-link"
                      >
                        Forgot password?
                      </button>
                    )}
                  </div>
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className="field-input"
                    autoComplete={mode === "signin" ? "current-password" : "new-password"}
                    required
                  />
                </div>
              )}

              <button type="submit" disabled={loading} className="modal-submit">
                {loading ? (
                  <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
                ) : isReset ? (
                  <KeyRound className="w-4 h-4" aria-hidden="true" />
                ) : mode === "signin" ? (
                  <LogIn className="w-4 h-4" aria-hidden="true" />
                ) : (
                  <UserPlus className="w-4 h-4" aria-hidden="true" />
                )}
                <span>
                  {isReset
                    ? "Send reset link"
                    : mode === "signin"
                      ? "Sign In"
                      : "Create Account"}
                </span>
              </button>

              {isReset && (
                <button
                  type="button"
                  onClick={() => switchMode("signin")}
                  className="modal-back"
                >
                  <ArrowLeft className="w-3.5 h-3.5" aria-hidden="true" />
                  <span>Back to sign in</span>
                </button>
              )}
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
