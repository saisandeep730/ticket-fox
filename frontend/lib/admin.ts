export const ADMIN_EMAIL = (process.env.NEXT_PUBLIC_ADMIN_EMAIL || "saisandeepy456@gmail.com").toLowerCase();
const ADMIN_UID = process.env.NEXT_PUBLIC_ADMIN_UID || "1tXP1wmqmgXhVZvOiIgDL5L8sm03";

/**
 * The public site origin. The control plane lives on admin.<domain>, so links
 * that leave the dashboard must be absolute — a relative "/" on the admin host
 * is rewritten back to the dashboard by middleware.ts.
 */
export const MAIN_SITE_URL = (process.env.NEXT_PUBLIC_SITE_URL || "https://ticketfox.site").replace(/\/$/, "");

/** Whether a signed-in Firebase user is the designated administrator. */
export function isAdminUser(user: { email?: string | null; uid?: string } | null | undefined): boolean {
    if (!user) return false;
    return user.email?.toLowerCase() === ADMIN_EMAIL || user.uid === ADMIN_UID;
}
