"use client";

import React, { useState, useEffect } from "react";
import {
  X,
  Search,
  Check,
  MapPin,
  Bell,
  Flame,
  CheckCircle2,
  Loader2,
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  Calendar as CalendarIcon,
  MessageSquare,
  Sparkles,
  Ticket,
  Film,
  Globe,
  Zap,
  RotateCcw,
  Rocket,
} from "lucide-react";
import { apiFetch } from "../lib/api";
import { toIndianDigits } from "../lib/phone";

interface WatchWizardModalProps {
  isOpen: boolean;
  onClose: () => void;
  city: string;
  initialMovie?: any;
  onSubmitWatch: (watchData: any) => Promise<void>;
  userToken?: string;
  user?: any;
}

const TIME_PRESETS = [
  { id: "any", label: "Any Time", after: "", before: "" },
  { id: "morning", label: "Morning (Before 12 PM)", after: "00:00", before: "12:00" },
  { id: "matinee", label: "Matinee (12 PM - 4 PM)", after: "12:00", before: "16:00" },
  { id: "evening", label: "Evening (4 PM - 9 PM)", after: "16:00", before: "21:00" },
  { id: "night", label: "Night (After 9 PM)", after: "21:00", before: "23:59" },
];

function formatYYYYMMDD(year: number, month: number, day: number): string {
  const y = year.toString();
  const m = (month + 1).toString().padStart(2, "0");
  const d = day.toString().padStart(2, "0");
  return `${y}-${m}-${d}`;
}

function getTodayYYYYMMDD(): string {
  const d = new Date();
  return formatYYYYMMDD(d.getFullYear(), d.getMonth(), d.getDate());
}

