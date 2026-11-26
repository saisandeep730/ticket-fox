import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft, ArrowRight, Clock } from "lucide-react";
import {
    BLOG_POSTS,
    formatPostDate,
    getAdjacentPosts,
    getPostBySlug,
    getPostHeadings,
    slugifyHeading,
} from "@/lib/blog";
import ReadingProgress from "./ReadingProgress";

const SITE_URL = (process.env.NEXT_PUBLIC_SITE_URL || "https://ticketfox.site").replace(/\/$/, "");

interface PageProps {
    params: { slug: string };
}

export function generateStaticParams() {
    return BLOG_POSTS.map((post) => ({ slug: post.slug }));
}

export function generateMetadata({ params }: PageProps): Metadata {
    const post = getPostBySlug(params.slug);
    if (!post) {
        return { title: "Article not found — TicketFox" };
    }
    const url = `${SITE_URL}/blog/${post.slug}`;
    return {
        title: `${post.title} — TicketFox`,
        description: post.description,
        alternates: { canonical: `/blog/${post.slug}` },
        openGraph: {
            title: post.title,
            description: post.description,
            url,
            siteName: "TicketFox",
            type: "article",
            publishedTime: post.date,
            tags: post.tags,
        },
    };
}

export default function BlogPostPage({ params }: PageProps) {
    const post = getPostBySlug(params.slug);
    if (!post) notFound();

    const headings = getPostHeadings(post);
    const { previous, next } = getAdjacentPosts(post.slug);
    const others = BLOG_POSTS.filter((p) => p.slug !== post.slug).slice(0, 2);

    const jsonLd = {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        headline: post.title,
        description: post.description,
        datePublished: post.date,
        author: {
            "@type": "Person",
            name: "Y Sai Sandeep",
        },
        publisher: {
            "@type": "Organization",
            name: "TicketFox",
        },
        keywords: post.tags.join(", "),
        mainEntityOfPage: {
            "@type": "WebPage",
            "@id": `${SITE_URL}/blog/${post.slug}`,
        },
    };

    return (
        <div className="page">
            <script
                type="application/ld+json"
                dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
            />
            <ReadingProgress targetId="post-body" />
            <div className="container">
                <div className="page-bar">
                    <Link href="/blog" className="page-back">
                        <ArrowLeft className="w-4 h-4" aria-hidden="true" />
                        All articles
                    </Link>
                </div>

                <article className="post">
                    <header className="post-head">
                        <div className="post-card-meta">
                            <time dateTime={post.date}>{formatPostDate(post.date)}</time>
                            <span className="post-card-dot" aria-hidden="true" />
                            <span className="post-card-read">
                                <Clock className="w-3.5 h-3.5" aria-hidden="true" />
                                {post.readingMinutes} min read
                            </span>
                        </div>
                        <h1 className="post-title">{post.title}</h1>
                        <p className="post-lede">{post.description}</p>
                        <ul className="post-tags">
                            {post.tags.map((tag) => (
                                <li className="post-tag" key={tag}>
                                    {tag}
                                </li>
                            ))}
                        </ul>
                    </header>

                    <div className="post-layout">
                        {headings.length > 1 && (
                            <nav className="post-toc" aria-label="On this page">
                                <p className="post-toc-head">On this page</p>
                                <ol className="post-toc-list">
                                    {headings.map((h) => (
                                        <li className="post-toc-item" key={h.id}>
                                            <a className="post-toc-link" href={`#${h.id}`}>
                                                {h.heading}
                                            </a>
                                        </li>
                                    ))}
                                </ol>
                            </nav>
                        )}

                        <div className="post-body" id="post-body">
                            {post.sections.map((section, idx) => (
                                <section className="post-section" key={idx}>
                                    {section.heading && (
                                        <h2
                                            className="post-section-title"
                                            id={slugifyHeading(section.heading)}
                                        >
                                            {section.heading}
                                        </h2>
                                    )}
                                    {section.paragraphs?.map((p, i) => (
                                        <p className="post-line" key={i}>
                                            {p}
                                        </p>
                                    ))}
                                    {section.list && (
                                        <ul className="post-list-items">
                                            {section.list.map((item, i) => (
                                                <li key={i}>{item}</li>
                                            ))}
                                        </ul>
                                    )}
                                    {section.quote && (
                                        <blockquote className="post-quote">{section.quote}</blockquote>
                                    )}
                                </section>
                            ))}
                        </div>
                    </div>

                    <footer className="post-foot">
                        <div className="post-cta">
                            <h2>Never miss the drop again</h2>
                            <p>
                                Set a watch for the film, city and formats you care about. The engine
                                polls BookMyShow and District and messages you the moment a matching
                                show opens.
                            </p>
                            <Link href="/" className="btn-primary">
                                Create a ticket watch
                            </Link>
                        </div>
                    </footer>
                </article>

                {/* Prev / next */}
                {(previous || next) && (
                    <nav className="post-nav" aria-label="More articles">
                        {previous ? (
                            <Link href={`/blog/${previous.slug}`} className="post-nav-link">
                                <span className="post-nav-dir">
                                    <ArrowLeft className="w-3.5 h-3.5" aria-hidden="true" />
                                    Older
                                </span>
                                <span className="post-nav-title">{previous.title}</span>
                            </Link>
                        ) : (
                            <span />
                        )}
                        {next ? (
                            <Link href={`/blog/${next.slug}`} className="post-nav-link is-next">
                                <span className="post-nav-dir">
                                    Newer
                                    <ArrowRight className="w-3.5 h-3.5" aria-hidden="true" />
                                </span>
                                <span className="post-nav-title">{next.title}</span>
                            </Link>
                        ) : (
                            <span />
                        )}
                    </nav>
                )}

                {others.length > 0 && (
                    <section className="band band-rule" aria-labelledby="more-posts-title">
                        <div className="band-head">
                            <h2 id="more-posts-title">Keep reading.</h2>
                        </div>
                        <div className="post-list">
                            {others.map((other) => (
                                <article className="post-card" key={other.slug}>
                                    <div className="post-card-meta">
                                        <time dateTime={other.date}>{formatPostDate(other.date)}</time>
                                        <span className="post-card-dot" aria-hidden="true" />
                                        <span className="post-card-read">
                                            <Clock className="w-3.5 h-3.5" aria-hidden="true" />
                                            {other.readingMinutes} min
                                        </span>
                                    </div>
                                    <h3 className="post-card-title">
                                        <Link href={`/blog/${other.slug}`}>{other.title}</Link>
                                    </h3>
                                    <p className="post-card-line">{other.description}</p>
                                    <div className="post-card-foot">
                                        <ul className="post-tags">
                                            {other.tags.map((tag) => (
                                                <li className="post-tag" key={tag}>
                                                    {tag}
                                                </li>
                                            ))}
                                        </ul>
                                        <Link href={`/blog/${other.slug}`} className="post-card-more">
                                            Read
                                            <ArrowRight className="w-4 h-4" aria-hidden="true" />
                                        </Link>
                                    </div>
                                </article>
                            ))}
                        </div>
                    </section>
                )}
            </div>
        </div>
    );
}
