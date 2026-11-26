"use client";

import React, { useState } from "react";
import { Heart, Star, Film, BellRing } from "lucide-react";

interface MovieCardProps {
  movie: any;
  onSelectMovie: (movie: any) => void;
  onViewDetails?: (movie: any) => void;
  eager?: boolean;
}

export default function MovieCard({ movie, onSelectMovie, onViewDetails, eager = false }: MovieCardProps) {
  const [imageError, setImageError] = useState(false);
  const poster =
    !imageError && movie.poster_url
      ? movie.poster_url
      : "https://images.unsplash.com/photo-1536440136628-849c177e76a1?w=500&auto=format&fit=crop&q=80";

  const likes = movie.likes_count || movie.likes || 0;
  const rating = movie.likes_pct ? (movie.likes_pct / 10).toFixed(1) : null;

  const handleCardClick = () => {
    if (onViewDetails) {
      onViewDetails(movie);
    } else {
      onSelectMovie(movie);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      handleCardClick();
    }
  };

  const status = (() => {
    if (movie.release_date) {
      const parts = movie.release_date.split("-");
      if (parts.length === 3) {
        const rd = new Date(parseInt(parts[0], 10), parseInt(parts[1], 10) - 1, parseInt(parts[2], 10));
        if (!isNaN(rd.getTime())) {
          const now = new Date();
          const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
          return rd <= today ? "In theatres" : "Upcoming";
        }
      }
    }
    return movie.source === "district" ? "District" : "BookMyShow";
  })();

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={handleCardClick}
      onKeyDown={handleKeyDown}
      className="movie-card"
    >
      <div className="movie-card-poster">
        <img
          src={poster}
          alt={movie.title || "Movie poster"}
          onError={() => setImageError(true)}
          className="movie-card-image"
          loading={eager ? "eager" : "lazy"}
          fetchPriority={eager ? "high" : "auto"}
        />

        {rating && (
          <span className="movie-card-rating">
            <Star className="w-3 h-3" aria-hidden="true" />
            <span>{rating}</span>
          </span>
        )}

        <div className="movie-card-action">
          <button
            onClick={(e) => {
              e.stopPropagation();
              onSelectMovie(movie);
            }}
            className="movie-card-watch"
          >
            <BellRing className="w-3.5 h-3.5" aria-hidden="true" />
            <span>Set watch</span>
          </button>
        </div>
      </div>

      <div className="movie-card-info">
        <h3 className="movie-card-title">{movie.title}</h3>

        <p className="movie-card-meta">
          <span>{movie.language || "Multi-language"}</span>
          {movie.release_date && <span className="movie-card-date">{movie.release_date}</span>}
        </p>

        <div className="movie-card-foot">
          {likes > 0 ? (
            <span className="movie-card-likes">
              <Heart className="w-3 h-3" aria-hidden="true" />
              {likes.toLocaleString()}
            </span>
          ) : (
            <span className="movie-card-status">
              <Film className="w-3 h-3" aria-hidden="true" />
              {status}
            </span>
          )}

          <span className="movie-card-track">
            <span>Track</span>
            <span aria-hidden="true">→</span>
          </span>
        </div>
      </div>
    </div>
  );
}
