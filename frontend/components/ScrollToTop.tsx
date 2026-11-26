"use client";

import { useEffect, useState } from "react";
import { ArrowUp } from "lucide-react";

/**
 * A small fixed "back to top" button that appears once the page has been
 * scrolled past a comfortable threshold. Mounted once in the root layout so
 * every route gets it without duplicating the component.
 */
export default function ScrollToTop() {
    const [visible, setVisible] = useState(false);

    useEffect(() => {
        const threshold = 480;

        const onScroll = () => {
            setVisible(window.scrollY > threshold);
        };

        onScroll();
        window.addEventListener("scroll", onScroll, { passive: true });
        return () => window.removeEventListener("scroll", onScroll);
    }, []);

    const handleClick = () => {
        const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
        window.scrollTo({ top: 0, behavior: reduce ? "auto" : "smooth" });
    };

    return (
        <button
            type="button"
            onClick={handleClick}
            className={`scroll-top${visible ? " is-visible" : ""}`}
            aria-label="Scroll back to top"
            title="Back to top"
            tabIndex={visible ? 0 : -1}
            aria-hidden={!visible}
        >
            <ArrowUp className="w-5 h-5" aria-hidden="true" />
        </button>
    );
}
