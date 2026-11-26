"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, ChevronDown, Mail, Github, Send } from "lucide-react";
import TicketFoxLogo from "../../components/TicketFoxLogo";
import { FALLBACK_CITIES, loadCities, type City } from "../../lib/cities";

interface FAQItem {
    question: string;
    answer: string;
    tag: string;
}

const FAQS: FAQItem[] = [
    {
        tag: "Alerts and speed",
        question: "How fast does TicketFox detect when tickets drop?",
        answer:
            "The backend worker polls BookMyShow and District continuously, using browser impersonation that gets past Cloudflare challenge gates. The second showtimes appear, or a booking status shifts to available, an alert is dispatched to your WhatsApp and email.",
    },
    {
        tag: "Booking",
        question: "Does TicketFox book the tickets automatically for me?",
        answer:
            "No. TicketFox is a real-time intelligence and alert engine. It never asks for your payment details or your BookMyShow credentials. When tickets drop, it sends an alert with a direct link, so you can pick your seats and check out in the cinema's own app.",
    },
    {
        tag: "Channels",
        question: "How do I configure WhatsApp and email notifications?",
        answer:
            "Open Settings in the top navigation, or in the bottom bar on a phone. Enter your 10-digit Indian mobile number (the +91 is fixed) and an optional email address. You can test the setup immediately with Send test drill, which confirms delivery.",
    },
    {
        tag: "Filters",
        question: "Can I watch for specific formats like IMAX 3D, 4DX, or evening shows?",
        answer:
            "Yes. When you create a watch, you can narrow it by cinema hall, by date (premiere night, release day, or a custom date on the calendar), by time slot (morning, matinee, evening, night) and by format such as IMAX 3D, 4DX or 2D. You are only alerted when a matching show opens.",
    },
    {
        tag: "Coverage",
        question: "Which cities and cinema chains are supported?",
        answer:
            "Hyderabad, Mumbai, Bengaluru, Delhi-NCR, Chennai, Kolkata, Pune, Kochi and regional centres across India. The chains include PVR INOX, Cinepolis, Miraj Cinemas, Asian Cinemas and prominent single-screen theatres.",
    },
    {
        tag: "Reliability",
        question: "What happens if an alert fails to deliver?",
        answer:
            "Delivery is durable. If a WhatsApp or email provider has a temporary network glitch, the watch keeps its status and retries up to five times with exponential backoff, so the alert is not lost.",
    },
    {
        tag: "Cost",
        question: "Is TicketFox free to use?",
        answer:
            "Yes. TicketFox is free for individual moviegoers. It was built by Y Sai Sandeep as a utility for cinema lovers.",
    },
];

