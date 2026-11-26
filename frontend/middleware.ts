import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/**
 * Subdomain routing for the control plane.
 *
 *   admin.<domain>  →  the admin dashboard (rewritten to /admin)
 *   <domain>/admin  →  redirected to admin.<domain>
 *
 * The admin host is derived from the request itself (any hostname beginning
 * with "admin."), so no environment variable is required and the same build
 * works on localhost, a staging host and production.
 */

const ADMIN_PREFIX = "admin.";

function hostnameOf(req: NextRequest): string {
    const raw = req.headers.get("host") || req.nextUrl.hostname || "";
    return raw.split(":")[0].toLowerCase();
}

function isIpAddress(host: string): boolean {
    return /^\d{1,3}(\.\d{1,3}){3}$/.test(host) || host.includes(":");
}

export function middleware(req: NextRequest) {
    const hostname = hostnameOf(req);
    const { pathname } = req.nextUrl;
    const onAdminHost = hostname.startsWith(ADMIN_PREFIX);

    if (onAdminHost) {
        // Everything on the admin host is the control plane. "/" and any unknown
        // path are rewritten to /admin so the dashboard is the only surface here.
        if (pathname === "/admin" || pathname.startsWith("/admin/")) {
            return NextResponse.next();
        }

        const url = req.nextUrl.clone();
        url.pathname = "/admin";
        return NextResponse.rewrite(url);
    }

    // Main site: the control plane is not reachable from here.
    if (pathname === "/admin" || pathname.startsWith("/admin/")) {
        // An IP host has no subdomain to redirect to — answer with a plain 404.
        if (isIpAddress(hostname)) {
            return new NextResponse("Not found", { status: 404 });
        }

        const url = req.nextUrl.clone();
        url.hostname = `${ADMIN_PREFIX}${hostname}`;
        // Drop the internal port (the app listens on :3000 behind Caddy) so the
        // redirect lands on the public https origin, not admin.<host>:3000.
        url.port = "";
        url.pathname = "/";
        return NextResponse.redirect(url);
    }

    return NextResponse.next();
}

export const config = {
    // Skip Next internals, the API proxy, and static files so the middleware only
    // runs on real page navigations.
    matcher: [
        "/((?!api|_next/static|_next/image|favicon.ico|logo.jpg|sitemap.xml|robots.txt|.*\\.(?:png|jpg|jpeg|svg|webp|ico|css|js|woff2?)$).*)",
    ],
};
