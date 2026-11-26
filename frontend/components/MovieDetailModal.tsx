"use client";

import React, { useState, useEffect } from "react";
import {
  X,
  Star,
  Calendar,
  Clock,
  Flame,
  Bell,
  Film,
  Play,
  User,
  Rocket,
  Loader2,
} from "lucide-react";
import { apiFetch } from "../lib/api";
import TicketFoxLogo from "./TicketFoxLogo";

interface MovieDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  movie: any;
  city: string;
  onStartWatch: (movie: any) => void;
}

export default function MovieDetailModal({
  isOpen,
  onClose,
  movie,
  city,
  onStartWatch,
}: MovieDetailModalProps) {
  const [details, setDetails] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [showTrailer, setShowTrailer] = useState(false);

  useEffect(() => {
    if (isOpen && movie) {
      setLoading(true);
      setShowTrailer(false);
      setDetails(null);
      const title = movie.title || movie.name || "";
      const movieId = movie.id || movie.eventCode || "";
      const posterUrl = movie.poster_url || movie.poster || "";
      apiFetch(
        `/api/movie/info?title=${encodeURIComponent(title)}&movie_id=${encodeURIComponent(
          movieId
        )}&poster_url=${encodeURIComponent(posterUrl)}`
      )
        .then((data) => {
          setDetails(data?.movie || null);
        })
        .catch((err) => {
          console.error("Failed to load movie info:", err);
          setDetails(null);
        })
        .finally(() => setLoading(false));
    }
  }, [isOpen, movie]);

  useEffect(() => {
    if (!isOpen) return;
    function handleKey(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [isOpen, onClose]);

  if (!isOpen || !movie) return null;

  const title = details?.title || movie.title || movie.name || "Movie Details";
  const poster = details?.poster_url || movie.poster_url || "";
  const backdrop = details?.backdrop_url || poster;
  const rating = details?.rating || (movie.likes_pct ? (movie.likes_pct / 10).toFixed(1) : null);
  const voteCount = details?.vote_count ? details.vote_count.toLocaleString() : null;
  const releaseDate = details?.release_date || movie.release_date || "Upcoming";
  const runtime = details?.runtime || "2h 30m";
  const director = details?.director || "";
  const writers = details?.writers || [];
  const cast = details?.cast || [];
  const trailerKey = details?.trailer_key || "";

  return (
    <div role="dialog" aria-modal="true" aria-label={`${title} details`} className="modal-backdrop">
      <div className="detail-panel">
        {/* Top bar */}
        <div className="detail-topbar">
          <TicketFoxLogo size="sm" />

          <div className="detail-topbar-meta">
            <span className="detail-topbar-tag">Cinema Intel</span>
            {loading ? (
              <span className="detail-topbar-loading">
                <Loader2 className="w-3.5 h-3.5 animate-spin" aria-hidden="true" />
                Fetching details
              </span>
            ) : (
              <>
                <span>{releaseDate.split("-")[0] || "Upcoming"}</span>
                <span aria-hidden="true">·</span>
                <span className="detail-topbar-tag">UA / PG-13</span>
                <span aria-hidden="true">·</span>
                <span>{runtime}</span>
              </>
            )}
          </div>

          <button
            type="button"
            onClick={onClose}
            aria-label="Close details dialog"
            className="icon-btn"
          >
            <X className="w-4 h-4" aria-hidden="true" />
          </button>
        </div>

        {/* Scrollable body */}
        <div className="detail-scroll">
          {/* Hero */}
          <div className="detail-hero">
            {showTrailer && trailerKey ? (
              <>
                <iframe
                  src={`https://www.youtube-nocookie.com/embed/${trailerKey}?autoplay=1`}
                  title="Official Trailer"
                  className="detail-trailer-frame"
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                  allowFullScreen
                />
                <button
                  type="button"
                  onClick={() => setShowTrailer(false)}
                  className="detail-trailer-close"
                >
                  <X className="w-3.5 h-3.5" aria-hidden="true" />
                  <span>Close Trailer</span>
                </button>
              </>
            ) : (
              <>
                {backdrop ? (
                  <img src={backdrop} alt={title} className="detail-hero-media" />
                ) : (
                  <div className="detail-hero-fallback" aria-hidden="true" />
                )}

                <div className="detail-hero-fade" aria-hidden="true" />

                <div className="detail-hero-actions">
                  {rating ? (
                    <div className="detail-rating">
                      <Star
                        className="w-4 h-4"
                        style={{ color: "var(--color-warning)", fill: "var(--color-warning)" }}
                        aria-hidden="true"
                      />
                      <span className="detail-rating-value">
                        {rating}
                        <span className="detail-rating-max"> /10</span>
                      </span>
                      {voteCount ? <span className="detail-rating-votes">{voteCount} votes</span> : null}
                    </div>
                  ) : null}

                  {trailerKey ? (
                    <button
                      type="button"
                      onClick={() => setShowTrailer(true)}
                      className="detail-trailer-btn"
                    >
                      <Play className="w-3.5 h-3.5" aria-hidden="true" />
                      <span>Watch Trailer</span>
                    </button>
                  ) : null}
                </div>

                <div className="detail-hero-foot">
                  {poster ? (
                    <img src={poster} alt="" className="detail-poster" />
                  ) : null}

                  <div className="detail-hero-info">
                    <div className="detail-chips">
                      <span className="badge badge--accent">
                        <Flame className="w-3 h-3" aria-hidden="true" />
                        <span>{details?.is_tmdb_matched ? "TMDB Verified" : "BookMyShow Verified"}</span>
                      </span>
                      {details?.genres?.map((g: string) => (
                        <span key={g} className="badge badge--muted">
                          {g}
                        </span>
                      ))}
                    </div>

                    <h1 className="detail-title">{title}</h1>

                    <p className="detail-meta">
                      <span className="detail-meta-item">
                        <Calendar
                          className="w-3.5 h-3.5"
                          style={{ color: "var(--color-accent)" }}
                          aria-hidden="true"
                        />
                        Release: {releaseDate}
                      </span>
                      <span aria-hidden="true">·</span>
                      <span className="detail-meta-item">
                        <Clock className="w-3.5 h-3.5" aria-hidden="true" />
                        {runtime}
                      </span>
                      <span aria-hidden="true">·</span>
                      <span className="detail-meta-city">{city}</span>
                    </p>
                  </div>
                </div>
              </>
            )}
          </div>

          {/* Body */}
          <div className="detail-body">
            {/* Primary action: one big Track Now button */}
            <button
              type="button"
              onClick={() => {
                onClose();
                onStartWatch(movie);
              }}
              className="detail-track-cta"
            >
              <Rocket className="w-5 h-5" aria-hidden="true" />
              <span>Track Now</span>
            </button>

            {/* Synopsis */}
            <div>
              <h3 className="detail-section-title">
                <Film
                  className="w-3.5 h-3.5"
                  style={{ color: "var(--color-accent)" }}
                  aria-hidden="true"
                />
                Storyline & Overview
              </h3>
              {loading ? (
                <div className="detail-synopsis" aria-busy="true">
                  <div className="skeleton" style={{ height: "0.75rem", width: "75%", marginBottom: "0.5rem" }} />
                  <div className="skeleton" style={{ height: "0.75rem", width: "100%", marginBottom: "0.5rem" }} />
                  <div className="skeleton" style={{ height: "0.75rem", width: "50%" }} />
                </div>
              ) : (
                <p className="detail-synopsis">
                  {details?.overview ||
                    movie.synopsis ||
                    `Track ticket availability for ${title} on TicketFox. Receive instant alerts on WhatsApp and email as soon as cinema bookings open.`}
                </p>
              )}
            </div>

            {/* Credits */}
            {director || writers.length > 0 ? (
              <div className="detail-credits">
                {director ? (
                  <div className="detail-credit">
                    <User
                      className="w-4 h-4 shrink-0"
                      style={{ color: "var(--color-accent)" }}
                      aria-hidden="true"
                    />
                    <div>
                      <span className="detail-credit-label">Director</span>
                      <strong className="detail-credit-value">{director}</strong>
                    </div>
                  </div>
                ) : null}
                {writers.length > 0 ? (
                  <div className="detail-credit">
                    <Film
                      className="w-4 h-4 shrink-0"
                      style={{ color: "var(--color-accent-2)" }}
                      aria-hidden="true"
                    />
                    <div>
                      <span className="detail-credit-label">Writers</span>
                      <strong className="detail-credit-value">{writers.join(", ")}</strong>
                    </div>
                  </div>
                ) : null}
              </div>
            ) : null}

            {/* Cast */}
            <div>
              <h3 className="detail-section-title">
                <User
                  className="w-3.5 h-3.5"
                  style={{ color: "var(--color-accent)" }}
                  aria-hidden="true"
                />
                Top Billed Cast
              </h3>
              {loading ? (
                <div className="detail-cast-grid" aria-busy="true">
                  {[...Array(6)].map((_, i) => (
                    <div key={i} className="detail-cast-card">
                      <div className="skeleton" style={{ width: "3rem", height: "3rem", borderRadius: "999px" }} />
                      <div className="skeleton" style={{ height: "0.6rem", width: "75%" }} />
                    </div>
                  ))}
                </div>
              ) : cast && cast.length > 0 ? (
                <div className="detail-cast-grid">
                  {cast.slice(0, 8).map((c: any, i: number) => (
                    <div key={i} className="detail-cast-card">
                      {c.profile_path ? (
                        <img src={c.profile_path} alt="" className="detail-cast-avatar" />
                      ) : (
                        <div className="detail-cast-fallback" aria-hidden="true">
                          {c.name?.[0] || "?"}
                        </div>
                      )}
                      <h4 className="detail-cast-name">{c.name}</h4>
                      <p className="detail-cast-role">{c.character}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="detail-cast-empty">
                  Cast & crew details will update as cinema showtimes are announced.
                </p>
              )}
            </div>

            {/* Specs */}
            <div className="detail-specs">
              <div className="detail-spec">
                <span className="detail-spec-label">Release Date</span>
                <span className="detail-spec-value">{releaseDate}</span>
              </div>
              <div className="detail-spec">
                <span className="detail-spec-label">Runtime</span>
                <span className="detail-spec-value">{runtime}</span>
              </div>
              <div className="detail-spec">
                <span className="detail-spec-label">Target City</span>
                <span className="detail-spec-value">{city}</span>
              </div>
              <div className="detail-spec">
                <span className="detail-spec-label">Formats</span>
                <span className="detail-spec-value is-accent">IMAX 3D, 4DX, 2D</span>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="detail-foot">
          <div className="detail-foot-provider">
            Provider: <strong>{movie.source || "BookMyShow"}</strong>
          </div>

          <div className="detail-foot-actions">
            <button type="button" onClick={onClose} className="modal-btn-quiet">
              Close
            </button>

            <button
              type="button"
              onClick={() => {
                onClose();
                onStartWatch(movie);
              }}
              className="modal-btn-accent"
            >
              <Bell className="w-3.5 h-3.5" aria-hidden="true" />
              <span>Start Ticket Alert</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
