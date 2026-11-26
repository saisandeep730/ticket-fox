import { apiFetch } from "./api";

export interface City {
    key: string;
    name: string;
}

/**
 * Fallback used before the backend catalog loads (and if it is unreachable).
 * The backend `/api/cities` endpoint is the source of truth.
 */
export const FALLBACK_CITIES: City[] = [
    { key: "hyderabad", name: "Hyderabad" },
    { key: "mumbai", name: "Mumbai" },
    { key: "delhi-ncr", name: "Delhi-NCR" },
    { key: "bengaluru", name: "Bengaluru" },
    { key: "chennai", name: "Chennai" },
    { key: "kolkata", name: "Kolkata" },
    { key: "pune", name: "Pune" },
    { key: "kochi", name: "Kochi" },
    { key: "ahmedabad", name: "Ahmedabad" },
    { key: "chandigarh", name: "Chandigarh" },
];

let cache: City[] | null = null;

/** Fetch the canonical city catalog once, falling back to the static list. */
export async function loadCities(): Promise<City[]> {
    if (cache) return cache;
    try {
        const data = await apiFetch("/api/cities");
        if (Array.isArray(data?.cities) && data.cities.length > 0) {
            cache = data.cities as City[];
            return cache;
        }
    } catch {
        // fall through to the static list
    }
    cache = FALLBACK_CITIES;
    return cache;
}
