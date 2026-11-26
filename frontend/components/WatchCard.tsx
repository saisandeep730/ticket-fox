"use client";

import React, { useState } from "react";
import {
  Bell,
  Pause,
  Play,
  Trash2,
  Calendar,
  Clock,
  MapPin,
  Zap,
  CheckCircle2,
  RefreshCw,
  Film,
  CalendarClock,
  Timer,
  BellRing,
  RotateCcw,
  IndianRupee,
} from "lucide-react";
import type { WatchGroup } from "../lib/watches";

interface WatchCardProps {
  group: WatchGroup;
  onTogglePause: (ids: string[], currentActive: boolean) => void;
  onDelete: (ids: string[]) => void;
  onTestDrill?: (ids: string[]) => void;
  isBatchMode?: boolean;
  isSelected?: boolean;
  onToggleSelect?: (ids: string[]) => void;
}

function timeAgo(isoString: string | null): string {
  if (!isoString) return "Never";
  try {
    const date = new Date(isoString.endsWith("Z") ? isoString : isoString + "Z");
    const seconds = Math.floor((Date.now() - date.getTime()) / 1000);
    if (seconds < 10) return "Just now";
    if (seconds < 60) return `${seconds}s ago`;
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    return `${days}d ago`;
  } catch {
    return "Recently";
  }
}

