"use client";

import { useEffect, useState } from "react";

/**
 * A hairline reading-progress bar pinned under the page bar.
 *
 * Tracks how far the article body has been scrolled through, not the whole
 * document, so the bar reaches 100% when the reader finishes the piece rather
 * than when they reach the footer.
 */
export default function ReadingProgress({ targetId }: { targetId: string }) {
    const [progress, setProgress] = useState(0);

    useEffect(() => {
        const target = document.getElementById(targetId);
        if (!target) return;

        let frame = 0;

        const measure = () => {
            frame = 0;
            const rect = target.getBoundingClientRect();
            const viewport = window.innerHeight;
            const total = rect.height - viewport;
            if (total <= 0) {
                setProgress(rect.top <= 0 ? 1 : 0);
                return;
            }
            const scrolled = Math.min(Math.max(-rect.top, 0), total);
            setProgress(scrolled / total);
        };

        const onScroll = () => {
            if (frame) return;
            frame = window.requestAnimationFrame(measure);
        };

        measure();
        window.addEventListener("scroll", onScroll, { passive: true });
        window.addEventListener("resize", onScroll);
        return () => {
            if (frame) window.cancelAnimationFrame(frame);
            window.removeEventListener("scroll", onScroll);
            window.removeEventListener("resize", onScroll);
        };
    }, [targetId]);

    return (
        <div className="read-progress" aria-hidden="true">
            <span
                className="read-progress-fill"
                style={{ transform: `scaleX(${progress.toFixed(4)})` }}
            />
        </div>
    );
}
