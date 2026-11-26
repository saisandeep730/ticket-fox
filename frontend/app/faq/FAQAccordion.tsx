"use client";

import React, { useState } from "react";
import { ChevronDown } from "lucide-react";

export interface FAQItem {
    tag: string;
    question: string;
    answer: string;
}

export interface FAQGroup {
    id: string;
    label: string;
    /** One line describing what this group of answers covers. */
    note: string;
    items: FAQItem[];
}

/**
 * The Ledger — a grouped accordion.
 *
 * Each group renders as a ledger section with its own heading and a
 * hairline rule, so a long FAQ reads as an index rather than a wall.
 * Only one answer is open at a time across the whole ledger.
 */
export default function FAQAccordion({ groups }: { groups: FAQGroup[] }) {
    const [openId, setOpenId] = useState<string | null>(
        groups[0]?.items[0] ? `${groups[0].id}-0` : null
    );

    const toggle = (id: string) => {
        setOpenId((current) => (current === id ? null : id));
    };

    return (
        <div className="ledger">
            {groups.map((group) => (
                <section className="ledger-group" key={group.id} aria-labelledby={`ledger-${group.id}`}>
                    <header className="ledger-head">
                        <h2 className="ledger-title" id={`ledger-${group.id}`}>
                            {group.label}
                        </h2>
                        <p className="ledger-note">{group.note}</p>
                    </header>
                    <div className="faq-list">
                        {group.items.map((faq, idx) => {
                            const id = `${group.id}-${idx}`;
                            const isOpen = openId === id;
                            return (
                                <div key={faq.question} className={`faq-item${isOpen ? " is-open" : ""}`}>
                                    <button
                                        type="button"
                                        onClick={() => toggle(id)}
                                        className="faq-trigger"
                                        aria-expanded={isOpen}
                                        aria-controls={`answer-${id}`}
                                    >
                                        <span className="faq-question">
                                            <span className="faq-tag">{faq.tag}</span>
                                            <span className="faq-title">{faq.question}</span>
                                        </span>
                                        <ChevronDown className="faq-chevron" aria-hidden="true" />
                                    </button>
                                    {isOpen && (
                                        <p className="faq-answer" id={`answer-${id}`}>
                                            {faq.answer}
                                        </p>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                </section>
            ))}
        </div>
    );
}
