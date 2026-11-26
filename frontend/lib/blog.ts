/**
 * Blog content — the single source of truth for /blog and /blog/[slug].
 *
 * Posts are plain data so the index, the post pages, the sitemap and the
 * structured data all read from one place. Add a post here and it appears
 * everywhere, including the sitemap.
 */

export interface BlogSection {
    heading?: string;
    paragraphs?: string[];
    list?: string[];
    quote?: string;
}

export interface BlogPost {
    slug: string;
    title: string;
    /** Used for the meta description and the index card. Keep under ~160 chars. */
    description: string;
    /** ISO date, e.g. "2026-11-10". */
    date: string;
    readingMinutes: number;
    tags: string[];
    sections: BlogSection[];
}

export const BLOG_POSTS: BlogPost[] = [
    {
        slug: "how-to-get-imax-tickets-in-india",
        title: "How to actually get IMAX tickets in India before they sell out",
        description:
            "IMAX and 4DX seats for big releases vanish in minutes. Here is the timing, the formats and the habits that decide whether you get a seat or a waitlist.",
        date: "2026-11-12",
        readingMinutes: 7,
        tags: ["IMAX", "Booking strategy", "PVR INOX"],
        sections: [
            {
                paragraphs: [
                    "Every big Indian release follows the same pattern. The booking announcement lands on social media, the app opens, and within ten to twenty minutes the IMAX and 4DX shows for opening weekend are gone. The people who get seats are rarely the fastest typists — they are the ones who knew when the listing would open.",
                    "This guide is about that timing: how showtimes appear, which formats sell out first, and what you can do ahead of the drop so that the only thing left to do is pick a seat.",
                ],
            },
            {
                heading: "Understand how a showtime appears",
                paragraphs: [
                    "A cinema does not publish a whole week of shows at once. The theatre's programming team finalises a screen and a slot, then the listing is pushed to BookMyShow or District. That push can happen at any hour — often late at night, sometimes mid-morning on a weekday.",
                    "The practical consequence: there is no reliable 'booking opens at 9 AM' rule. The listing appears when the theatre publishes it, and the first people to see it are the ones polling the source rather than refreshing a social feed.",
                ],
            },
            {
                heading: "Which formats sell out first",
                list: [
                    "IMAX — the smallest seat count per screen and the highest demand. Usually gone first.",
                    "4DX — limited screens nationally, so a single city may have one or two. Sells out almost as fast.",
                    "Premium large format (P[XL], ICE, ScreenX) — a middle tier that lasts slightly longer.",
                    "Recliner and central rows in standard shows — the seats people actually want, gone before the show is 'full'.",
                    "Standard 2D — usually available for days, which is why it is the fallback rather than the target.",
                ],
            },
            {
                heading: "The habits that decide the outcome",
                paragraphs: [
                    "Three habits separate people who get opening-night IMAX seats from people who do not.",
                ],
                list: [
                    "Decide your acceptable formats and time slots before the drop, not during it. Deciding while seats disappear is how you end up with a 10:40 PM show in a city you do not live in.",
                    "Watch the source, not the rumour. A listing on BookMyShow is real; a screenshot on X is not.",
                    "Have your payment method ready and your account signed in. The checkout is where most near-misses happen.",
                ],
            },
            {
                heading: "Where an alert engine fits",
                paragraphs: [
                    "Polling a booking page yourself works only if you happen to be looking at the right minute. A watch flips that: you describe the film, city, formats and time window once, and the engine polls the source continuously and messages you the moment a matching show opens.",
                    "That is the entire premise of TicketFox. It does not book for you and it never touches your payment details — it just makes sure you are not the last to know.",
                ],
                quote:
                    "The seat is not won at checkout. It is won in the ten minutes before the listing goes public.",
            },
        ],
    },
    {
        slug: "bookmyshow-vs-district-ticket-alerts",
        title: "BookMyShow vs District: where tickets actually drop first",
        description:
            "The two big booking platforms do not publish showtimes at the same moment. Here is how the difference affects your chances of catching a drop.",
        date: "2026-11-08",
        readingMinutes: 6,
        tags: ["BookMyShow", "District", "Comparison"],
        sections: [
            {
                paragraphs: [
                    "Most moviegoers in India check one platform and assume the other has the same inventory at the same time. They usually do — but not always at the same moment, and that gap is where tickets get missed.",
                ],
            },
            {
                heading: "Same cinemas, different pipelines",
                paragraphs: [
                    "BookMyShow and District both surface inventory from the same theatre chains, but each platform ingests and publishes listings through its own pipeline. A theatre that pushes a show to one platform may take minutes — occasionally longer — to appear on the other.",
                    "For a film with a quiet release, that gap is irrelevant. For an IMAX opening night, a few minutes is the difference between a centre seat and a waitlist.",
                ],
            },
            {
                heading: "What this means in practice",
                list: [
                    "Watching a single platform is a coin flip on which one publishes first for a given theatre.",
                    "Watching both removes the guesswork — whichever lists first is the one that alerts you.",
                    "The platform that lists first is not consistent: it varies by chain, city and even by screen.",
                ],
            },
            {
                heading: "Why TicketFox polls both",
                paragraphs: [
                    "The engine treats BookMyShow and District as two independent sources for the same watch. It does not assume one is authoritative. When either source publishes a matching showtime, the alert fires.",
                    "This is also why the alert includes a direct link to the listing that triggered it: you land on the platform that actually has the seat, rather than searching for it again.",
                ],
            },
            {
                heading: "A note on reliability",
                paragraphs: [
                    "Both platforms sit behind Cloudflare and both change their markup from time to time. A polling engine has to handle challenge pages, rate limits and layout changes without silently reporting 'no shows'. TicketFox retries failed polls and surfaces a miss on the watch rather than pretending the show does not exist.",
                ],
            },
        ],
    },
    {
        slug: "premiere-show-booking-checklist",
        title: "The premiere-show booking checklist for Indian blockbusters",
        description:
            "A short, practical checklist to run before a big release: formats, accounts, payment, and the exact moment to stop refreshing and start booking.",
        date: "2026-11-03",
        readingMinutes: 5,
        tags: ["Premiere", "Checklist", "Booking strategy"],
        sections: [
            {
                paragraphs: [
                    "Premiere shows — the first screenings, often a day before the official release — are the hardest tickets in India to get. The seat count is small, the demand is enormous, and the announcement is usually last-minute.",
                    "This checklist is what to have ready before that announcement lands.",
                ],
            },
            {
                heading: "Before the drop",
                list: [
                    "Pick two acceptable formats and two acceptable time slots. Anything more is indecision; anything less is a missed seat.",
                    "Sign in to BookMyShow and District on the device you will book from, and confirm the session is still valid.",
                    "Save a payment method. Do not plan to type card details while seats disappear.",
                    "Know which cinemas in your city actually run the premium format — not every PVR has IMAX.",
                    "Set a watch for the film, city and formats so you are not relying on a social feed.",
                ],
            },
            {
                heading: "At the drop",
                list: [
                    "Open the direct link from the alert rather than searching the app again.",
                    "Choose the show, then the seats — do not browse other showtimes first.",
                    "If your first choice is gone, take your second format immediately. Do not wait to see if seats reappear.",
                    "Complete checkout in one pass. Abandoned carts release the seats back to the pool.",
                ],
            },
            {
                heading: "After the drop",
                paragraphs: [
                    "If you missed it, do not give up on the same day. Seats are released back when carts expire, and theatres occasionally open additional shows when the first ones sell out. A watch that stays active will catch those releases too.",
                ],
                quote:
                    "The people who get premiere seats are not luckier. They decided what they would accept before the seats existed.",
            },
        ],
    },
    {
        slug: "why-ticket-alerts-beat-refreshing",
        title: "Why a ticket alert beats refreshing the booking page",
        description:
            "Refreshing a booking page is a lottery you have to sit through. Here is the arithmetic of why continuous polling wins, and what a good alert actually contains.",
        date: "2026-10-27",
        readingMinutes: 6,
        tags: ["Alerts", "How it works", "Reliability"],
        sections: [
            {
                paragraphs: [
                    "Refreshing a booking page feels productive. It is not. It is a manual poll with a human latency of anywhere from thirty seconds to several hours, depending on whether you are awake, at work, or looking at your phone.",
                ],
            },
            {
                heading: "The arithmetic of missing a drop",
                paragraphs: [
                    "A premium show can open and sell out inside fifteen minutes. If you check the page every ten minutes, you have a real chance of missing the entire window. If you check every few seconds, you almost cannot.",
                    "The problem is that a human cannot check every few seconds for days. A machine can, and that is the whole trade: you describe the watch once, and the polling happens whether or not you are looking.",
                ],
            },
            {
                heading: "What a good alert contains",
                list: [
                    "The film, the cinema and the exact showtime that opened.",
                    "The format, so you know whether it is the IMAX show you wanted or a standard one.",
                    "A direct link to the listing, so there is no second search.",
                    "A timestamp, so you know how fresh the alert is.",
                ],
            },
            {
                heading: "What a good alert does not do",
                paragraphs: [
                    "It does not book for you, and it should not ask for your booking credentials. The moment an alert service wants your BookMyShow password or your card, it has stopped being an alert service and become a liability.",
                    "TicketFox is deliberately on the other side of that line: it watches, it tells you, and the booking stays in your hands on the cinema's own page.",
                ],
            },
            {
                heading: "Delivery has to be durable",
                paragraphs: [
                    "An alert that fails silently is worse than no alert, because you stop watching. Delivery is retried with backoff, and a miss is reported on the watch rather than hidden. That is the difference between a notification and a promise.",
                ],
            },
        ],
    },
    {
        slug: "what-a-showtime-listing-tells-you",
        title: "What a showtime listing actually tells you, and what it hides",
        description:
            "A listing looks like a simple row of times. Read closely and it tells you the screen, the format, the seat map and how fresh the data is — all of which change your odds.",
        date: "2026-10-19",
        readingMinutes: 6,
        tags: ["Showtimes", "Booking strategy", "Data"],
        sections: [
            {
                paragraphs: [
                    "A showtime listing looks like the simplest thing on a booking site: a film, a cinema, a row of times. But almost every detail that decides whether you get a good seat is already in that row, if you know what to read.",
                    "This is a short guide to reading a listing properly — and to the parts of it that are guesses dressed up as facts.",
                ],
            },
            {
                heading: "The screen is the real variable",
                paragraphs: [
                    "Two shows at the same cinema, at the same time, on the same day can be completely different experiences. One is on the largest screen with the premium projector; the other is in a small auditorium that was retrofitted a decade ago.",
                    "The listing usually names the screen or the format, and that name is the single most useful piece of information in the row. A 7:30 PM show in the IMAX auditorium and a 7:30 PM show in screen 4 are not the same ticket, even at the same price.",
                ],
            },
            {
                heading: "Format labels are not standardised",
                list: [
                    "IMAX is the one label that is broadly consistent, because the brand is licensed.",
                    "P[XL], ICE, ScreenX, 4DX and 'Large Screen' mean different things at different chains.",
                    "A chain's own premium brand may be a bigger screen, a better projector, recliners, or all three.",
                    "Dolby Atmos is a sound specification, not a screen size — it says nothing about the picture.",
                ],
            },
            {
                heading: "The seat map is the honest part",
                paragraphs: [
                    "Everything else in a listing is metadata the theatre typed in. The seat map is generated from the actual inventory, which makes it the most trustworthy signal on the page. A show that looks empty in the listing but has a full seat map is a show that is about to sell out.",
                    "This is also why an alert that links straight to the listing beats a screenshot: the seat map is live, and it is the only part of the page that cannot be stale.",
                ],
            },
            {
                heading: "What the listing hides",
                paragraphs: [
                    "A listing does not tell you when it was published, how many seats were released, or whether more shows will be added. Those are the three things that matter most during a big release, and none of them appear on the page.",
                    "That gap is exactly what a watch fills. It records the moment a listing appears, so the timestamp you never see on the booking site becomes the first thing you know.",
                ],
                quote:
                    "The listing tells you what exists. It never tells you what just appeared — and that is the only thing that matters at a drop.",
            },
        ],
    },
];

