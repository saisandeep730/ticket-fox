import { apiFetch } from "./api";

export const TMDB_IMG_URL = "https://image.tmdb.org/t/p/w500";
export const TMDB_BACKDROP_URL = "https://image.tmdb.org/t/p/original";

export interface TMDBMovie {
  id: number;
  title: string;
  overview: string;
  poster_path: string | null;
  backdrop_path: string | null;
  release_date: string;
  vote_average: number;
  runtime?: number;
  genres?: { id: number; name: string }[];
}

export interface TMDBAuthorCast {
  id: number;
  name: string;
  character: string;
  profile_path: string | null;
}

export interface TMDBWatchProvider {
  provider_id: number;
  provider_name: string;
  logo_path: string;
}

/**
 * Read TMDB through the backend proxy so the API key stays server-side.
 * `endpoint` is a TMDB path such as `/movie/123?language=en-US`.
 */
export async function fetchTMDBData<T = any>(endpoint: string): Promise<T> {
  const [path, query = ""] = endpoint.split("?");
  const params = new URLSearchParams(query);
  const language = params.get("language") || "en-US";
  const url = `/api/tmdb?path=${encodeURIComponent(path)}&language=${encodeURIComponent(language)}`;
  try {
    return (await apiFetch(url)) as T;
  } catch (error) {
    console.error("TMDB proxy error:", error);
    return { results: [] } as unknown as T;
  }
}

export async function getTrendingMovies(): Promise<TMDBMovie[]> {
  const data = await fetchTMDBData<{ results: TMDBMovie[] }>("/trending/movie/week?language=en-US");
  return data.results || [];
}

export async function getTopRatedMovies(): Promise<TMDBMovie[]> {
  const data = await fetchTMDBData<{ results: TMDBMovie[] }>("/movie/top_rated?language=en-US&page=1");
  return data.results || [];
}

export async function getGenreMovies(genreId: number): Promise<TMDBMovie[]> {
  const data = await fetchTMDBData<{ results: TMDBMovie[] }>(`/discover/movie?with_genres=${genreId}&language=en-US`);
  return data.results || [];
}

export async function searchMovies(query: string): Promise<TMDBMovie[]> {
  if (!query || query.trim().length < 2) return [];
  const data = await fetchTMDBData<{ results: TMDBMovie[] }>(`/search/movie?query=${encodeURIComponent(query)}&page=1`);
  return data.results || [];
}

export async function getMovieDetails(id: number): Promise<{
  movie: TMDBMovie;
  cast: TMDBAuthorCast[];
  trailerKey: string | null;
  providers: TMDBWatchProvider[];
  recommendations: TMDBMovie[];
}> {
  const [movie, credits, videos, watchProviders, recs] = await Promise.all([
    fetchTMDBData<TMDBMovie>(`/movie/${id}?language=en-US`),
    fetchTMDBData<{ cast: TMDBAuthorCast[] }>(`/movie/${id}/credits?language=en-US`),
    fetchTMDBData<{ results: { type: string; site: string; key: string }[] }>(`/movie/${id}/videos?language=en-US`),
    fetchTMDBData<{ results: Record<string, { flatrate?: TMDBWatchProvider[] }> }>(`/movie/${id}/watch/providers`),
    fetchTMDBData<{ results: TMDBMovie[] }>(`/movie/${id}/recommendations?language=en-US&page=1`)
  ]);

  const trailer = videos?.results?.find((v) => v.type === "Trailer" && v.site === "YouTube");
  const providers = watchProviders?.results?.IN?.flatrate || watchProviders?.results?.US?.flatrate || [];

  return {
    movie,
    cast: credits?.cast?.slice(0, 8) || [],
    trailerKey: trailer ? trailer.key : null,
    providers: providers.slice(0, 6),
    recommendations: recs?.results?.slice(0, 6) || []
  };
}
