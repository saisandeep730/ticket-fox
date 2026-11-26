import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeft, ArrowRight, Compass, HelpCircle, Newspaper } from "lucide-react";

export const metadata: Metadata = {
    title: "404 — This showtime does not exist",
    description:
        "The page you asked for is not on the board. Head back to the catalog, or read how the watch engine works.",
    robots: { index: false, follow: true },
};

/** The struck board — showtimes that were never scheduled. */
const STRUCK: { time: string; title: string; screen: string }[] = [
    { time: "09:15", title: "The Page You Wanted", screen: "Screen 404" },
    { time: "12:40", title: "A Link That Expired", screen: "Screen 404" },
    { time: "18:05", title: "Something You Typed", screen: "Screen 404" },
    { time: "22:30", title: "A Show That Never Opened", screen: "Screen 404" },
];

export default function NotFound() {
    return (
        <div className="page">
            <div className="container">
                <div className="page-bar">
                    <Link href="/" className="page-back">
                        <ArrowLeft className="w-4 h-4" aria-hidden="true" />
                        Back to the catalog
                    </Link>
                </div>

                <section className="dead" aria-labelledby="nf-title">
                    {/* The marquee */}
                    <div className="dead-marquee" aria-hidden="true">
                        <span className="dead-marquee-track">
                            NO SHOW &nbsp;·&nbsp; NO SHOW &nbsp;·&nbsp; NO SHOW &nbsp;·&nbsp; NO SHOW
                            &nbsp;·&nbsp; NO SHOW &nbsp;·&nbsp; NO SHOW &nbsp;·&nbsp; NO SHOW
                            &nbsp;·&nbsp; NO SHOW &nbsp;·&nbsp;
                        </span>
                    </div>

                    <div className="dead-body">
                        <p className="dead-code" aria-hidden="true">
                            404
                        </p>
                        <h1 className="dead-title" id="nf-title">
                            This showtime does not exist.
                        </h1>
                        <p className="dead-line">
                            The page you asked for is not on the board. It may have been renamed,
                            removed, or it never opened in the first place. The catalog is still
                            running.
                        </p>

                        <div className="dead-actions">
                            <Link href="/" className="btn-primary">
                                Back to the catalog
                            </Link>
                            <Link href="/blog" className="contact-link">
                                <Newspaper className="w-4 h-4" aria-hidden="true" />
                                Read the blog
                            </Link>
                        </div>
                    </div>

                    {/* The struck board */}
                    <div className="dead-board">
                        <div className="dead-board-head">
                            <span className="dead-board-label">Today&rsquo;s board</span>
                            <span className="dead-board-status">Cancelled</span>
                        </div>
                        <ul className="dead-board-list">
                            {STRUCK.map((row) => (
                                <li className="dead-row" key={row.time}>
                                    <span className="dead-row-time">{row.time}</span>
                                    <span className="dead-row-title">{row.title}</span>
                                    <span className="dead-row-screen">{row.screen}</span>
                                </li>
                            ))}
                        </ul>
                    </div>

                    <nav className="dead-links" aria-label="Useful pages">
                        <Link href="/how-it-works" className="contact-link">
                            <Compass className="w-4 h-4" aria-hidden="true" />
                            How it works
                        </Link>
                        <Link href="/faq" className="contact-link">
                            <HelpCircle className="w-4 h-4" aria-hidden="true" />
                            FAQ
                        </Link>
                        <Link href="/about" className="contact-link">
                            About
                            <ArrowRight className="w-4 h-4" aria-hidden="true" />
                        </Link>
                    </nav>
                </section>
            </div>
        </div>
    );
}
