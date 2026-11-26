import type { MetadataRoute } from "next";
import { BLOG_POSTS } from "../lib/blog";

/**
 * The public origin. Set NEXT_PUBLIC_SITE_URL in the environment (e.g.
 * https://ticketfox.site) so the sitemap emits absolute URLs. Falls back to the
 * production domain so a build without the variable still produces a valid file.
 */
const SITE_URL = (process.env.NEXT_PUBLIC_SITE_URL || "https://ticketfox.site").replace(/\/$/, "");

export default function sitemap(): MetadataRoute.Sitemap {
    const now = new Date();

    const staticRoutes: MetadataRoute.Sitemap = [
        { url: `${SITE_URL}/`, lastModified: now, changeFrequency: "daily", priority: 1 },
        { url: `${SITE_URL}/how-it-works`, lastModified: now, changeFrequency: "monthly", priority: 0.8 },
        { url: `${SITE_URL}/about`, lastModified: now, changeFrequency: "monthly", priority: 0.7 },
        { url: `${SITE_URL}/faq`, lastModified: now, changeFrequency: "monthly", priority: 0.7 },
        { url: `${SITE_URL}/blog`, lastModified: now, changeFrequency: "weekly", priority: 0.8 },
    ];

    const postRoutes: MetadataRoute.Sitemap = BLOG_POSTS.map((post) => ({
        url: `${SITE_URL}/blog/${post.slug}`,
        lastModified: new Date(`${post.date}T00:00:00Z`),
        changeFrequency: "monthly",
        priority: 0.6,
    }));

    return [...staticRoutes, ...postRoutes];
}
