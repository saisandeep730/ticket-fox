import { apiFetch } from "./api";

/**
 * Ask the backend to email a branded password-reset link.
 *
 * The backend mints the Firebase action link and sends it through Resend from
 * the verified domain, so the mail is on-brand instead of Firebase's default
 * template. Throws `ApiError` when the backend is unreachable or refuses.
 */
export async function requestPasswordResetEmail(email: string): Promise<void> {
    await apiFetch("/auth/password-reset", {
        method: "POST",
        body: JSON.stringify({ email }),
    });
}

/**
 * Ask the backend to email a branded email-verification link (sent right after
 * sign-up). Throws `ApiError` on failure; callers treat it as best-effort.
 */
export async function requestEmailVerification(email: string): Promise<void> {
    await apiFetch("/auth/verify-email", {
        method: "POST",
        body: JSON.stringify({ email }),
    });
}
