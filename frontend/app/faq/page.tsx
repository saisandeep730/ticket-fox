import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeft, ArrowRight, Github, Mail, Send } from "lucide-react";
import FAQAccordion, { type FAQGroup } from "./FAQAccordion";

const SITE_URL = (process.env.NEXT_PUBLIC_SITE_URL || "https://ticketfox.site").replace(/\/$/, "");

export const metadata: Metadata = {
  title: "FAQ — How TicketFox watches, alerts and never books",
  description:
    "Answers on alert speed, channels, filters, coverage, reliability, privacy and cost. What TicketFox does, what it refuses to do, and how to get the most out of a watch.",
  alternates: { canonical: "/faq" },
  openGraph: {
    title: "FAQ — How TicketFox watches, alerts and never books",
    description:
      "Alert speed, channels, filters, coverage, reliability, privacy and cost — answered in one ledger.",
    url: `${SITE_URL}/faq`,
    siteName: "TicketFox",
    type: "website",
  },
};

const GROUPS: FAQGroup[] = [
  {
    id: "alerts",
    label: "Alerts and speed",
    note: "How fast the engine notices a drop, and what lands in your inbox.",
    items: [
      {
        tag: "Alerts and speed",
        question: "How fast is an alert after a showtime appears?",
        answer:
          "The engine polls BookMyShow and District continuously. When a matching showtime appears, the alert is queued immediately and delivered over your chosen channel. In practice the gap between a listing going live and your phone buzzing is measured in seconds to a couple of minutes, depending on the source's own publish delay.",
      },
      {
        tag: "Alerts and speed",
        question: "What exactly does an alert contain?",
        answer:
          "The film, the cinema, the format, the exact showtime, a timestamp, and a direct link to the listing that triggered it. The link matters: it takes you to the platform that actually has the seat, so there is no second search.",
      },
      {
        tag: "Alerts and speed",
        question: "Will I get an alert for a show that is already sold out?",
        answer:
          "No. The engine alerts on a listing that exists and has seats available at the moment it is detected. If a show sells out between detection and your tap, the listing itself will show that — but you will not be woken up for a show that was never bookable.",
      },
    ],
  },
  {
    id: "channels",
    label: "Channels",
    note: "Where alerts arrive, and how delivery stays durable.",
    items: [
      {
        tag: "Channels",
        question: "Which channels can I receive alerts on?",
        answer:
          "WhatsApp and email. You can enable either or both on a watch. WhatsApp is the fastest in practice because it is the app most people already have open; email is the durable fallback that keeps a record.",
      },
      {
        tag: "Channels",
        question: "What happens if a delivery fails?",
        answer:
          "Delivery is retried with backoff. If it still fails, the miss is reported on the watch rather than hidden. An alert that fails silently is worse than no alert, because you stop watching — so the engine surfaces the failure instead of pretending it delivered.",
      },
      {
        tag: "Channels",
        question: "Can I pause alerts without deleting a watch?",
        answer:
          "Yes. Every watch can be paused and resumed. Pausing keeps the watch definition intact, so you can switch it back on for a later release without rebuilding the filters.",
      },
    ],
  },
  {
    id: "filters",
    label: "Filters and watches",
    note: "How a watch decides what counts as a match.",
    items: [
      {
        tag: "Filters",
        question: "What can a watch filter on?",
        answer:
          "Film, city, cinema or chain, format (IMAX, 4DX, P[XL], ICE, ScreenX and others), and a time window for the show. You can be as broad as 'any IMAX in Bengaluru this weekend' or as narrow as one screen on one evening.",
      },
      {
        tag: "Filters",
        question: "How many watches can I run at once?",
        answer:
          "There is no hard limit for individual use. In practice most people run a handful — one per film they are waiting on — and pause the ones that have already paid off.",
      },
      {
        tag: "Filters",
        question: "Do watches expire?",
        answer:
          "A watch stays active until you pause or delete it. If a film's run ends, the watch simply stops matching; it does not silently delete itself, so you keep the history of what it caught.",
      },
    ],
  },
  {
    id: "coverage",
    label: "Coverage",
    note: "Which cities, chains and formats the engine can see.",
    items: [
      {
        tag: "Coverage",
        question: "Which cities and chains are covered?",
        answer:
          "Major Indian cities and the cinema chains that publish through BookMyShow and District — including PVR INOX, Cinepolis, Miraj and the larger regional chains. If a cinema lists on either platform, the engine can watch it.",
      },
      {
        tag: "Coverage",
        question: "Does it cover regional-language releases?",
        answer:
          "Yes. Coverage is driven by what the platforms list, not by language. A Telugu, Tamil, Malayalam, Kannada or Hindi release is watched the same way as an English one.",
      },
      {
        tag: "Coverage",
        question: "What if my cinema is not on either platform?",
        answer:
          "Then the engine cannot see it. TicketFox reads BookMyShow and District only; a cinema that sells exclusively through its own site is outside the watch. That is a deliberate limit rather than an oversight.",
      },
    ],
  },
  {
    id: "reliability",
    label: "Reliability",
    note: "What happens when a source misbehaves.",
    items: [
      {
        tag: "Reliability",
        question: "What happens when a booking site blocks the poll?",
        answer:
          "Both platforms sit behind Cloudflare and both change their markup from time to time. The engine handles challenge pages, rate limits and layout changes, retries failed polls, and reports a miss on the watch rather than silently returning 'no shows'.",
      },
      {
        tag: "Reliability",
        question: "Can the engine guarantee I get a seat?",
        answer:
          "No, and it never claims to. It guarantees you will know the moment a matching show opens. Whether you get the seat still depends on how fast you tap and how many other people are trying at the same second.",
      },
      {
        tag: "Reliability",
        question: "How do I know the engine is actually working?",
        answer:
          "Each watch shows its last poll and its alert history. If a poll fails, the watch says so. You can also run a test alert on a watch to confirm the delivery path end to end before a real drop.",
      },
    ],
  },
  {
    id: "privacy",
    label: "Privacy and cost",
    note: "What is stored, what is never asked for, and what it costs.",
    items: [
      {
        tag: "Privacy",
        question: "Do you need my BookMyShow or District login?",
        answer:
          "No. TicketFox never asks for booking credentials and never stores them. The engine reads public listings; it does not act as you on a booking site.",
      },
      {
        tag: "Privacy",
        question: "What data is stored?",
        answer:
          "Your watch definitions (film, city, filters), your chosen delivery channels, and the alert history for those watches. No card details, no booking passwords, no payment information of any kind.",
      },
      {
        tag: "Privacy",
        question: "Is TicketFox free?",
        answer:
          "Yes, for individual moviegoers. The point was never to sell tickets — it was to stop people missing them. There is no paid tier gating alert speed.",
      },
    ],
  },
];

