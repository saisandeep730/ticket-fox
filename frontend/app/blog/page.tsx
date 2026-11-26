import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeft, ArrowRight, Clock } from "lucide-react";
import {
    formatPostDate,
    formatPostDateShort,
    getAllTags,
    getLeadPost,
    getSortedPosts,
} from "@/lib/blog";

const SITE_URL = (process.env.NEXT_PUBLIC_SITE_URL || "https://ticketfox.site").replace(/\/$/, "");

export const metadata: Metadata = {
    title: "The Screening Room — TicketFox writing on drops, formats and booking",
    description:
        "Practical writing on getting tickets in India: how showtimes appear, which formats sell out first, BookMyShow vs District, and why an alert beats refreshing.",
    alternates: { canonical: "/blog" },
    openGraph: {
        title: "The Screening Room — TicketFox writing",
        description:
            "Practical writing on getting tickets in India: timing, formats, sources and the habits that decide the outcome.",
        url: `${SITE_URL}/blog`,
        siteName: "TicketFox",
        type: "website",
    },
};

export default function BlogIndexPage() {
    const posts = getSortedPosts();
    const lead = getLeadPost();
    const rest = posts.filter((post) => post.slug !== lead.slug);
    const tags = getAllTags();

    return (
        <div className="page">
            <div className="container">
                <div className="page-bar">
                    <Link href="/" className="page-back">
                        <ArrowLeft className="w-4 h-4" aria-hidden="true" />
                        Back to the catalog
                    </Link>
                </div>

                <header className="page-head">
                    <h1>The Screening Room.</h1>
                    <p className="lead">
                        Practical writing on getting tickets in India — how showtimes appear, which
                        formats sell out first, and the habits that decide whether you get a seat or
                        a waitlist.
                    </p>
                </header>

                {/* The lead story */}
                <section className="band band-rule" aria-labelledby="lead-title">
                    <div className="band-head">
                        <h2 id="lead-title">Now showing.</h2>
                    </div>
                    <article className="lead-story">
                        <div className="lead-story-meta">
                            <time dateTime={lead.date}>{formatPostDate(lead.date)}</time>
                            <span className="post-card-dot" aria-hidden="true" />
                            <span className="post-card-read">
                                <Clock className="w-3.5 h-3.5" aria-hidden="true" />
                                {lead.readingMinutes} min read
                            </span>
                        </div>
                        <h3 className="lead-story-title">
                            <Link href={`/blog/${lead.slug}`}>{lead.title}</Link>
                        </h3>
                        <p className="lead-story-line">{lead.description}</p>
                        <div className="lead-story-foot">
                            <ul className="post-tags">
                                {lead.tags.map((tag) => (
                                    <li className="post-tag" key={tag}>
                                        {tag}
                                    </li>
                                ))}
                            </ul>
                            <Link href={`/blog/${lead.slug}`} className="post-card-more">
                                Read the story
                                <ArrowRight className="w-4 h-4" aria-hidden="true" />
                            </Link>
                        </div>
                    </article>
                </section>

                {/* The rest of the programme */}
                <section className="band band-rule" aria-labelledby="posts-title">
                    <div className="band-head">
                        <h2 id="posts-title">The rest of the programme.</h2>
                        <p className="band-lead">
                            {rest.length} more {rest.length === 1 ? "piece" : "pieces"} on timing,
                            sources and booking.
                        </p>
                    </div>
                    <div className="post-list">
                        {rest.map((post) => (
                            <article className="post-card" key={post.slug}>
                                <div className="post-card-meta">
                                    <time dateTime={post.date}>{formatPostDateShort(post.date)}</time>
                                    <span className="post-card-dot" aria-hidden="true" />
                                    <span className="post-card-read">
                                        <Clock className="w-3.5 h-3.5" aria-hidden="true" />
                                        {post.readingMinutes} min
                                    </span>
                                </div>
                                <h3 className="post-card-title">
                                    <Link href={`/blog/${post.slug}`}>{post.title}</Link>
                                </h3>
                                <p className="post-card-line">{post.description}</p>
                                <div className="post-card-foot">
                                    <ul className="post-tags">
                                        {post.tags.map((tag) => (
                                            <li className="post-tag" key={tag}>
                                                {tag}
                                            </li>
                                        ))}
                                    </ul>
                                    <Link href={`/blog/${post.slug}`} className="post-card-more">
                                        Read
                                        <ArrowRight className="w-4 h-4" aria-hidden="true" />
                                    </Link>
                                </div>
                            </article>
                        ))}
                    </div>
                </section>

                {/* The tag archive */}
                <section className="band band-rule" aria-labelledby="tags-title">
                    <div className="band-head">
                        <h2 id="tags-title">The archive.</h2>
                        <p className="band-lead">
                            Every topic the room has covered, with how many pieces carry it.
                        </p>
                    </div>
                    <ul className="tag-archive">
                        {tags.map((entry) => (
                            <li className="tag-archive-item" key={entry.tag}>
                                <span className="tag-archive-name">{entry.tag}</span>
                                <span className="tag-archive-count">{entry.count}</span>
                            </li>
                        ))}
                    </ul>
                </section>

                <section className="close">
                    <div className="close-inner">
                        <div>
                            <h2>Reading is good. An alert is better.</h2>
                            <p className="close-line">
                                Set a watch for the film you are waiting on, and let the engine do
                                the checking.
                            </p>
                        </div>
                        <div className="close-action">
                            <Link href="/" className="btn-primary">
                                Create a ticket watch
                            </Link>
                        </div>
                    </div>
                </section>
            </div>
        </div>
    );
}
