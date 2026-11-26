"use client";

import Link from "next/link";
import { Github, Mail, Send } from "lucide-react";
import TicketFoxLogo from "./TicketFoxLogo";

const PRODUCT_LINKS = [
  { href: "/", label: "Now showing" },
  { href: "/how-it-works", label: "How it works" },
  { href: "/faq", label: "FAQ" },
];

const COMPANY_LINKS = [
  { href: "/about", label: "About" },
  { href: "/blog", label: "The Screening Room" },
];

const CONTACT_LINKS = [
  {
    href: "mailto:support@ticketfox.site",
    label: "support@ticketfox.site",
    icon: Mail,
    external: false,
  },
  {
    href: "https://github.com/saisandeep730",
    label: "github.com/saisandeep730",
    icon: Github,
    external: true,
  },
  {
    href: "https://t.me/saisandeepy456",
    label: "t.me/saisandeepy456",
    icon: Send,
    external: true,
  },
];

export default function Footer() {
  const year = new Date().getFullYear();

  return (
    <footer className="mast">
      <div className="container mast-inner">
        <div className="mast-brand">
          <TicketFoxLogo size="md" />
          <p className="mast-line">
            Real-time ticket drop alerts for BookMyShow and District. We watch the
            listings, you pick the seat.
          </p>
          <p className="mast-line mast-line-tight">
            Built by <strong>Y Sai Sandeep</strong>.
          </p>
        </div>

        <nav className="mast-column" aria-label="Product">
          <h2 className="mast-head">Product</h2>
          <ul className="mast-list">
            {PRODUCT_LINKS.map((link) => (
              <li key={link.href}>
                <Link href={link.href}>{link.label}</Link>
              </li>
            ))}
          </ul>
        </nav>

        <nav className="mast-column" aria-label="Company">
          <h2 className="mast-head">Company</h2>
          <ul className="mast-list">
            {COMPANY_LINKS.map((link) => (
              <li key={link.href}>
                <Link href={link.href}>{link.label}</Link>
              </li>
            ))}
          </ul>
        </nav>

        <nav className="mast-column" aria-label="Contact">
          <h2 className="mast-head">Contact</h2>
          <ul className="mast-list">
            {CONTACT_LINKS.map((link) => {
              const Icon = link.icon;
              return (
                <li key={link.href}>
                  <a
                    href={link.href}
                    {...(link.external
                      ? { target: "_blank", rel: "noopener noreferrer" }
                      : {})}
                  >
                    <Icon className="mast-icon" aria-hidden="true" />
                    {link.label}
                  </a>
                </li>
              );
            })}
          </ul>
        </nav>
      </div>

      <div className="container mast-foot">
        <span>© {year} TicketFox. Built for cinema lovers.</span>
        <span className="mast-foot-note">
          Not affiliated with BookMyShow or District. Alerts only — never bookings.
        </span>
      </div>
    </footer>
  );
}