export default function FAQPage() {
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
          <h1>Frequently asked questions.</h1>
          <p className="lead">
            Everything about how the engine watches, what an alert contains, and the
            line it will not cross. Grouped so you can jump to the part you need.
          </p>
        </header>

        {/* The index */}
        <nav className="ledger-index" aria-label="FAQ sections">
          {GROUPS.map((group) => (
            <a className="ledger-index-link" href={`#ledger-${group.id}`} key={group.id}>
              <span className="ledger-index-label">{group.label}</span>
              <span className="ledger-index-count">{group.items.length}</span>
            </a>
          ))}
        </nav>

        <section className="band band-rule" aria-labelledby="faq-title">
          <div className="band-head">
            <h2 id="faq-title">The ledger.</h2>
            <p className="band-lead">
              Six sections, one answer open at a time. Tap a question to read it.
            </p>
          </div>
          <FAQAccordion groups={GROUPS} />
        </section>

        <section className="band band-rule" aria-labelledby="more-title">
          <div className="band-head">
            <h2 id="more-title">Still reading.</h2>
          </div>
          <div className="contact-row">
            <Link href="/how-it-works" className="contact-link">
              How it works
              <ArrowRight className="w-4 h-4" aria-hidden="true" />
            </Link>
            <Link href="/blog" className="contact-link">
              Blog
              <ArrowRight className="w-4 h-4" aria-hidden="true" />
            </Link>
            <Link href="/about" className="contact-link">
              About
              <ArrowRight className="w-4 h-4" aria-hidden="true" />
            </Link>
          </div>
        </section>

        <section className="band band-rule" aria-labelledby="contact-title">
          <div className="band-head">
            <h2 id="contact-title">Ask the booth.</h2>
            <p className="band-lead">
              If the ledger does not answer it, reach out directly.
            </p>
          </div>
          <div className="contact-row">
            <a href="mailto:support@ticketfox.site" className="contact-link">
              <Mail className="w-4 h-4" aria-hidden="true" />
              support@ticketfox.site
            </a>
            <a
              href="https://github.com/saisandeep730"
              target="_blank"
              rel="noopener noreferrer"
              className="contact-link"
            >
              <Github className="w-4 h-4" aria-hidden="true" />
              github.com/saisandeep730
            </a>
            <a
              href="https://t.me/saisandeepy456"
              target="_blank"
              rel="noopener noreferrer"
              className="contact-link"
            >
              <Send className="w-4 h-4" aria-hidden="true" />
              t.me/saisandeepy456
            </a>
          </div>
        </section>

        <section className="close">
          <div className="close-inner">
            <div>
              <h2>Set the watch. Close the tab.</h2>
              <p className="close-line">
                Describe the film, city and formats once. The engine does the
                waiting, and messages you the moment a seat opens.
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