export function getPostBySlug(slug: string): BlogPost | undefined {
    return BLOG_POSTS.find((p) => p.slug === slug);
}

export function getAllSlugs(): string[] {
    return BLOG_POSTS.map((p) => p.slug);
}

/** Newest first. */
export function getSortedPosts(): BlogPost[] {
    return [...BLOG_POSTS].sort((a, b) => (a.date < b.date ? 1 : -1));
}

export function formatPostDate(iso: string): string {
    return new Date(`${iso}T00:00:00Z`).toLocaleDateString("en-IN", {
        day: "numeric",
        month: "long",
        year: "numeric",
        timeZone: "UTC",
    });
}

/** Short form for dense metadata rows, e.g. "12 Nov 2026". */
export function formatPostDateShort(iso: string): string {
    return new Date(`${iso}T00:00:00Z`).toLocaleDateString("en-IN", {
        day: "2-digit",
        month: "short",
        year: "numeric",
        timeZone: "UTC",
    });
}

/** The newest post, used as the lead story on the index. */
export function getLeadPost(): BlogPost {
    return getSortedPosts()[0];
}

/** Every tag in the archive with how many posts carry it, most-used first. */
export function getAllTags(): { tag: string; count: number }[] {
    const counts = new Map<string, number>();
    for (const post of BLOG_POSTS) {
        for (const tag of post.tags) {
            counts.set(tag, (counts.get(tag) ?? 0) + 1);
        }
    }
    return Array.from(counts.entries())
        .map(([tag, count]) => ({ tag, count }))
        .sort((a, b) => b.count - a.count || a.tag.localeCompare(b.tag));
}

/** Posts carrying a tag, newest first. */
export function getPostsByTag(tag: string): BlogPost[] {
    return getSortedPosts().filter((post) => post.tags.includes(tag));
}

/**
 * The posts either side of `slug` in reading order.
 * `previous` is older, `next` is newer.
 */
export function getAdjacentPosts(slug: string): {
    previous: BlogPost | null;
    next: BlogPost | null;
} {
    const ordered = getSortedPosts();
    const index = ordered.findIndex((post) => post.slug === slug);
    if (index === -1) return { previous: null, next: null };
    return {
        previous: ordered[index + 1] ?? null,
        next: ordered[index - 1] ?? null,
    };
}

/** Stable anchor id for a section heading. */
export function slugifyHeading(heading: string): string {
    return heading
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-+|-+$/g, "");
}

/** Section headings in document order, for the on-page table of contents. */
export function getPostHeadings(post: BlogPost): { id: string; heading: string }[] {
    return post.sections
        .filter((section): section is { heading: string } & typeof section =>
            Boolean(section.heading)
        )
        .map((section) => ({
            id: slugifyHeading(section.heading),
            heading: section.heading,
        }));
}