export default function HowItWorksPage() {
    const [cities, setCities] = useState<City[]>(FALLBACK_CITIES);
    const [openIndex, setOpenIndex] = useState<number | null>(0);

    useEffect(() => {
        loadCities().then(setCities);
    }, []);

    const toggle = (idx: number) => {
        setOpenIndex(openIndex === idx ? null : idx);
    };

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

                <header className="page-head">
                    <h1>How it works.</h1>
                    <p className="lead">
                        Why premiere tickets vanish, the four stages of a watch, the sources and formats it
                        covers, what it will not do, and the answers people ask for most.
                    </p>
                </header>

                <section className="band band-rule" aria-labelledby="problem-title">
                    <div className="band-head">
                        <h2 id="problem-title">The rush for premiere tickets</h2>
                        <p className="band-lead">
                            In India, blockbusters open bookings without notice, at midnight or midday. By the
                            time it reaches social media, the premium formats are gone.
                        </p>
                    </div>

                    <div className="prose-pair">
                        <div>
                            <h3 className="prose-title">What goes wrong</h3>
                            <p className="prose-line">
                                IMAX, 4DX, the central recliner rows and opening night shows are booked out before
                                most people know the listing exists. Refreshing a page is a lottery you have to sit
                                through.
                            </p>
                        </div>
                        <div>
                            <h3 className="prose-title">What TicketFox does instead</h3>
                            <p className="prose-line">
                                You name the film, the city, the formats and the time window. The engine scans every
                                few seconds and sends WhatsApp and email the moment a matching showtime appears.
                            </p>
                        </div>
                    </div>
                </section>

                <section className="band band-rule" aria-labelledby="lifecycle-title">
                    <div className="band-head">
                        <h2 id="lifecycle-title">How a watch runs</h2>
                        <p className="band-lead">
                            Four stages, all of them on our side. You set it once and close the tab.
                        </p>
                    </div>

                    <ol className="steps">
                        <li className="step">
                            <span className="step-num num" aria-hidden="true">01</span>
                            <h3 className="step-title">You create the watch</h3>
                            <p className="step-line">
                                Pick a film, a city, the formats you will accept and where the alert should land.
                                It takes about twenty seconds.
                            </p>
                        </li>
                        <li className="step">
                            <span className="step-num num" aria-hidden="true">02</span>
                            <h3 className="step-title">We scan the sources</h3>
                            <p className="step-line">
                                BookMyShow and District are polled every few seconds, through Cloudflare, for
                                every theatre in your city running that film.
                            </p>
                        </li>
                        <li className="step">
                            <span className="step-num num" aria-hidden="true">03</span>
                            <h3 className="step-title">A showtime appears</h3>
                            <p className="step-line">
                                The moment a listing opens in a format you asked for, the watch catches it. No
                                refresh, no queue, no luck.
                            </p>
                        </li>
                        <li className="step">
                            <span className="step-num num" aria-hidden="true">04</span>
                            <h3 className="step-title">The alert leaves</h3>
                            <p className="step-line">
                                WhatsApp and email, within seconds. If delivery fails, it retries five times
                                before it gives up.
                            </p>
                        </li>
                    </ol>
                </section>

                <section className="band band-rule" aria-labelledby="spec-title">
                    <div className="band-head">
                        <h2 id="spec-title">What it watches</h2>
                        <p className="band-lead">
                            The sources, the formats, the chains and the cities the engine actually covers.
                        </p>
                    </div>

                    <table className="spec">
                        <caption className="visually-hidden">
                            Sources, formats, theatre chains, cities and alert channels TicketFox covers
                        </caption>
                        <tbody>
                            <tr>
                                <th scope="row">Sources</th>
                                <td>BookMyShow, District</td>
                            </tr>
                            <tr>
                                <th scope="row">Formats</th>
                                <td>IMAX, 4DX, 3D, 2D, and every other format the theatre runs</td>
                            </tr>
                            <tr>
                                <th scope="row">Chains</th>
                                <td>PVR, INOX, Cinepolis, Miraj, Asian</td>
                            </tr>
                            <tr>
                                <th scope="row">Cities</th>
                                <td>{cities.map((c) => c.name).join(", ")}</td>
                            </tr>
                            <tr>
                                <th scope="row">Channels</th>
                                <td>WhatsApp, email</td>
                            </tr>
                            <tr>
                                <th scope="row">Poll interval</th>
                                <td className="num">Every few seconds</td>
                            </tr>
                            <tr>
                                <th scope="row">On failure</th>
                                <td>Retries five times, then reports the miss</td>
                            </tr>
                        </tbody>
                    </table>
                </section>

                <section className="band band-rule" aria-labelledby="compare-title">
                    <div className="band-head">
                        <h2 id="compare-title">By hand, or by watch</h2>
                        <p className="band-lead">
                            The same job, done two ways. No scores, just what each one costs you.
                        </p>
                    </div>

                    <table className="compare">
                        <caption className="visually-hidden">
                            Refreshing the booking page by hand compared with a TicketFox watch
                        </caption>
                        <thead>
                            <tr>
                                <th scope="col">The job</th>
                                <th scope="col">By hand</th>
                                <th scope="col">With a watch</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <th scope="row">Finding the drop</th>
                                <td>Refresh the page and hope you are looking at the right minute</td>
                                <td>A poll every few seconds, running whether or not you are awake</td>
                            </tr>
                            <tr>
                                <th scope="row">Missing it</th>
                                <td>The seats open and close while you are in a meeting</td>
                                <td>The alert leaves the second the listing appears</td>
                            </tr>
                            <tr>
                                <th scope="row">Formats</th>
                                <td>Check each theatre, each format, one at a time</td>
                                <td>Every theatre in the city, every format you named</td>
                            </tr>
                            <tr>
                                <th scope="row">Repeat visits</th>
                                <td>Days of checking, for a film that may never list</td>
                                <td>Set once, then close the tab</td>
                            </tr>
                            <tr>
                                <th scope="row">Delivery</th>
                                <td>Whatever you happen to be looking at</td>
                                <td>WhatsApp and email, retried five times</td>
                            </tr>
                        </tbody>
                    </table>
                </section>

                <section className="band band-rule" aria-labelledby="guarantees-title">
                    <div className="band-head">
                        <h2 id="guarantees-title">What it will not do</h2>
                        <p className="band-lead">
                            Three limits, stated plainly, because they are the reason the service is safe to use.
                        </p>
                    </div>

                    <table className="spec">
                        <caption className="visually-hidden">
                            The limits TicketFox keeps: privacy, coverage and delivery
                        </caption>
                        <tbody>
                            <tr>
                                <th scope="row">Privacy</th>
                                <td>
                                    It never asks for your passwords, your BookMyShow credentials or your banking
                                    details. Booking happens in the cinema&rsquo;s own app, with your own account.
                                </td>
                            </tr>
                            <tr>
                                <th scope="row">Coverage</th>
                                <td>
                                    PVR INOX, Cinepolis, Miraj, Asian Cinemas and major single-screen theatres across
                                    Hyderabad, Bengaluru, Mumbai, Delhi-NCR, Chennai, Pune, Kochi and Kolkata.
                                </td>
                            </tr>
                            <tr>
                                <th scope="row">Delivery</th>
                                <td>
                                    If a provider lags, it retries up to five times rather than silently dropping the
                                    alert. A miss is reported on the watch, not hidden.
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </section>

                <section className="band band-rule" aria-labelledby="questions-title">
                    <div className="band-head">
                        <h2 id="questions-title">The four things people ask</h2>
                        <p className="band-lead">The short answers, before the long ones.</p>
                    </div>

                    <div className="questions">
                        <div className="question">
                            <h3 className="question-title">Does it book the ticket for me?</h3>
                            <p className="question-line">
                                No. It watches and it tells you. The booking stays in your hands, on the
                                theatre&rsquo;s own page, with your own account.
                            </p>
                        </div>
                        <div className="question">
                            <h3 className="question-title">How often does it check?</h3>
                            <p className="question-line">
                                Every few seconds, per watch. That is the whole point: a refresh you would have
                                to sit through, done continuously on our side.
                            </p>
                        </div>
                        <div className="question">
                            <h3 className="question-title">What if the site blocks it?</h3>
                            <p className="question-line">
                                The engine goes through Cloudflare and retries five times before it reports a
                                miss. You will see the failure on the watch, not silence.
                            </p>
                        </div>
                        <div className="question">
                            <h3 className="question-title">Which cities work?</h3>
                            <p className="question-line">
                                {cities.map((c) => c.name).join(", ")}. Pick another city in the bar at the top and
                                the catalog and the watch follow it.
                            </p>
                        </div>
                    </div>
                </section>

                <section className="band band-rule" aria-labelledby="faq-title">
                    <div className="band-head">
                        <h2 id="faq-title">Questions</h2>
                        <p className="band-lead">Seven answers, in the order people usually ask them.</p>
                    </div>

                    <div className="faq-list">
                        {FAQS.map((faq, idx) => {
                            const isOpen = openIndex === idx;
                            return (
                                <div key={faq.question} className={`faq-item${isOpen ? " is-open" : ""}`}>
                                    <button
                                        onClick={() => toggle(idx)}
                                        className="faq-trigger"
                                        aria-expanded={isOpen}
                                    >
                                        <span className="faq-question">
                                            <span className="faq-tag">{faq.tag}</span>
                                            <span className="faq-title">{faq.question}</span>
                                        </span>
                                        <ChevronDown className="faq-chevron" aria-hidden="true" />
                                    </button>

                                    {isOpen && <p className="faq-answer">{faq.answer}</p>}
                                </div>
                            );
                        })}
                    </div>
                </section>

                <section className="band band-rule" aria-labelledby="creator-title">
                    <div className="band-head">
                        <h2 id="creator-title">Who builds it</h2>
                        <p className="band-lead">
                            TicketFox is designed and engineered by Y Sai Sandeep. Still have a question? Reach
                            him directly.
                        </p>
                    </div>

                    <div className="contact-row">
                        <a href="mailto:support@ticketfox.site" className="contact-link" title="Email TicketFox support">
                            <Mail className="w-4 h-4" aria-hidden="true" />
                            <span>support@ticketfox.site</span>
                        </a>
                        <a
                            href="https://github.com/saisandeep730"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="contact-link"
                            title="GitHub: saisandeep730"
                        >
                            <Github className="w-4 h-4" aria-hidden="true" />
                            <span>saisandeep730</span>
                        </a>
                        <a
                            href="https://t.me/saisandeepy456"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="contact-link"
                            title="Telegram: @saisandeepy456"
                        >
                            <Send className="w-4 h-4" aria-hidden="true" />
                            <span>@saisandeepy456</span>
                        </a>
                    </div>
                </section>

                <section className="close">
                    <div className="close-inner">
                        <div>
                            <h2>Set the watch. Close the tab.</h2>
                            <p className="close-line">
                                Pick a film and a city, and the next time a showtime opens you will hear about it
                                before the queue does.
                            </p>
                        </div>
                        <Link href="/" className="btn-primary close-action">
                            Create ticket watch
                        </Link>
                    </div>
                </section>
            </div>
        </div>
    );
}
