/**
 * Single source of truth for Indian mobile-number handling in the UI.
 *
 * The backend stores numbers as `+91XXXXXXXXXX`; the forms edit the bare
 * 10 digits. Every component must go through these two helpers so the rules
 * never drift apart.
 */

/** Reduce any stored/typed number to its 10 significant digits. */
export function toIndianDigits(value: string): string {
    const digits = (value || "").replace(/\D/g, "");
    if (digits.length === 12 && digits.startsWith("91")) {
        return digits.slice(2);
    }
    if (digits.length === 11 && digits.startsWith("0")) {
        return digits.slice(1);
    }
    return digits.slice(-10);
}

/** Format 10 digits as the canonical `+91XXXXXXXXXX` the API expects. */
export function toE164India(digits: string): string {
    return `+91${(digits || "").replace(/\D/g, "").slice(-10)}`;
}
