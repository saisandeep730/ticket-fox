import type { Metadata } from "next";
import Link from "next/link";
import {
  ArrowLeft,
  Bell,
  Film,
  Github,
  Mail,
  Radar,
  Send,
  ShieldCheck,
  X,
} from "lucide-react";
import TicketFoxLogo from "@/components/TicketFoxLogo";

const SITE_URL = (process.env.NEXT_PUBLIC_SITE_URL || "https://ticketfox.site").replace(/\/$/, "");

export const metadata: Metadata = {
  title: "About TicketFox — The projection booth behind the alerts",
  description:
    "TicketFox is a real-time ticket drop notifier for BookMyShow and District. Who builds it, how it works, what it refuses to do, and why it never touches your money.",
  alternates: { canonical: "/about" },
  openGraph: {
    title: "About TicketFox — The projection booth behind the alerts",
    description:
      "Who builds TicketFox, how the watch engine works, and the five things it will never do with your account.",
    url: `${SITE_URL}/about`,
    siteName: "TicketFox",
    type: "website",
  },
};

/** The credit roll — who is behind the booth. */
const CREDITS: { role: string; name: string }[] = [
  { role: "Direction", name: "Y Sai Sandeep" },
  { role: "Engineering", name: "Y Sai Sandeep" },
  { role: "Sources", name: "BookMyShow, District" },
  { role: "Delivery", name: "WhatsApp, Email" },
  { role: "Built for", name: "Cinema lovers in India" },
];

/** How the booth got here. */
const TIMELINE: { year: string; title: string; line: string }[] = [
  {
    year: "The first watch",
    title: "One film, one city, one script",
    line: "TicketFox started as a private script polling a single BookMyShow listing for a single film. It existed because refreshing a page by hand is a lottery you have to sit through.",
  },
  {
    year: "The second source",
    title: "District joined the poll",
    line: "The two platforms do not publish at the same moment. Adding District meant an alert fires on whichever source lists first, instead of betting on one pipeline.",
  },
  {
    year: "The second channel",
    title: "WhatsApp and email",
    line: "A single delivery channel is a single point of failure. Alerts now go out over WhatsApp and email, retried with backoff, with a miss reported rather than hidden.",
  },
  {
    year: "The open door",
    title: "Free for moviegoers",
    line: "The engine was opened to anyone who wants it. It stays free for individual moviegoers, because the point was never to sell tickets — it was to stop people missing them.",
  },
];

/** The principles the engine is built on. */
const PRINCIPLES: { icon: typeof Radar; title: string; line: string }[] = [
  {
    icon: Radar,
    title: "Watch, do not guess",
    line: "The engine polls the source continuously. It does not infer a drop from a rumour, a poster or a social post — only from a listing that actually exists.",
  },
  {
    icon: Bell,
    title: "Tell you the second it opens",
    line: "A watch is a standing instruction. The moment a matching showtime appears, the alert fires with the film, cinema, format, showtime and a direct link.",
  },
  {
    icon: ShieldCheck,
    title: "Never touch your money",
    line: "No booking logins, no card details, no automated checkout. TicketFox watches and tells you; the booking stays in your hands on the cinema's own page.",
  },
];

/** The refusals — the line the product will not cross. */
const REFUSALS: string[] = [
  "We will not book on your behalf.",
  "We will not ask for your BookMyShow or District password.",
  "We will not store your card or payment details.",
  "We will not sell or share your watch list.",
  "We will not send marketing you did not ask for.",
];

/** Operational facts, kept separate from the credit roll. */
const FACTS: { label: string; value: string }[] = [
  { label: "Coverage", value: "Major Indian cities and cinema chains" },
  { label: "Cost", value: "Free for individual moviegoers" },
  { label: "Booking", value: "Never automated — you stay in control" },
  { label: "Credentials", value: "Never requested; no booking logins stored" },
  { label: "Data", value: "Watch definitions and alert history only" },
];

