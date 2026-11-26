/**
 * Group the raw watch rows returned by the API into one card per movie.
 *
 * A single "Track Now" with platform = both creates two database rows (one
 * BookMyShow, one District) because the worker polls per (source, movie_id,
 * region). The UI should still read as one hunt, so we fold rows that share a
 * movie title + city into a single group and fan actions out over every id.
 */

export type WatchRow = {
    id: string;
    source?: string;
    movie_id?: string;
    movie_title?: string;
    city?: string;
    state?: string;
    is_active?: boolean;
    expired_at?: string | null;
    [key: string]: any;
};

export type WatchGroup = {
    key: string;
    watches: WatchRow[];
    primary: WatchRow;
    ids: string[];
    sources: string[];
    isActive: boolean;
    isExpired: boolean;
    isAvailable: boolean;
    isPaused: boolean;
};

function normalizeTitle(value: unknown): string {
    return String(value ?? "")
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, " ")
        .trim();
}

function normalizeCity(value: unknown): string {
    return String(value ?? "")
        .toLowerCase()
        .trim();
}

function sourceLabel(watch: WatchRow): string {
    const raw = String(watch?.source ?? "").toLowerCase();
    if (raw.includes("district")) return "District";
    if (raw.includes("bookmyshow") || raw === "bms") return "BookMyShow";
    return watch?.source ? String(watch.source) : "BMS";
}

export function groupWatches(watches: WatchRow[]): WatchGroup[] {
    const groups = new Map<string, WatchRow[]>();

    for (const watch of watches || []) {
        if (!watch) continue;
        const title = normalizeTitle(watch.movie_title || watch.movie_id);
        const city = normalizeCity(watch.city);
        const key = `${title}::${city}`;
        const bucket = groups.get(key);
        if (bucket) bucket.push(watch);
        else groups.set(key, [watch]);
    }

    const result: WatchGroup[] = [];

    groups.forEach((rows, key) => {
        // Prefer an available row as the primary so the card shows the best state.
        const primary =
            rows.find((w) => w.state === "AVAILABLE") ||
            rows.find((w) => w.is_active) ||
            rows[0];

        const sources: string[] = [];
        for (const row of rows) {
            const label = sourceLabel(row);
            if (!sources.includes(label)) sources.push(label);
        }

        const isExpired = rows.every((w) => Boolean(w.expired_at));
        const isAvailable = rows.some((w) => w.state === "AVAILABLE");
        const isActive = rows.some((w) => w.is_active && !w.expired_at);
        const isPaused = !isActive && !isExpired;

        result.push({
            key,
            watches: rows,
            primary,
            ids: rows.map((w) => w.id),
            sources,
            isActive,
            isExpired,
            isAvailable,
            isPaused,
        });
    });

    return result;
}
