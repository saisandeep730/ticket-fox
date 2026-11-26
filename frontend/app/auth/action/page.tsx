"use client";

import React, { Suspense, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
    ArrowLeft,
    AlertCircle,
    CheckCircle2,
    KeyRound,
    Loader2,
    Lock,
    Mail,
} from "lucide-react";
import {
    applyActionCode,
    confirmPasswordReset,
    verifyPasswordResetCode,
} from "firebase/auth";
import { auth, firebaseConfigured } from "../../../lib/firebase";
import TicketFoxLogo from "../../../components/TicketFoxLogo";

type Phase = "verifying" | "form" | "done" | "invalid" | "verified";

function AuthActionInner() {
    const searchParams = useSearchParams();
    const mode = searchParams.get("mode");
    const oobCode = searchParams.get("oobCode");

    const [phase, setPhase] = useState<Phase>("verifying");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [confirm, setConfirm] = useState("");
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        let cancelled = false;

        async function verify() {
            if (!oobCode || (mode !== "resetPassword" && mode !== "verifyEmail")) {
                if (!cancelled) {
                    setError(
                        "This link is missing its code or has already been used. Request a new one from the sign-in screen."
                    );
                    setPhase("invalid");
                }
                return;
            }

            if (!firebaseConfigured || !auth) {
                // Demo mode: no Firebase project, so just show the form.
                if (!cancelled) setPhase(mode === "verifyEmail" ? "verified" : "form");
                return;
            }

            try {
                if (mode === "verifyEmail") {
                    // Confirms the address and consumes the one-time code.
                    await applyActionCode(auth, oobCode);
                    if (!cancelled) setPhase("verified");
                    return;
                }

                const accountEmail = await verifyPasswordResetCode(auth, oobCode);
                if (cancelled) return;
                setEmail(accountEmail);
                setPhase("form");
            } catch (err: any) {
                if (cancelled) return;
                const code = err?.code as string | undefined;
                if (code === "auth/expired-action-code") {
                    setError("This link has expired. Request a new one from the sign-in screen.");
                } else if (code === "auth/invalid-action-code") {
                    setError("This link is invalid or has already been used.");
                } else {
                    setError(err.message?.replace("Firebase: ", "") || "This link could not be verified.");
                }
                setPhase("invalid");
            }
        }

        verify();
        return () => {
            cancelled = true;
        };
    }, [mode, oobCode]);

    const handleSubmit = useCallback(
        async (e: React.FormEvent) => {
            e.preventDefault();
            setError("");

            if (password.length < 6) {
                setError("Use at least 6 characters for your new password.");
                return;
            }
            if (password !== confirm) {
                setError("The two passwords don't match.");
                return;
            }
            if (!oobCode) {
                setError("This reset link is missing its code. Request a new one.");
                return;
            }

            setLoading(true);
            try {
                if (!firebaseConfigured || !auth) {
                    setPhase("done");
                    return;
                }
                await confirmPasswordReset(auth, oobCode, password);
                setPhase("done");
            } catch (err: any) {
                const code = err?.code as string | undefined;
                if (code === "auth/expired-action-code") {
                    setError("This reset link has expired. Request a new one from the sign-in screen.");
                } else if (code === "auth/weak-password") {
                    setError("That password is too weak. Try a longer one.");
                } else {
                    setError(err.message?.replace("Firebase: ", "") || "Could not reset your password.");
                }
            } finally {
                setLoading(false);
            }
        },
        [password, confirm, oobCode]
    );

    return (
        <div className="page">
            <div className="container">
                <div className="page-bar">
                    <Link href="/" className="page-back">
                        <ArrowLeft className="w-4 h-4" aria-hidden="true" />
                        <span>Back to home</span>
                    </Link>
                    <TicketFoxLogo size="sm" />
                </div>

                <div className="auth-action">
                    <div className="auth-action-card">
                        <div className="modal-brand">
                            <div className="modal-brand-icon">
                                {phase === "done" || phase === "verified" ? (
                                    <CheckCircle2 className="w-6 h-6" aria-hidden="true" />
                                ) : phase === "invalid" ? (
                                    <AlertCircle className="w-6 h-6" aria-hidden="true" />
                                ) : (
                                    <KeyRound className="w-6 h-6" aria-hidden="true" />
                                )}
                            </div>
                            <h1 className="modal-title">
                                {phase === "done"
                                    ? "Password updated"
                                    : phase === "verified"
                                        ? "Email confirmed"
                                        : phase === "invalid"
                                            ? "Link not valid"
                                            : mode === "verifyEmail"
                                                ? "Confirm your email"
                                                : "Set a new password"}
                            </h1>
                            <p className="modal-subtitle">
                                {phase === "done"
                                    ? "You can now sign in with your new password."
                                    : phase === "verified"
                                        ? "Your email address is confirmed. You're all set."
                                        : phase === "invalid"
                                            ? "Request a fresh link from the sign-in screen and try again."
                                            : mode === "verifyEmail"
                                                ? "Confirming your TicketFox email address…"
                                                : email
                                                    ? `Choose a new password for ${email}`
                                                    : "Choose a new password for your TicketFox account"}
                            </p>
                        </div>

                        {phase === "verifying" && (
                            <div className="modal-loading">
                                <Loader2 className="w-5 h-5 animate-spin" aria-hidden="true" />
                                <span>Checking your reset link…</span>
                            </div>
                        )}

                        {phase === "invalid" && (
                            <>
                                <div className="modal-error">
                                    <AlertCircle className="w-4 h-4 shrink-0" aria-hidden="true" />
                                    <span>{error || "This reset link is no longer valid."}</span>
                                </div>
                                <Link href="/" className="modal-submit">
                                    <ArrowLeft className="w-4 h-4" aria-hidden="true" />
                                    <span>Back to sign in</span>
                                </Link>
                            </>
                        )}

                        {phase === "form" && (
                            <form onSubmit={handleSubmit} className="modal-stack">
                                {error && (
                                    <div className="modal-error">
                                        <AlertCircle className="w-4 h-4 shrink-0" aria-hidden="true" />
                                        <span>{error}</span>
                                    </div>
                                )}

                                {email && (
                                    <div className="auth-action-email">
                                        <Mail className="w-3.5 h-3.5" aria-hidden="true" />
                                        <span>{email}</span>
                                    </div>
                                )}

                                <div>
                                    <label className="field-label flex items-center gap-1.5">
                                        <Lock className="w-3.5 h-3.5 text-muted" aria-hidden="true" />
                                        <span>New password</span>
                                    </label>
                                    <input
                                        type="password"
                                        value={password}
                                        onChange={(e) => setPassword(e.target.value)}
                                        placeholder="••••••••"
                                        className="field-input"
                                        autoComplete="new-password"
                                        minLength={6}
                                        required
                                    />
                                    <p className="field-hint">At least 6 characters.</p>
                                </div>

                                <div>
                                    <label className="field-label flex items-center gap-1.5">
                                        <Lock className="w-3.5 h-3.5 text-muted" aria-hidden="true" />
                                        <span>Confirm new password</span>
                                    </label>
                                    <input
                                        type="password"
                                        value={confirm}
                                        onChange={(e) => setConfirm(e.target.value)}
                                        placeholder="••••••••"
                                        className="field-input"
                                        autoComplete="new-password"
                                        minLength={6}
                                        required
                                    />
                                </div>

                                <button type="submit" disabled={loading} className="modal-submit">
                                    {loading ? (
                                        <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
                                    ) : (
                                        <KeyRound className="w-4 h-4" aria-hidden="true" />
                                    )}
                                    <span>Update password</span>
                                </button>
                            </form>
                        )}

                        {phase === "done" && (
                            <Link href="/" className="modal-submit">
                                <ArrowLeft className="w-4 h-4" aria-hidden="true" />
                                <span>Continue to TicketFox</span>
                            </Link>
                        )}

                        {phase === "verified" && (
                            <Link href="/" className="modal-submit">
                                <ArrowLeft className="w-4 h-4" aria-hidden="true" />
                                <span>Continue to TicketFox</span>
                            </Link>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}

export default function AuthActionPage() {
    return (
        <Suspense
            fallback={
                <div className="page">
                    <div className="container">
                        <div className="modal-loading">
                            <Loader2 className="w-5 h-5 animate-spin" aria-hidden="true" />
                            <span>Loading…</span>
                        </div>
                    </div>
                </div>
            }
        >
            <AuthActionInner />
        </Suspense>
    );
}