/** Visual calendar date picker component */
function VisualCalendar({
  selectedDates,
  onToggleDate,
  releaseDate,
}: {
  selectedDates: string[];
  onToggleDate: (date: string) => void;
  releaseDate?: string;
}) {
  const todayStr = getTodayYYYYMMDD();

  const [viewDate, setViewDate] = useState(() => {
    const firstIso = selectedDates.find((d) => /^\d{4}-\d{2}-\d{2}$/.test(d));
    if (firstIso) {
      const [y, m, d] = firstIso.split("-").map(Number);
      return new Date(y, m - 1, d);
    }
    if (releaseDate && releaseDate.match(/^\d{4}-\d{2}-\d{2}$/)) {
      const [y, m, d] = releaseDate.split("-").map(Number);
      return new Date(y, m - 1, d);
    }
    return new Date();
  });

  const year = viewDate.getFullYear();
  const month = viewDate.getMonth();

  const monthNames = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
  ];
  const dayNames = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"];

  const firstDayOfMonth = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();

  const relISO = releaseDate && releaseDate.match(/^\d{4}-\d{2}-\d{2}$/) ? releaseDate : "";
  let prem1ISO = "";
  let prem2ISO = "";
  if (relISO) {
    const [y, m, d] = relISO.split("-").map(Number);
    const relDt = new Date(y, m - 1, d);
    const p1 = new Date(relDt); p1.setDate(p1.getDate() - 1);
    const p2 = new Date(relDt); p2.setDate(p2.getDate() - 2);
    prem1ISO = formatYYYYMMDD(p1.getFullYear(), p1.getMonth(), p1.getDate());
    prem2ISO = formatYYYYMMDD(p2.getFullYear(), p2.getMonth(), p2.getDate());
  }

  const handlePrevMonth = () => {
    setViewDate(new Date(year, month - 1, 1));
  };

  const handleNextMonth = () => {
    setViewDate(new Date(year, month + 1, 1));
  };

  const getFormattedSelectedDate = (dateStr: string) => {
    if (!dateStr || !dateStr.match(/^\d{4}-\d{2}-\d{2}$/)) return "";
    const [y, m, d] = dateStr.split("-").map(Number);
    const dateObj = new Date(y, m - 1, d);
    return dateObj.toLocaleDateString("en-US", {
      weekday: "short",
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  return (
    <div className="wizard-cal">
      {/* Month & Year header */}
      <div className="wizard-cal-head">
        <button
          type="button"
          onClick={handlePrevMonth}
          className="wizard-cal-nav"
          aria-label="Previous month"
        >
          <ChevronLeft className="w-4 h-4" aria-hidden="true" />
        </button>
        <h4 className="wizard-cal-title">
          <CalendarIcon
            className="w-3.5 h-3.5"
            style={{ color: "var(--color-accent)" }}
            aria-hidden="true"
          />
          <span>
            {monthNames[month]} {year}
          </span>
        </h4>
        <button
          type="button"
          onClick={handleNextMonth}
          className="wizard-cal-nav"
          aria-label="Next month"
        >
          <ChevronRight className="w-4 h-4" aria-hidden="true" />
        </button>
      </div>

      {/* Quick date presets */}
      {(relISO || prem1ISO || prem2ISO) && (
        <div className="wizard-cal-presets">
          {relISO && (
            <button
              type="button"
              onClick={() => {
                onToggleDate(relISO);
                const [y, m, d] = relISO.split("-").map(Number);
                setViewDate(new Date(y, m - 1, d));
              }}
              className={`wizard-cal-preset is-release${selectedDates.includes(relISO) ? " is-selected" : ""}`}
            >
              <Ticket className="w-3 h-3" aria-hidden="true" />
              Release Day ({relISO})
            </button>
          )}
          {prem1ISO && (
            <button
              type="button"
              onClick={() => {
                onToggleDate(prem1ISO);
                const [y, m, d] = prem1ISO.split("-").map(Number);
                setViewDate(new Date(y, m - 1, d));
              }}
              className={`wizard-cal-preset is-premiere${selectedDates.includes(prem1ISO) ? " is-selected" : ""}`}
            >
              <Film className="w-3 h-3" aria-hidden="true" />
              Premiere Night (1d before)
            </button>
          )}
          {prem2ISO && (
            <button
              type="button"
              onClick={() => {
                onToggleDate(prem2ISO);
                const [y, m, d] = prem2ISO.split("-").map(Number);
                setViewDate(new Date(y, m - 1, d));
              }}
              className={`wizard-cal-preset${selectedDates.includes(prem2ISO) ? " is-selected" : ""}`}
            >
              <Sparkles className="w-3 h-3" aria-hidden="true" />
              Early Previews (2d before)
            </button>
          )}
        </div>
      )}

      {/* Selected dates banner */}
      {selectedDates.some((d) => /^\d{4}-\d{2}-\d{2}$/.test(d)) && (
        <div className="wizard-cal-selected">
          <CalendarIcon className="w-3 h-3" aria-hidden="true" />
          <span>Dates:</span>
          <strong>
            {selectedDates
              .filter((d) => /^\d{4}-\d{2}-\d{2}$/.test(d))
              .map((d) => getFormattedSelectedDate(d))
              .join(" · ")}
          </strong>
        </div>
      )}

      {/* Weekday header */}
      <div className="wizard-cal-week" aria-hidden="true">
        {dayNames.map((d) => (
          <span key={d}>{d}</span>
        ))}
      </div>

      {/* Days grid */}
      <div className="wizard-cal-grid">
        {Array.from({ length: firstDayOfMonth }).map((_, i) => (
          <div key={`offset-${i}`} aria-hidden="true" />
        ))}

        {Array.from({ length: daysInMonth }).map((_, i) => {
          const dayNum = i + 1;
          const dateISO = formatYYYYMMDD(year, month, dayNum);
          const isSelected = selectedDates.includes(dateISO);
          const isToday = todayStr === dateISO;
          const isRelease = relISO === dateISO;
          const isPremiere = prem1ISO === dateISO || prem2ISO === dateISO;
          const isPast = dateISO < todayStr;

          const classes = [
            "wizard-cal-day",
            isRelease ? "is-release" : "",
            isPremiere ? "is-premiere" : "",
            isToday ? "is-today" : "",
            isSelected ? "is-selected" : "",
          ]
            .filter(Boolean)
            .join(" ");

          return (
            <button
              key={dateISO}
              type="button"
              disabled={isPast}
              onClick={() => onToggleDate(dateISO)}
              aria-pressed={isSelected}
              className={classes}
            >
              <span>{dayNum}</span>
              {isRelease && <span className="wizard-cal-day-dot" aria-hidden="true" />}
            </button>
          );
        })}
      </div>
    </div>
  );
}

function formatMovieReleaseStatus(relDate?: string): string {
  if (!relDate) return "Release Date: TBA";
  try {
    const parts = relDate.split("-");
    if (parts.length === 3) {
      const year = parseInt(parts[0], 10);
      const month = parseInt(parts[1], 10) - 1;
      const day = parseInt(parts[2], 10);
      const rd = new Date(year, month, day);
      if (!isNaN(rd.getTime())) {
        const now = new Date();
        const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
        const dateStr = rd.toLocaleDateString("en-IN", {
          day: "numeric",
          month: "short",
          year: "numeric",
        });
        if (rd <= today) {
          return `Released: ${dateStr}`;
        } else {
          return `Releasing: ${dateStr}`;
        }
      }
    }
  } catch (e) { }
  return `Release: ${relDate}`;
}

export default function WatchWizardModal({
  isOpen,
  onClose,
  city,
  initialMovie,
  onSubmitWatch,
  userToken,
  user,
}: WatchWizardModalProps) {
  const [step, setStep] = useState(initialMovie ? 2 : 1);
  const [selectedMovie, setSelectedMovie] = useState<any>(initialMovie || null);
  const [movieQuery, setMovieQuery] = useState("");
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [searching, setSearching] = useState(false);

  const [anyTheatre, setAnyTheatre] = useState(true);
  const [availableTheatres, setAvailableTheatres] = useState<any[]>([]);
  const [loadingTheatres, setLoadingTheatres] = useState(false);
  const [theatreError, setTheatreError] = useState("");
  const [selectedTheatres, setSelectedTheatres] = useState<string[]>([]);
  const [theatreQuery, setTheatreQuery] = useState("");

  const [region, setRegion] = useState<{ code: string; name: string }>({ code: "", name: "" });
  const [searchError, setSearchError] = useState("");

  const [dateFilter, setDateFilter] = useState<string[]>(["all"]);
  const [selectedTimePreset, setSelectedTimePreset] = useState("any");
  const [selectedFormats, setSelectedFormats] = useState<string[]>([]);
  const [maxPrice, setMaxPrice] = useState<number | null>(null);
  const [notifyNewShows, setNotifyNewShows] = useState(true);
  const [notifyBack, setNotifyBack] = useState(true);
  const [watchPlatform, setWatchPlatform] = useState<"both" | "bookmyshow" | "district">("both");
  const [submitting, setSubmitting] = useState(false);

  const [profileWhatsapp, setProfileWhatsapp] = useState("");
  const [inputWhatsapp, setInputWhatsapp] = useState("");
  const [editingWhatsapp, setEditingWhatsapp] = useState(false);

  useEffect(() => {
    if (isOpen && userToken) {
      apiFetch("/api/user/me", {
        headers: { Authorization: `Bearer ${userToken}` },
      })
        .then((data) => {
          const clean10 = toIndianDigits(data?.profile?.whatsapp_number || "");
          if (clean10 && clean10.length === 10) {
            setProfileWhatsapp(clean10);
            setInputWhatsapp(clean10);
          }
        })
        .catch(() => { });
    }
  }, [isOpen, userToken]);

  useEffect(() => {
    if (initialMovie) {
      setSelectedMovie(initialMovie);
      setStep(2);
    }
  }, [initialMovie]);

  useEffect(() => {
    if (!isOpen) {
      setSelectedMovie(initialMovie || null);
      setStep(initialMovie ? 2 : 1);
      setMovieQuery("");
      setSearchResults([]);
      setSearchError("");
      setAnyTheatre(true);
      setAvailableTheatres([]);
      setTheatreError("");
      setSelectedTheatres([]);
      setTheatreQuery("");
      setRegion({ code: "", name: "" });
      setDateFilter(["all"]);
      setSelectedTimePreset("any");
      setSelectedFormats([]);
      setMaxPrice(null);
      setNotifyNewShows(true);
      setNotifyBack(true);
      setWatchPlatform("both");
      setSubmitting(false);
      setEditingWhatsapp(false);
    }
  }, [isOpen, initialMovie]);

  useEffect(() => {
    if (!movieQuery.trim()) {
      setSearchResults([]);
      setSearchError("");
      return;
    }
    const timer = setTimeout(() => {
      setSearching(true);
      apiFetch(`/api/search?q=${encodeURIComponent(movieQuery)}&city=${encodeURIComponent(city)}`)
        .then((data) => {
          setSearchResults(data.results || []);
          setSearchError(data.error || "");
        })
        .catch((err) => {
          setSearchResults([]);
          setSearchError(err?.message || "Search failed");
        })
        .finally(() => setSearching(false));
    }, 250);
    return () => clearTimeout(timer);
  }, [movieQuery, city]);

  useEffect(() => {
    if (step === 2 && selectedMovie) {
      setLoadingTheatres(true);
      setTheatreError("");
      const source = selectedMovie.source || "bookmyshow";
      const params = new URLSearchParams({
        city,
        source,
        movie_id: selectedMovie.id || selectedMovie.eventCode || "",
        movie_slug: selectedMovie.movie_slug || "",
        movie_title: selectedMovie.title || "",
      });
      apiFetch(`/api/theatres?${params.toString()}`)
        .then((data) => {
          setAvailableTheatres(data.theatres || []);
          setTheatreError(data.error || "");
          if (data.region_code) {
            setRegion({ code: data.region_code, name: data.region_name || city });
          }
        })
        .catch((err) => {
          setAvailableTheatres([]);
          setTheatreError(err?.message || "Could not load cinemas");
        })
        .finally(() => setLoadingTheatres(false));
    }
  }, [step, selectedMovie, city]);

  useEffect(() => {
    if (!isOpen) return;
    function handleKey(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const toggleDatePreset = (id: string) => {
    if (id === "all") {
      setDateFilter(["all"]);
      return;
    }
    setDateFilter((prev) => {
      const withoutAll = prev.filter((d) => d !== "all");
      const next = withoutAll.includes(id)
        ? withoutAll.filter((d) => d !== id)
        : [...withoutAll, id];
      return next.length === 0 ? ["all"] : next;
    });
  };

  const toggleExactDate = (date: string) => {
    setDateFilter((prev) => {
      const withoutAll = prev.filter((d) => d !== "all");
      const next = withoutAll.includes(date)
        ? withoutAll.filter((d) => d !== date)
        : [...withoutAll, date];
      return next.length === 0 ? ["all"] : next;
    });
  };

  const toggleTheatreSelection = (tName: string) => {
    setAnyTheatre(false);
    if (selectedTheatres.includes(tName)) {
      const next = selectedTheatres.filter((t) => t !== tName);
      setSelectedTheatres(next);
      if (next.length === 0) setAnyTheatre(true);
    } else {
      setSelectedTheatres([...selectedTheatres, tName]);
    }
  };

  const handleFinish = async () => {
    if (!selectedMovie) return;

    const clean10 = toIndianDigits(profileWhatsapp || inputWhatsapp);

    if (!clean10 || clean10.length !== 10) {
      alert("WhatsApp number is compulsory! Please enter a valid 10-digit Indian mobile number.");
      setStep(4);
      return;
    }

    setSubmitting(true);
    try {
      const preset = TIME_PRESETS.find((p) => p.id === selectedTimePreset);

      let dateFilterArray: string[] = [];
      if (!dateFilter.includes("all")) {
        const expanded = new Set<string>();
        for (const d of dateFilter) {
          if (d === "premier") {
            expanded.add("premier");
            expanded.add("premier_2days");
          } else {
            expanded.add(d);
          }
        }
        dateFilterArray = Array.from(expanded);
      }

      await onSubmitWatch({
        movie_title: selectedMovie.title || selectedMovie.name,
        movie_id: selectedMovie.id || selectedMovie.eventCode,
        movie_slug: selectedMovie.movie_slug || "",
        poster_url: selectedMovie.poster_url || "",
        source: watchPlatform,
        city: city,
        region_code: region.code,
        theatres: anyTheatre ? [] : selectedTheatres,
        date_filter: dateFilterArray,
        after_time: preset?.after || "",
        before_time: preset?.before || "",
        formats: selectedFormats,
        max_price: maxPrice,
        notify_new_shows: notifyNewShows,
        notify_back: notifyBack,
        release_date: selectedMovie.release_date || "",
        whatsapp_number: `+91${clean10}`,
      });
      onClose();
    } catch (err) {
      console.error(err);
    } finally {
      setSubmitting(false);
    }
  };

  const filteredTheatres = availableTheatres.filter((t) =>
    (t.name || "").toLowerCase().includes(theatreQuery.toLowerCase())
  );

  const steps = [
    { s: 1, label: "1. Movie" },
    { s: 2, label: "2. Theatres" },
    { s: 3, label: "3. Preferences" },
    { s: 4, label: "4. Confirm" },
  ];

  const platformLabel =
    watchPlatform === "both"
      ? "BookMyShow + District"
      : watchPlatform === "district"
        ? "District"
        : "BookMyShow";

  return (
    <div role="dialog" aria-modal="true" aria-label="Configure ticket watch" className="modal-backdrop">
      <div className="wizard-panel">
        {/* Header */}
        <div className="wizard-head">
          <div className="wizard-head-brand">
            <div className="wizard-head-icon">
              <Flame className="w-4 h-4" aria-hidden="true" />
            </div>
            <div>
              <h2 className="wizard-head-title">Configure Ticket Watch</h2>
              <p className="wizard-head-sub">
                City: <strong>{city}</strong>
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close wizard"
            className="icon-btn"
          >
            <X className="w-4 h-4" aria-hidden="true" />
          </button>
        </div>

        {/* Stepper */}
        <div className="wizard-steps" role="list" aria-label="Wizard progress">
          {steps.map((item) => (
            <span
              key={item.s}
              role="listitem"
              aria-current={step === item.s ? "step" : undefined}
              className={`wizard-step${step === item.s ? " is-active" : step > item.s ? " is-done" : ""}`}
            >
              {item.label}
            </span>
          ))}
        </div>

        {/* Body */}
        <div className="wizard-body">
          {/* STEP 1: MOVIE */}
          {step === 1 && (
            <>
              <label className="wizard-label" htmlFor="wizard-movie-search">
                Search or select movie
              </label>
              <div className="wizard-field">
                <Search className="wizard-search-icon w-4 h-4" aria-hidden="true" />
                <input
                  id="wizard-movie-search"
                  type="text"
                  value={movieQuery}
                  onChange={(e) => setMovieQuery(e.target.value)}
                  placeholder="Search movie title (e.g. Devara, Kalki, Avengers)..."
                  className="wizard-input wizard-input--icon"
                />
                {searching && (
                  <Loader2 className="wizard-search-spin w-4 h-4 animate-spin" aria-hidden="true" />
                )}
              </div>

              {searchResults.length > 0 && (
                <div className="wizard-results">
                  {searchResults.map((m) => (
                    <button
                      key={m.id || m.eventCode}
                      type="button"
                      onClick={() => setSelectedMovie(m)}
                      aria-pressed={selectedMovie?.id === m.id}
                      className={`wizard-result${selectedMovie?.id === m.id ? " is-selected" : ""}`}
                    >
                      {m.poster_url ? (
                        <img src={m.poster_url} alt="" className="wizard-result-poster" />
                      ) : (
                        <div className="wizard-result-fallback" aria-hidden="true">
                          <Flame className="w-5 h-5" />
                        </div>
                      )}

                      <div className="wizard-result-info">
                        <h4 className="wizard-result-title">{m.title}</h4>
                        <p className="wizard-result-meta">{formatMovieReleaseStatus(m.release_date)}</p>
                      </div>

                      {m.both_sources ? (
                        <span className="badge badge--accent">BMS + District</span>
                      ) : (
                        <span className="badge badge--muted">
                          {m.source === "district" ? "District" : "BookMyShow"}
                        </span>
                      )}
                    </button>
                  ))}
                </div>
              )}

              {selectedMovie && (
                <div className="wizard-picked">
                  {selectedMovie.poster_url ? (
                    <img src={selectedMovie.poster_url} alt="" className="wizard-picked-poster" />
                  ) : (
                    <div className="wizard-picked-fallback" aria-hidden="true">
                      <Flame className="w-6 h-6" />
                    </div>
                  )}
                  <div className="wizard-picked-info">
                    <span className="wizard-picked-eyebrow">Target movie</span>
                    <h4 className="wizard-picked-title">
                      {selectedMovie.title || selectedMovie.name}
                    </h4>
                    <span className="wizard-picked-meta">
                      {formatMovieReleaseStatus(selectedMovie.release_date)}
                    </span>
                    <span className="wizard-picked-platforms">
                      Platforms:{" "}
                      <strong>
                        {selectedMovie.both_sources
                          ? "BookMyShow + District"
                          : selectedMovie.source === "district"
                            ? "District"
                            : "BookMyShow"}
                      </strong>
                    </span>
                  </div>
                  <CheckCircle2
                    className="w-6 h-6 shrink-0"
                    style={{ color: "var(--color-accent)" }}
                    aria-hidden="true"
                  />
                </div>
              )}

              {selectedMovie && (
                <div>
                  <span className="wizard-label wizard-label--tight">
                    Ticketing platforms to watch
                  </span>
                  <div className="wizard-options wizard-options--3">
                    <button
                      type="button"
                      onClick={() => setWatchPlatform("both")}
                      aria-pressed={watchPlatform === "both"}
                      className={`wizard-option${watchPlatform === "both" ? " is-selected" : ""}`}
                    >
                      <span className="wizard-option-title">
                        <Zap className="w-3.5 h-3.5" style={{ color: "var(--color-accent)" }} aria-hidden="true" />
                        Both
                      </span>
                      <span className="wizard-option-sub">BMS + District</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => setWatchPlatform("bookmyshow")}
                      aria-pressed={watchPlatform === "bookmyshow"}
                      className={`wizard-option${watchPlatform === "bookmyshow" ? " is-selected" : ""}`}
                    >
                      <span className="wizard-option-title">BookMyShow</span>
                      <span className="wizard-option-sub">BMS only</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => setWatchPlatform("district")}
                      aria-pressed={watchPlatform === "district"}
                      className={`wizard-option${watchPlatform === "district" ? " is-selected" : ""}`}
                    >
                      <span className="wizard-option-title">District</span>
                      <span className="wizard-option-sub">District only</span>
                    </button>
                  </div>
                </div>
              )}

              {searchError && (
                <div className="wizard-alert" role="status">
                  <AlertTriangle className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />
                  <span>{searchError}</span>
                </div>
              )}
            </>
          )}

          {/* STEP 2: THEATRES */}
          {step === 2 && (
            <>
              <span className="wizard-label">Select cinemas in {city}</span>

              <button
                type="button"
                onClick={() => {
                  setAnyTheatre(true);
                  setSelectedTheatres([]);
                }}
                aria-pressed={anyTheatre}
                className={`wizard-option wizard-option--row${anyTheatre ? " is-selected" : ""}`}
              >
                <span className="flex items-center gap-3 min-w-0">
                  <MapPin
                    className="w-5 h-5 shrink-0"
                    style={{ color: "var(--color-accent)" }}
                    aria-hidden="true"
                  />
                  <span className="min-w-0">
                    <span className="wizard-option-title">Any cinema in {city}</span>
                    <span className="wizard-option-desc">
                      Alert as soon as ANY cinema in {city} opens booking
                    </span>
                  </span>
                </span>
                <span className={`wizard-check${anyTheatre ? " is-on" : ""}`} aria-hidden="true">
                  {anyTheatre && <Check className="w-3 h-3" />}
                </span>
              </button>

              <div className="space-y-2">
                <input
                  type="text"
                  value={theatreQuery}
                  onChange={(e) => setTheatreQuery(e.target.value)}
                  placeholder="Filter cinemas by name (e.g. IMAX, PVR, Cinepolis)"
                  className="wizard-input"
                  aria-label="Filter cinemas by name"
                />

                {loadingTheatres ? (
                  <div className="wizard-loading">
                    <Loader2
                      className="w-4 h-4 animate-spin"
                      style={{ color: "var(--color-accent)" }}
                      aria-hidden="true"
                    />
                    <span>Fetching live cinemas in {city}…</span>
                  </div>
                ) : (
                  <div className="wizard-cinemas">
                    {filteredTheatres.map((t) => {
                      const isSelected = selectedTheatres.includes(t.name);
                      return (
                        <button
                          key={t.id || t.name}
                          type="button"
                          onClick={() => toggleTheatreSelection(t.name)}
                          aria-pressed={isSelected}
                          className={`wizard-cinema${isSelected ? " is-selected" : ""}`}
                        >
                          <span className="wizard-cinema-name">
                            <span className="wizard-cinema-name-track">{t.name}</span>
                          </span>
                          <span className={`wizard-check${isSelected ? " is-on" : ""}`} aria-hidden="true">
                            {isSelected && <Check className="w-3 h-3" />}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                )}

                {theatreError && (
                  <div className="wizard-alert" role="status">
                    <AlertTriangle className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />
                    <span>{theatreError}</span>
                  </div>
                )}
              </div>
            </>
          )}

          {/* STEP 3: DATES, TIMES, FORMATS */}
          {step === 3 && (
            <>
              <div>
                <span className="wizard-label wizard-label--tight">
                  Which show dates do you want alerts for?
                </span>
                <div className="wizard-options">
                  {[
                    {
                      id: "all",
                      label: "Any available date",
                      desc: "Alert whenever tickets open for any date",
                      icon: <Globe className="w-4 h-4" aria-hidden="true" />,
                    },
                    {
                      id: "first_day",
                      label: "Release day (Day 1)",
                      desc: selectedMovie?.release_date
                        ? `Release: ${selectedMovie.release_date}`
                        : "Official opening day shows",
                      icon: <Ticket className="w-4 h-4" aria-hidden="true" />,
                    },
                    {
                      id: "premier",
                      label: "Premiere night (1d before)",
                      desc: "Late preview shows 1 day before release",
                      icon: <Film className="w-4 h-4" aria-hidden="true" />,
                    },
                    {
                      id: "premier_2days",
                      label: "Early previews (2d before)",
                      desc: "Fan preview shows 2 days before release",
                      icon: <Sparkles className="w-4 h-4" aria-hidden="true" />,
                    },
                  ].map((item) => {
                    const isSelected = dateFilter.includes(item.id);
                    return (
                      <button
                        key={item.id}
                        type="button"
                        onClick={() => toggleDatePreset(item.id)}
                        aria-pressed={isSelected}
                        className={`wizard-option wizard-option--left${isSelected ? " is-selected" : ""}`}
                      >
                        <span className="wizard-option-icon">{item.icon}</span>
                        <span className="flex-1 min-w-0">
                          <span className="wizard-option-title" style={{ display: "block" }}>
                            {item.label}
                          </span>
                          <span className="wizard-option-desc" style={{ display: "block" }}>
                            {item.desc}
                          </span>
                        </span>
                        {isSelected && <Check className="wizard-option-check w-4 h-4" aria-hidden="true" />}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div>
                <span className="wizard-label wizard-label--tight">
                  Or pick exact dates (select as many as you like)
                </span>
                <VisualCalendar
                  selectedDates={dateFilter}
                  onToggleDate={toggleExactDate}
                  releaseDate={selectedMovie?.release_date}
                />
              </div>

              <div>
                <span className="wizard-label wizard-label--tight">Showtime window</span>
                <div className="wizard-options wizard-options--3">
                  {TIME_PRESETS.map((t) => {
                    const isSelected = selectedTimePreset === t.id;
                    return (
                      <button
                        key={t.id}
                        type="button"
                        onClick={() => setSelectedTimePreset(t.id)}
                        aria-pressed={isSelected}
                        className={`wizard-option wizard-option--row${isSelected ? " is-selected" : ""}`}
                      >
                        <span className="wizard-option-sub truncate">{t.label}</span>
                        {isSelected && <Check className="wizard-option-check w-3.5 h-3.5 shrink-0" aria-hidden="true" />}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div>
                <span className="wizard-label wizard-label--tight">Screen format (optional)</span>
                <div className="wizard-options wizard-options--3">
                  {["Any Format", "IMAX 3D", "4DX 3D", "3D", "2D", "ScreenX"].map((fmt) => {
                    const isAny = fmt === "Any Format";
                    const isSelected = isAny
                      ? selectedFormats.length === 0
                      : selectedFormats.includes(fmt);
                    return (
                      <button
                        key={fmt}
                        type="button"
                        onClick={() => {
                          if (isAny) {
                            setSelectedFormats([]);
                          } else {
                            if (selectedFormats.includes(fmt)) {
                              setSelectedFormats(selectedFormats.filter((f) => f !== fmt));
                            } else {
                              setSelectedFormats([...selectedFormats, fmt]);
                            }
                          }
                        }}
                        aria-pressed={isSelected}
                        className={`wizard-option wizard-option--row${isSelected ? " is-selected" : ""}`}
                      >
                        <span className="wizard-option-sub">{fmt}</span>
                        {isSelected && <Check className="wizard-option-check w-3.5 h-3.5 shrink-0" aria-hidden="true" />}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div>
                <span className="wizard-label wizard-label--tight">Max ticket budget (optional)</span>
                <div className="wizard-options">
                  {[
                    { label: "Any price", val: null },
                    { label: "Under ₹250", val: 250 },
                    { label: "Under ₹350", val: 350 },
                    { label: "Under ₹500", val: 500 },
                  ].map((opt) => {
                    const isSelected = maxPrice === opt.val;
                    return (
                      <button
                        key={opt.label}
                        type="button"
                        onClick={() => setMaxPrice(opt.val)}
                        aria-pressed={isSelected}
                        className={`wizard-option wizard-option--row${isSelected ? " is-selected" : ""}`}
                      >
                        <span className="wizard-option-sub">{opt.label}</span>
                        {isSelected && <Check className="wizard-option-check w-3.5 h-3.5 shrink-0" aria-hidden="true" />}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div>
                <span className="wizard-label wizard-label--tight">Smart trigger flags</span>
                <div className="wizard-options">
                  <button
                    type="button"
                    onClick={() => setNotifyNewShows(!notifyNewShows)}
                    aria-pressed={notifyNewShows}
                    className={`wizard-option wizard-option--row${notifyNewShows ? " is-selected" : ""}`}
                  >
                    <span className="flex items-center gap-2 min-w-0">
                      <Bell
                        className="w-4 h-4 shrink-0"
                        style={{ color: "var(--color-accent)" }}
                        aria-hidden="true"
                      />
                      <span className="min-w-0">
                        <span className="wizard-option-title" style={{ display: "block" }}>
                          New shows added
                        </span>
                        <span className="wizard-option-sub" style={{ display: "block" }}>
                          Midnight & added screenings
                        </span>
                      </span>
                    </span>
                    <span className={`wizard-check${notifyNewShows ? " is-on" : ""}`} aria-hidden="true">
                      {notifyNewShows && <Check className="w-3 h-3" />}
                    </span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setNotifyBack(!notifyBack)}
                    aria-pressed={notifyBack}
                    className={`wizard-option wizard-option--row${notifyBack ? " is-selected" : ""}`}
                  >
                    <span className="flex items-center gap-2 min-w-0">
                      <RotateCcw
                        className="w-4 h-4 shrink-0"
                        style={{ color: "var(--color-success)" }}
                        aria-hidden="true"
                      />
                      <span className="min-w-0">
                        <span className="wizard-option-title" style={{ display: "block" }}>
                          Re-stock alert
                        </span>
                        <span className="wizard-option-sub" style={{ display: "block" }}>
                          If sold-out tickets return
                        </span>
                      </span>
                    </span>
                    <span
                      className={`wizard-check${notifyBack ? " is-on is-success" : ""}`}
                      aria-hidden="true"
                    >
                      {notifyBack && <Check className="w-3 h-3" />}
                    </span>
                  </button>
                </div>
              </div>
            </>
          )}

          {/* STEP 4: CONFIRMATION & WHATSAPP */}
          {step === 4 && (
            <>
              <div className="wizard-summary">
                {selectedMovie?.poster_url && (
                  <img src={selectedMovie.poster_url} alt="" className="wizard-summary-poster" />
                )}
                <div className="wizard-summary-body">
                  <h3 className="wizard-summary-title">
                    {selectedMovie?.title || "Movie Alert"}
                  </h3>
                  <div className="wizard-summary-rows">
                    <p>
                      Platforms: <strong className="is-accent">{platformLabel}</strong>
                    </p>
                    <p>
                      Theatres:{" "}
                      <strong>
                        {anyTheatre
                          ? "Any cinema in " + city
                          : `${selectedTheatres.length} selected`}
                      </strong>
                    </p>
                    <p>
                      Dates:{" "}
                      <strong>
                        {dateFilter.includes("all") || dateFilter.length === 0
                          ? "Any available date"
                          : dateFilter
                            .map((d) =>
                              d === "first_day"
                                ? "Release day"
                                : d === "premier"
                                  ? "Premiere night"
                                  : d === "premier_2days"
                                    ? "Early previews"
                                    : d
                            )
                            .join(", ")}
                      </strong>
                    </p>
                    <p>
                      Showtime:{" "}
                      <strong>
                        {TIME_PRESETS.find((p) => p.id === selectedTimePreset)?.label}
                      </strong>
                    </p>
                  </div>
                </div>
              </div>

              <div className="wizard-whatsapp">
                <div className="wizard-whatsapp-head">
                  <span className="wizard-whatsapp-title">
                    <MessageSquare
                      className="w-4 h-4"
                      style={{ color: "var(--color-success)" }}
                      aria-hidden="true"
                    />
                    <span>
                      WhatsApp instant alerts <span className="is-required">required</span>
                    </span>
                  </span>
                  {profileWhatsapp && !editingWhatsapp ? (
                    <button
                      type="button"
                      onClick={() => {
                        setInputWhatsapp(profileWhatsapp);
                        setEditingWhatsapp(true);
                      }}
                      className="wizard-whatsapp-change"
                    >
                      Change number
                    </button>
                  ) : (
                    <span className="wizard-whatsapp-count">
                      {(editingWhatsapp ? inputWhatsapp : profileWhatsapp || inputWhatsapp).length}/10 digits
                    </span>
                  )}
                </div>

                {profileWhatsapp && !editingWhatsapp ? (
                  <div className="wizard-phone-ready">
                    <div className="wizard-phone-value">
                      <span>+91</span>
                      <span>
                        {profileWhatsapp.slice(0, 5)} {profileWhatsapp.slice(5)}
                      </span>
                    </div>
                    <span className="wizard-phone-ready-tag">
                      <CheckCircle2 className="w-3 h-3" aria-hidden="true" />
                      Ready
                    </span>
                  </div>
                ) : (
                  <>
                    <div className="wizard-phone">
                      <div className="wizard-phone-prefix">
                        <span>IN</span>
                        <code>+91</code>
                      </div>
                      <input
                        type="tel"
                        inputMode="numeric"
                        maxLength={10}
                        value={inputWhatsapp}
                        onChange={(e) => {
                          const digits = e.target.value.replace(/\D/g, "");
                          setInputWhatsapp(digits.slice(0, 10));
                          if (digits.length === 10) {
                            setProfileWhatsapp(digits);
                            setEditingWhatsapp(false);
                          }
                        }}
                        placeholder="98765 43210"
                        className="wizard-phone-input"
                        aria-label="WhatsApp number, 10 digits"
                        required
                      />
                    </div>
                    <p className="wizard-hint">
                      We scan every few seconds so you grab premiere tickets immediately.
                    </p>
                  </>
                )}
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="wizard-foot">
          {step > 1 ? (
            <button type="button" onClick={() => setStep(step - 1)} className="wizard-btn-back">
              Back
            </button>
          ) : (
            <span />
          )}

          {step < 4 ? (
            <button
              type="button"
              onClick={() => setStep(step + 1)}
              disabled={step === 1 && !selectedMovie}
              className="wizard-btn-next"
            >
              Continue
            </button>
          ) : (
            <button
              type="button"
              onClick={handleFinish}
              disabled={submitting || (!profileWhatsapp && inputWhatsapp.length !== 10)}
              className="wizard-btn-finish"
            >
              {submitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
                  <span>Creating watch…</span>
                </>
              ) : !profileWhatsapp && inputWhatsapp.length !== 10 ? (
                <span>Enter 10-digit WhatsApp number</span>
              ) : (
                <>
                  <Rocket className="w-4 h-4" aria-hidden="true" />
                  <span>Start Hunting</span>
                </>
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
