"use client";

import { useEffect, useRef } from "react";

/**
 * A single, site-wide interactive starfield.
 *
 * Mounted once in the root layout so every route shares one canvas and one
 * animation loop — no per-page duplication. The canvas is fixed, full-viewport,
 * `pointer-events: none` and sits at z-index 0 behind the app shell.
 *
 * Palette: the field is drawn only in TicketFox brand colours — ink white for
 * the star cores, accent violet (`--color-accent-2`) for the cool halos and
 * constellation lines, and accent orange (`--color-accent`) for the warm
 * minority. Nothing here introduces a colour the rest of the site does not use.
 *
 * Rendering: every star is a pre-rendered radial-gradient sprite drawn with
 * `drawImage`, which is far cheaper than an arc + fill per particle. That is
 * what lets the field carry 420–1000 stars on desktop and 140–320 on phones
 * without dropping frames.
 *
 * Motion: three depth layers (far → near) drift at different speeds and twinkle
 * on their own phase. The only pointer response is a local, eased repulsion —
 * stars near the cursor drift away from it and settle back. There is no global
 * parallax, so moving the mouse never shifts the whole field.
 *
 * Resilience: the canvas element also carries a CSS nebula gradient, so even if
 * 2D canvas is unavailable (or the tab is in a reduced-motion state) the page
 * still has a visible starry backdrop instead of a flat black panel.
 *
 * Cost control:
 *  - device pixel ratio is capped at 2, so a 3x phone does not render 9x pixels
 *  - star count scales with viewport area
 *  - constellation lines use a bounded neighbour scan and a per-frame cap
 *  - the loop stops when the tab is hidden
 *  - `prefers-reduced-motion` draws one static frame and never starts the loop
 */

type Star = {
    x: number;
    y: number;
    ox: number;
    oy: number;
    r: number;
    baseAlpha: number;
    phase: number;
    speed: number;
    driftX: number;
    driftY: number;
    depth: number;
    warm: boolean;
};

const MAX_DPR = 2;
const POINTER_RADIUS = 170;
const LINK_DISTANCE = 120;
const MAX_LINKS_PER_FRAME = 320;
const NEIGHBOUR_SCAN = 14;
const MOBILE_QUERY = "(max-width: 48rem)";
const REDUCED_QUERY = "(prefers-reduced-motion: reduce)";
const SPRITE_SIZE = 32;

// Brand colours, sampled from tokens.css so the field never drifts off-palette.
const INK = "242, 246, 252"; // --color-ink
const VIOLET = "160, 107, 255"; // --color-accent-2
const ORANGE = "255, 138, 61"; // --color-accent

function starCount(width: number, height: number, isMobile: boolean): number {
    const area = width * height;
    if (isMobile) {
        return Math.max(140, Math.min(320, Math.round(area / 1800)));
    }
    return Math.max(420, Math.min(1000, Math.round(area / 1800)));
}

function makeStars(width: number, height: number, count: number): Star[] {
    const stars: Star[] = [];
    for (let i = 0; i < count; i += 1) {
        const depth = Math.random();
        const angle = Math.random() * Math.PI * 2;
        const drift = 0.08 + depth * 0.35;
        stars.push({
            x: Math.random() * width,
            y: Math.random() * height,
            ox: 0,
            oy: 0,
            r: 0.4 + depth * 1.5 + Math.random() * 0.35,
            baseAlpha: 0.3 + depth * 0.42 + Math.random() * 0.18,
            phase: Math.random() * Math.PI * 2,
            speed: 0.0008 + Math.random() * 0.0022,
            driftX: Math.cos(angle) * drift,
            driftY: Math.sin(angle) * drift,
            depth,
            warm: Math.random() < 0.22,
        });
    }
    return stars;
}