export default function WatchCard({
  group,
  onTogglePause,
  onDelete,
  onTestDrill,
  isBatchMode = false,
  isSelected = false,
  onToggleSelect,
}: WatchCardProps) {
  const [imageError, setImageError] = useState(false);
  const watch = group.primary;
  const ids = group.ids;

  const isAvailable = group.isAvailable;
  const isExpired = group.isExpired;
  const isPaused = group.isPaused;
  const poster = !imageError && watch.poster_url ? watch.poster_url : "";

  const timeWindow = watch.after_time
    ? `${watch.after_time} - ${watch.before_time || "End"}`
    : "Any Time";

  const rawDateFilter =
    Array.isArray(watch.date_filter) && watch.date_filter.length > 0
      ? watch.date_filter
      : ["all"];

  const formatSingleDate = (d: string) => {
    if (d === "all") return "All Dates";
    if (d === "premier") return "Premiere Night";
    if (d === "premier_2days") return "Early Previews (2d before)";
    if (d === "first_day") return "Day 1";
    if (d.match(/^\d{4}-\d{2}-\d{2}$/)) return d;
    return d;
  };

  const dateFilter = rawDateFilter
    .map(formatSingleDate)
    .filter((v: string, i: number, a: string[]) => a.indexOf(v) === i)
    .join(", ");

  const theatreLabel =
    !watch.theatres || watch.theatres.length === 0
      ? "Any Cinema"
      : `${watch.theatres.length} cinema${watch.theatres.length > 1 ? "s" : ""}`;

  let daysUntilRelease: number | null = null;
  const relDateString =
    watch.release_date ||
    (Array.isArray(watch.date_filter)
      ? watch.date_filter.find((d: string) => typeof d === "string" && d.match(/^\d{4}-\d{2}-\d{2}$/))
      : null);
  if (relDateString) {
    try {
      const relDt = new Date(relDateString);
      const now = new Date();
      daysUntilRelease = Math.ceil((relDt.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
    } catch { }
  }

  const cardState = isSelected
    ? "is-selected"
    : isAvailable
      ? "is-available"
      : isExpired
        ? "is-expired"
        : isPaused
          ? "is-paused"
          : "";

  const iconState = isAvailable
    ? "is-available"
    : isExpired
      ? "is-expired"
      : isPaused
        ? "is-paused"
        : "is-hunting";

  return (
    <div
      onClick={() => {
        if (isBatchMode && onToggleSelect) {
          onToggleSelect(ids);
        }
      }}
      className={`watch-card ${cardState}${isBatchMode ? " is-batch" : ""}`}
    >
      <div className="watch-card-body">
        {/* Left: Info Section */}
        <div className="watch-card-main">
          {/* Batch Mode Checkbox */}
          {isBatchMode && (
            <div className="watch-card-check">
              <input
                type="checkbox"
                checked={isSelected}
                onChange={() => onToggleSelect && onToggleSelect(ids)}
                className="watch-card-checkbox"
                aria-label={`Select ${watch.movie_title || watch.movie_id}`}
              />
            </div>
          )}

          {/* Poster or Icon */}
          {poster ? (
            <div className="watch-card-poster">
              <img
                src={poster}
                alt={watch.movie_title || "Watch poster"}
                onError={() => setImageError(true)}
              />
              {isAvailable && (
                <div className="watch-card-poster-overlay">
                  <CheckCircle2 className="w-6 h-6" aria-hidden="true" />
                </div>
              )}
            </div>
          ) : (
            <div className={`watch-card-icon ${iconState}`}>
              <Bell className="w-5 h-5 sm:w-6 sm:h-6" aria-hidden="true" />
            </div>
          )}

          <div className="watch-card-info">
            {/* Title & Status Badges */}
            <div className="watch-card-title-row">
              <h3 className="watch-card-title">{watch.movie_title || watch.movie_id}</h3>

              {/* Status Badge */}
              {isAvailable ? (
                <span className="badge badge--success">
                  <span className="w-1.5 h-1.5 rounded-full bg-current animate-ping" />
                  BOOKING OPEN!
                </span>
              ) : isExpired ? (
                <span className="badge badge--muted">EXPIRED</span>
              ) : isPaused ? (
                <span className="badge badge--muted">PAUSED</span>
              ) : daysUntilRelease !== null && daysUntilRelease > 14 ? (
                <span
                  className="badge badge--warning"
                  title={`Release is ${daysUntilRelease} days away. Auto-activates 14 days before release.`}
                >
                  <CalendarClock className="w-3 h-3" aria-hidden="true" />
                  SCHEDULED ({daysUntilRelease}d away)
                </span>
              ) : daysUntilRelease !== null && daysUntilRelease > 3 ? (
                <span
                  className="badge badge--accent-2"
                  title="15-minute polling active. Will switch to ultra real-time closer to release."
                >
                  <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse" />
                  <Timer className="w-3 h-3" aria-hidden="true" />
                  15-MIN RADAR
                </span>
              ) : (
                <span className="badge badge--accent">
                  <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse" />
                  <Zap className="w-3 h-3" aria-hidden="true" />
                  REAL-TIME HUNTING
                </span>
              )}

              {/* Source Tags — one per platform in the group */}
              <span className="watch-card-sources">
                {group.sources.map((source) => (
                  <span key={source} className="badge badge--muted uppercase">
                    {source}
                  </span>
                ))}
              </span>

              {/* Smart Trigger Badges */}
              {watch.notify_new_shows && (
                <span className="badge badge--accent-2">
                  <BellRing className="w-3 h-3" aria-hidden="true" />
                  New Shows
                </span>
              )}
              {watch.notify_back && (
                <span className="badge badge--success">
                  <RotateCcw className="w-3 h-3" aria-hidden="true" />
                  Re-Stock
                </span>
              )}
            </div>

            {/* Filter Specs Row */}
            <div className="watch-card-specs">
              <span className="watch-card-spec is-strong">
                <MapPin className="watch-card-spec-icon is-accent" aria-hidden="true" />
                <span>
                  {watch.city} ({theatreLabel})
                </span>
              </span>
              <span className="watch-card-spec">
                <Calendar className="watch-card-spec-icon" aria-hidden="true" />
                <span>{dateFilter}</span>
              </span>
              <span className="watch-card-spec">
                <Clock className="watch-card-spec-icon" aria-hidden="true" />
                <span>{timeWindow}</span>
              </span>
              {Array.isArray(watch.formats) && watch.formats.length > 0 && (
                <span className="badge badge--warning">
                  <Film className="w-3 h-3" aria-hidden="true" />
                  {watch.formats.join(", ")}
                </span>
              )}
              {watch.max_price && (
                <span className="badge badge--success">
                  <IndianRupee className="w-3 h-3" aria-hidden="true" />
                  Max {watch.max_price}
                </span>
              )}
            </div>

            {/* Timestamps & Attempt Status */}
            <div className="watch-card-times">
              <span className="watch-card-spec">
                <RefreshCw className="watch-card-spec-icon" aria-hidden="true" />
                <span>Checked {timeAgo(watch.last_checked_at)}</span>
              </span>
              {watch.notified_at && (
                <span className="is-success watch-card-spec">
                  <CheckCircle2 className="w-3 h-3" aria-hidden="true" />
                  <span>Alerted {timeAgo(watch.notified_at)}</span>
                </span>
              )}
              {watch.notify_attempts > 0 && !watch.notified_at && (
                <span
                  className="is-warning"
                  title={watch.notify_last_error || "Delivery retrying"}
                >
                  • Retrying alert ({watch.notify_attempts}/5)
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Right: Actions Toolbar */}
        <div className="watch-card-actions">
          {onTestDrill && (
            <button
              onClick={() => onTestDrill(ids)}
              className="watch-card-action is-test"
              title="Send a test notification to your configured channels"
            >
              <Zap className="w-3.5 h-3.5" aria-hidden="true" />
              <span>Test Drill</span>
            </button>
          )}

          <button
            onClick={() => onTogglePause(ids, group.isActive)}
            className={`watch-card-action ${group.isActive ? "is-pause" : "is-resume"}`}
            title={group.isActive ? "Pause ticket watch" : "Resume ticket watch"}
            aria-label={group.isActive ? "Pause ticket watch" : "Resume ticket watch"}
          >
            {group.isActive ? (
              <Pause className="w-4 h-4" aria-hidden="true" />
            ) : (
              <Play className="w-4 h-4" aria-hidden="true" />
            )}
          </button>

          <button
            onClick={() => onDelete(ids)}
            className="watch-card-action is-delete"
            title="Delete ticket watch"
            aria-label="Delete ticket watch"
          >
            <Trash2 className="w-4 h-4" aria-hidden="true" />
          </button>
        </div>
      </div>
    </div>
  );
}