export default function AboutPage() {
  return (
    <div className="page">
      <div className="container">
        <div className="page-bar">
          <Link href="/" className="page-back">
            <ArrowLeft className="w-4 h-4" aria-hidden="true" />
            Back to the catalog
          </Link>
          <TicketFoxLogo size="sm" />
        </div>

        <header className="page-head">
          <h1>About TicketFox.</h1>
          <p className="lead">
            A real-time ticket drop notifier for BookMyShow and District. It watches the
            listings you care about and messages you the moment a matching showtime
            appears — so the only thing left to do is pick a seat.
          </p>
        </header>

        {/* The credit roll */}
        <section className="band band-rule" aria-labelledby="credits-title">
          <div className="band-head">
            <h2 id="credits-title">The booth credits.</h2>
            <p className="band-lead">
              TicketFox is a small, deliberately narrow product. Here is who is behind
              it and what it is built on.
            </p>
          </div>
          <dl className="credits">
            {CREDITS.map((credit) => (
              <div className="credit-row" key={credit.role}>
                <dt className="credit-role">{credit.role}</dt>
                <dd className="credit-name">{credit.name}</dd>
              </div>
            ))}
          </dl>
        </section>

        {/* The story */}
        <section className="band band-rule" aria-labelledby="story-title">
          <div className="band-head">
            <h2 id="story-title">Why it exists.</h2>
          </div>
          <div className="prose-pair">
            <div>
              <h3 className="prose-title">The problem</h3>
              <p className="prose-line">
                A premium show can open and sell out inside fifteen minutes, and the
                listing appears whenever the theatre publishes it — often late at
                night, sometimes mid-morning. There is no reliable &ldquo;booking opens
                at 9 AM&rdquo; rule, so checking by hand is a lottery you have to sit
                through.
              </p>
            </div>
            <div>
              <h3 className="prose-title">The answer</h3>
              <p className="prose-line">
                Describe the film, city, formats and time window once. The engine
                polls BookMyShow and District continuously and messages you the
                moment a matching show opens, with a direct link to the listing that
                triggered it.
              </p>
            </div>
          </div>
        </section>

        {/* The timeline */}
        <section className="band band-rule" aria-labelledby="timeline-title">
          <div className="band-head">
            <h2 id="timeline-title">How the booth was built.</h2>
            <p className="band-lead">
              Four decisions, in the order they were made. Each one removed a way to
              miss a drop.
            </p>
          </div>
          <ol className="timeline">
            {TIMELINE.map((item, idx) => (
              <li className="timeline-item" key={item.title}>
                <span className="timeline-mark" aria-hidden="true">
                  {String(idx + 1).padStart(2, "0")}
                </span>
                <div className="timeline-body">
                  <span className="timeline-year">{item.year}</span>
                  <h3 className="timeline-title">{item.title}</h3>
                  <p className="timeline-line">{item.line}</p>
                </div>
              </li>
            ))}
          </ol>
        </section>

        {/* The principles */}
        <section className="band band-rule" aria-labelledby="principles-title">
          <div className="band-head">
            <h2 id="principles-title">What the engine is built on.</h2>
          </div>
          <ol className="steps">
            {PRINCIPLES.map((p, idx) => {
              const Icon = p.icon;
              return (
                <li className="step" key={p.title}>
                  <span className="step-num">{String(idx + 1).padStart(2, "0")}</span>
                  <h3 className="step-title">
                    <Icon className="w-4 h-4" aria-hidden="true" />
                    {p.title}
                  </h3>
                  <p className="step-line">{p.line}</p>
                </li>
              );
            })}
          </ol>
        </section>

        {/* The refusals */}
        <section className="band band-rule" aria-labelledby="refusals-title">
          <div className="band-head">
            <h2 id="refusals-title">What it will never do.</h2>
            <p className="band-lead">
              The line is drawn on purpose. An alert service that crosses it has
              stopped being an alert service.
            </p>
          </div>
          <ul className="refusals">
            {REFUSALS.map((refusal) => (
              <li className="refusal" key={refusal}>
                <X className="refusal-mark" aria-hidden="true" />
                <span className="refusal-line">{refusal}</span>
              </li>
            ))}
          </ul>
        </section>

        {/* The facts */}
        <section className="band band-rule" aria-labelledby="facts-title">
          <div className="band-head">
            <h2 id="facts-title">The spec sheet.</h2>
          </div>
          <table className="spec">
            <caption className="sr-only">TicketFox operational facts</caption>
            <tbody>
              {FACTS.map((f) => (
                <tr key={f.label}>
                  <th scope="row">{f.label}</th>
                  <td>{f.value}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        {/* The creator */}
        <section className="band band-rule" aria-labelledby="creator-title">
          <div className="band-head">
            <h2 id="creator-title">Talk to the booth.</h2>
            <p className="band-lead">
              Questions, bugs, or a drop the engine missed — reach out directly.
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

        {/* The rest of the site */}
        <section className="band band-rule" aria-labelledby="more-title">
          <div className="band-head">
            <h2 id="more-title">Keep reading.</h2>
          </div>
          <div className="contact-row">
            <Link href="/how-it-works" className="contact-link">
              <Film className="w-4 h-4" aria-hidden="true" />
              How it works
            </Link>
            <Link href="/faq" className="contact-link">
              <Radar className="w-4 h-4" aria-hidden="true" />
              FAQ
            </Link>
            <Link href="/blog" className="contact-link">
              <Bell className="w-4 h-4" aria-hidden="true" />
              Blog
            </Link>
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