function makeSprite(warm: boolean): HTMLCanvasElement {
    const sprite = document.createElement("canvas");
    sprite.width = SPRITE_SIZE;
    sprite.height = SPRITE_SIZE;
    const g = sprite.getContext("2d");
    if (!g) return sprite;

    const c = SPRITE_SIZE / 2;
    const grad = g.createRadialGradient(c, c, 0, c, c, c);
    if (warm) {
        grad.addColorStop(0, `rgba(${INK},1)`);
        grad.addColorStop(0.2, `rgba(255,214,170,0.92)`);
        grad.addColorStop(0.45, `rgba(${ORANGE},0.34)`);
        grad.addColorStop(1, `rgba(${ORANGE},0)`);
    } else {
        grad.addColorStop(0, `rgba(${INK},1)`);
        grad.addColorStop(0.2, `rgba(226,236,255,0.9)`);
        grad.addColorStop(0.45, `rgba(${VIOLET},0.30)`);
        grad.addColorStop(1, `rgba(${VIOLET},0)`);
    }
    g.fillStyle = grad;
    g.fillRect(0, 0, SPRITE_SIZE, SPRITE_SIZE);
    return sprite;
}

export default function Starfield() {
    const canvasRef = useRef<HTMLCanvasElement | null>(null);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext("2d", { alpha: true });
        if (!ctx) return;

        const reducedMotion = window.matchMedia(REDUCED_QUERY);
        const mobile = window.matchMedia(MOBILE_QUERY);

        const coolSprite = makeSprite(false);
        const warmSprite = makeSprite(true);

        let width = 0;
        let height = 0;
        let stars: Star[] = [];
        let frame = 0;
        let running = false;
        let lastTime = 0;
        let resizeTimer: ReturnType<typeof setTimeout> | null = null;

        const pointer = { x: -9999, y: -9999, active: false };

        function resize() {
            const dpr = Math.min(window.devicePixelRatio || 1, MAX_DPR);
            width = window.innerWidth;
            height = window.innerHeight;

            // A zero-sized viewport (hidden tab, prerender) would produce an
            // empty field; retry on the next frame instead of giving up.
            if (width < 2 || height < 2) {
                window.requestAnimationFrame(resize);
                return;
            }

            canvas!.width = Math.floor(width * dpr);
            canvas!.height = Math.floor(height * dpr);
            canvas!.style.width = `${width}px`;
            canvas!.style.height = `${height}px`;

            ctx!.setTransform(dpr, 0, 0, dpr, 0, 0);
            stars = makeStars(width, height, starCount(width, height, mobile.matches));
            canvas!.dataset.stars = String(stars.length);
        }

        function drawStar(star: Star, alpha: number) {
            const x = star.x + star.ox;
            const y = star.y + star.oy;
            const size = star.r * 7;

            ctx!.globalAlpha = alpha;
            ctx!.drawImage(
                star.warm ? warmSprite : coolSprite,
                x - size / 2,
                y - size / 2,
                size,
                size,
            );
        }

        function drawLinks() {
            let links = 0;
            ctx!.strokeStyle = `rgba(${VIOLET},1)`;
            ctx!.lineWidth = 0.6;

            for (let i = 0; i < stars.length && links < MAX_LINKS_PER_FRAME; i += 1) {
                const a = stars[i];
                const ax = a.x + a.ox;
                const ay = a.y + a.oy;
                const limit = Math.min(stars.length, i + 1 + NEIGHBOUR_SCAN);

                for (let j = i + 1; j < limit && links < MAX_LINKS_PER_FRAME; j += 1) {
                    const b = stars[j];
                    const dx = ax - (b.x + b.ox);
                    const dy = ay - (b.y + b.oy);
                    const dist = Math.sqrt(dx * dx + dy * dy);
                    if (dist > LINK_DISTANCE) continue;

                    ctx!.globalAlpha = 0.16 * (1 - dist / LINK_DISTANCE);
                    ctx!.beginPath();
                    ctx!.moveTo(ax, ay);
                    ctx!.lineTo(b.x + b.ox, b.y + b.oy);
                    ctx!.stroke();
                    links += 1;
                }
            }
        }

        function paintStatic() {
            ctx!.clearRect(0, 0, width, height);
            for (const star of stars) {
                drawStar(star, star.baseAlpha);
            }
            drawLinks();
            ctx!.globalAlpha = 1;
        }

        function step(time: number) {
            if (!running) return;
            const dt = lastTime ? Math.min(time - lastTime, 48) : 16;
            lastTime = time;
            const scale = dt / 16;

            ctx!.clearRect(0, 0, width, height);

            for (const star of stars) {
                // twinkle
                star.phase += star.speed * dt;
                const alpha = star.baseAlpha * (0.5 + 0.5 * Math.sin(star.phase));

                // depth-scaled drift, wrapped so stars never pop at the edges
                star.x += star.driftX * scale;
                star.y += star.driftY * scale;
                if (star.x < -6) star.x = width + 6;
                if (star.x > width + 6) star.x = -6;
                if (star.y < -6) star.y = height + 6;
                if (star.y > height + 6) star.y = -6;

                // eased cursor repulsion: the offset chases a target instead of jumping
                let targetX = 0;
                let targetY = 0;
                if (pointer.active) {
                    const dx = star.x - pointer.x;
                    const dy = star.y - pointer.y;
                    const dist = Math.sqrt(dx * dx + dy * dy);
                    if (dist < POINTER_RADIUS && dist > 0.001) {
                        const force = (1 - dist / POINTER_RADIUS) ** 2;
                        const push = force * (14 + star.depth * 26);
                        targetX = (dx / dist) * push;
                        targetY = (dy / dist) * push;
                    }
                }
                star.ox += (targetX - star.ox) * 0.1;
                star.oy += (targetY - star.oy) * 0.1;

                drawStar(star, alpha);
            }

            drawLinks();
            ctx!.globalAlpha = 1;

            frame = window.requestAnimationFrame(step);
        }

        function start() {
            if (running || reducedMotion.matches) return;
            running = true;
            lastTime = 0;
            frame = window.requestAnimationFrame(step);
        }

        function stop() {
            running = false;
            if (frame) {
                window.cancelAnimationFrame(frame);
                frame = 0;
            }
        }

        function handlePointerMove(event: PointerEvent) {
            pointer.x = event.clientX;
            pointer.y = event.clientY;
            pointer.active = true;
        }

        function handlePointerOut(event: PointerEvent) {
            if (!event.relatedTarget) pointer.active = false;
        }

        function handleResize() {
            if (resizeTimer) clearTimeout(resizeTimer);
            resizeTimer = setTimeout(() => {
                resize();
                if (reducedMotion.matches) {
                    paintStatic();
                }
            }, 120);
        }

        function handleVisibility() {
            if (document.hidden) {
                stop();
            } else {
                start();
            }
        }

        function handleMotionChange() {
            if (reducedMotion.matches) {
                stop();
                paintStatic();
            } else {
                start();
            }
        }

        resize();

        if (reducedMotion.matches) {
            paintStatic();
        } else {
            start();
        }

        // Expose a tiny debug handle so the state can be inspected from the
        // console without guessing why a field looks empty.
        (window as unknown as Record<string, unknown>).__ticketfoxStarfield = {
            get stars() {
                return stars.length;
            },
            get running() {
                return running;
            },
            get reducedMotion() {
                return reducedMotion.matches;
            },
            get mobile() {
                return mobile.matches;
            },
            get size() {
                return [width, height];
            },
        };

        const observer =
            typeof ResizeObserver !== "undefined"
                ? new ResizeObserver(() => handleResize())
                : null;
        observer?.observe(document.documentElement);

        window.addEventListener("resize", handleResize);
        window.addEventListener("pointermove", handlePointerMove, { passive: true });
        window.addEventListener("pointerout", handlePointerOut);
        window.addEventListener("blur", handlePointerOut as unknown as EventListener);
        document.addEventListener("visibilitychange", handleVisibility);
        reducedMotion.addEventListener("change", handleMotionChange);

        return () => {
            stop();
            if (resizeTimer) clearTimeout(resizeTimer);
            observer?.disconnect();
            window.removeEventListener("resize", handleResize);
            window.removeEventListener("pointermove", handlePointerMove);
            window.removeEventListener("pointerout", handlePointerOut);
            window.removeEventListener("blur", handlePointerOut as unknown as EventListener);
            document.removeEventListener("visibilitychange", handleVisibility);
            reducedMotion.removeEventListener("change", handleMotionChange);
            delete (window as unknown as Record<string, unknown>).__ticketfoxStarfield;
        };
    }, []);

    return <canvas ref={canvasRef} className="starfield-canvas" aria-hidden="true" />;
}
