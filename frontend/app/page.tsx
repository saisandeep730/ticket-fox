"use client";

import React, { useState, useEffect, useCallback, useMemo, useRef } from "react";
import { signInWithPopup, signOut, onIdTokenChanged } from "firebase/auth";
import { auth, googleProvider, firebaseConfigured } from "../lib/firebase";
import { apiFetch } from "../lib/api";
import { groupWatches } from "../lib/watches";
import Navbar from "../components/Navbar";
import MovieCard from "../components/MovieCard";
import WatchCard from "../components/WatchCard";
import AlertHistory from "../components/AlertHistory";
import WatchWizardModal from "../components/WatchWizardModal";
import SettingsModal from "../components/SettingsModal";
import MovieDetailModal from "../components/MovieDetailModal";
import AuthModal from "../components/AuthModal";
import MobileNav from "../components/MobileNav";
import ToastContainer, { ToastMessage } from "../components/Toast";
import { playAlertChime } from "../lib/audio";
import {
  Sparkles,
  Bell,
  Film,
  Loader2,
  LogIn,
  Flame,
  ShieldCheck,
  Zap,
  AlertTriangle,
  Trash2,
  Layers,
  X,
  Search,
  RefreshCw,
  SlidersHorizontal,
} from "lucide-react";

export default function HomePage() {
  const [user, setUser] = useState<any>(null);
  const [userToken, setUserToken] = useState("");
  const [city, setCity] = useState("Hyderabad");
  const [searchQuery, setSearchQuery] = useState("");
  const [movies, setMovies] = useState<any[]>([]);
  const [catalogError, setCatalogError] = useState("");
  const [watches, setWatches] = useState<any[]>([]);
  // A "both platforms" watch is stored as two rows (one per source). Fold them
  // into one card per movie so Active Hunts reads as a single hunt.
  const watchGroups = useMemo(() => groupWatches(watches), [watches]);
  const allWatchIds = useMemo(
    () => watchGroups.reduce<string[]>((acc, g) => acc.concat(g.ids), []),
    [watchGroups]
  );
  const [alerts, setAlerts] = useState<any[]>([]);
  const [loadingMovies, setLoadingMovies] = useState(true);
  const [loadingWatches, setLoadingWatches] = useState(false);
  const [activeTab, setActiveTab] = useState<"discover" | "watches">("discover");

  // The catalog can hold hundreds of titles; mount them in pages so the first
  // paint stays cheap on a phone instead of laying out every card at once.
  const CATALOG_PAGE = 24;
  const [visibleCount, setVisibleCount] = useState(CATALOG_PAGE);

  // Universal Live BookMyShow Search State
  const [bmsSearchResults, setBmsSearchResults] = useState<any[]>([]);
  const [isSearchingBms, setIsSearchingBms] = useState(false);
  const searchDebounceRef = useRef<NodeJS.Timeout | null>(null);

  const handleSearchChange = (val: string) => {
    setSearchQuery(val);
    if (searchDebounceRef.current) {
      clearTimeout(searchDebounceRef.current);
    }
    const q = val.trim();
    if (q.length < 2) {
      setBmsSearchResults([]);
      setIsSearchingBms(false);
      return;
    }
    setIsSearchingBms(true);
    searchDebounceRef.current = setTimeout(async () => {
      try {
        const data = await apiFetch(
          `/api/search?q=${encodeURIComponent(q)}&city=${encodeURIComponent(city)}`
        );
        setBmsSearchResults(data.results || []);
      } catch (err) {
        console.error("BMS search error:", err);
        setBmsSearchResults([]);
      } finally {
        setIsSearchingBms(false);
      }
    }, 250);
  };

  const handleClearSearch = () => {
    setSearchQuery("");
    setBmsSearchResults([]);
    setIsSearchingBms(false);
  };

  // Filter & Sort State
  const [sourceFilter, setSourceFilter] = useState<"all" | "bookmyshow" | "district">("all");
  const [sortBy, setSortBy] = useState<"likes" | "date">("likes");

  // Batch Operations State
  const [isBatchMode, setIsBatchMode] = useState(false);
  const [selectedWatchIds, setSelectedWatchIds] = useState<Set<string>>(new Set());

  // Modals & Toasts
  const [isWizardOpen, setIsWizardOpen] = useState(false);
  const [selectedMovieForWizard, setSelectedMovieForWizard] = useState<any>(null);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);
  const [selectedMovieForDetail, setSelectedMovieForDetail] = useState<any>(null);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [isSettingsModalOpen, setIsSettingsModalOpen] = useState(false);
  const [toasts, setToasts] = useState<ToastMessage[]>([]);
  const toastSeq = useRef(0);

  const showToast = (message: string, type: "success" | "error" | "info" = "info") => {
    toastSeq.current += 1;
    const id = `toast-${toastSeq.current}`;
    setToasts((prev) => [...prev, { id, type, message }]);
  };

  const dismissToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  // Auth with onIdTokenChanged for auto-refresh
  useEffect(() => {
    if (!firebaseConfigured) {
      const stored = typeof window !== "undefined" ? localStorage.getItem("ticketfox_demo_token") : null;
      const token = stored || `demo-${Math.random().toString(36).slice(2)}${Date.now().toString(36)}`;
      if (!stored && typeof window !== "undefined") {
        localStorage.setItem("ticketfox_demo_token", token);
      }
      setUser({
        uid: "demo-user",
        displayName: "Demo User",
        email: "demo@ticketfox.local",
        photoURL: null,
        isDemo: true,
      });
      setUserToken(token);
      return;
    }

    const unsub = onIdTokenChanged(auth as NonNullable<typeof auth>, async (fu) => {
      if (fu) {
        const t = await fu.getIdToken();
        setUser(fu);
        setUserToken(t);
      } else {
        setUser(null);
        setUserToken("");
      }
    });
    return () => unsub();
  }, []);

  const loadCatalog = useCallback(async () => {
    setLoadingMovies(true);
    setCatalogError("");
    try {
      const data = await apiFetch(`/api/catalog?city=${encodeURIComponent(city)}`);
      setMovies(data.movies || []);
      if (data.error) {
        setCatalogError(data.error);
      }
    } catch (e: any) {
      console.error("Failed to load catalog", e);
      setMovies([]);
      setCatalogError(e?.message || "Could not load the movie catalog.");
    } finally {
      setLoadingMovies(false);
    }
  }, [city]);

  const loadWatches = useCallback(async () => {
    if (!userToken) {
      setWatches([]);
      setAlerts([]);
      return;
    }
    setLoadingWatches(true);
    try {
      const data = await apiFetch("/api/watches", {}, userToken);
      setWatches(data.watches || []);
    } catch (e) {
      console.error("Failed to load watches", e);
    } finally {
      setLoadingWatches(false);
    }
  }, [userToken]);

  const loadAlerts = useCallback(async () => {
    if (!userToken) {
      setAlerts([]);
      return;
    }
    try {
      const data = await apiFetch("/api/alerts?limit=15", {}, userToken);
      setAlerts(data.alerts || []);
    } catch (e) {
      console.error("Failed to load alert history", e);
    }
  }, [userToken]);

  useEffect(() => {
    loadCatalog();
  }, [loadCatalog]);

  const prevWatchesRef = useRef<any[]>([]);
  const prevAlertCountRef = useRef<number>(0);

  useEffect(() => {
    loadWatches();
    loadAlerts();
  }, [loadWatches, loadAlerts]);

  // Periodic background polling (every 30s)
  useEffect(() => {
    if (!userToken) return;
    const interval = setInterval(() => {
      loadWatches();
      loadAlerts();
    }, 30000);
    return () => clearInterval(interval);
  }, [userToken, loadWatches, loadAlerts]);

  // Detect availability transition (HUNTING/UNAVAILABLE -> AVAILABLE) and trigger alert chime
  useEffect(() => {
    if (watches.length > 0 && prevWatchesRef.current.length > 0) {
      for (const curr of watches) {
        const prev = prevWatchesRef.current.find((w) => w.id === curr.id);
        if (prev && prev.state !== "AVAILABLE" && curr.state === "AVAILABLE") {
          playAlertChime();
          showToast(
            `🎟️ TICKETS OPEN: "${curr.movie_title}" is now available in ${curr.city}!`,
            "success"
          );
        }
      }
    }
    prevWatchesRef.current = watches;
  }, [watches]);

  // Detect new delivered alerts in history and chime
  useEffect(() => {
    if (alerts.length > 0 && prevAlertCountRef.current > 0 && alerts.length > prevAlertCountRef.current) {
      const newest = alerts[0];
      if (newest && newest.status === "SENT") {
        playAlertChime();
        showToast(`⚡ Alert delivered on ${newest.channel}: ${newest.message?.slice(0, 70)}...`, "info");
      }
    }
    prevAlertCountRef.current = alerts.length;
  }, [alerts]);

  const handleGoogleSignIn = async () => {
    if (!firebaseConfigured) {
      showToast(
        "Running in demo mode — you are signed in as local demo user.",
        "info"
      );
      setIsAuthModalOpen(false);
      return;
    }
    try {
      await signInWithPopup(auth as NonNullable<typeof auth>, googleProvider);
      setIsAuthModalOpen(false);
      showToast("Signed in successfully with Google!", "success");
    } catch (e: any) {
      console.error("Sign-in error", e);
      showToast(e?.message || "Google Sign-In cancelled or failed", "error");
    }
  };

  const handleLogout = async () => {
    if (firebaseConfigured && auth) {
      await signOut(auth);
    } else if (typeof window !== "undefined") {
      localStorage.removeItem("ticketfox_demo_token");
      window.location.reload();
      return;
    }
    setWatches([]);
    setAlerts([]);
    showToast("Signed out", "info");
  };

  // A grouped card can own two rows (BookMyShow + District), so every action
  // fans out over the whole id list and reports one result to the user.
  const handleTogglePause = async (watchIds: string[], currentActive: boolean) => {
    if (!userToken || watchIds.length === 0) return;
    try {
      await Promise.all(
        watchIds.map((watchId) =>
          apiFetch(
            `/api/watches/${watchId}`,
            {
              method: "PATCH",
              body: JSON.stringify({ is_active: !currentActive }),
            },
            userToken
          )
        )
      );
      loadWatches();
      showToast(currentActive ? "Watch alert paused ⏸️" : "Watch alert resumed 🚀", "info");
    } catch (e: any) {
      showToast(e?.message || "Failed to update watch status", "error");
    }
  };

  const handleDeleteWatch = async (watchIds: string[]) => {
    if (!userToken || watchIds.length === 0) return;
    try {
      await Promise.all(
        watchIds.map((watchId) =>
          apiFetch(`/api/watches/${watchId}`, { method: "DELETE" }, userToken)
        )
      );
      loadWatches();
      showToast("Watch alert deleted 🗑️", "info");
    } catch (e: any) {
      showToast(e?.message || "Failed to delete watch", "error");
    }
  };

  const handleToggleSelectWatch = (watchIds: string[]) => {
    setSelectedWatchIds((prev) => {
      const next = new Set(prev);
      const allSelected = watchIds.every((id) => next.has(id));
      for (const id of watchIds) {
        if (allSelected) next.delete(id);
        else next.add(id);
      }
      return next;
    });
  };

  const handleSelectAllWatches = () => {
    if (selectedWatchIds.size === allWatchIds.length) {
      setSelectedWatchIds(new Set());
    } else {
      setSelectedWatchIds(new Set(allWatchIds));
    }
  };

  const handleBatchDelete = async () => {
    if (!userToken || selectedWatchIds.size === 0) return;
    const count = selectedWatchIds.size;
    if (!confirm(`Are you sure you want to delete ${count} selected watch${count > 1 ? "es" : ""}?`)) {
      return;
    }
    try {
      const res = await apiFetch(
        "/api/watches/batch-delete",
        {
          method: "POST",
          body: JSON.stringify({ watch_ids: Array.from(selectedWatchIds) }),
        },
        userToken
      );
      showToast(`Deleted ${res.count ?? count} watches 🗑️`, "success");
      setSelectedWatchIds(new Set());
      setIsBatchMode(false);
      loadWatches();
    } catch (e: any) {
      showToast(e?.message || "Failed to batch delete watches", "error");
    }
  };

  const handleTestDrill = async (watchIds: string[]) => {
    if (!userToken || watchIds.length === 0) return;
    try {
      const results = await Promise.all(
        watchIds.map((watchId) =>
          apiFetch(`/api/watches/${watchId}/test`, { method: "POST" }, userToken)
        )
      );
      playAlertChime();
      const message = results.find((r: any) => r?.message)?.message;
      showToast(message || "Test drill delivered ⚡", "success");
      loadAlerts();
    } catch (e: any) {
      showToast(e?.message || "Test drill request failed", "error");
      loadAlerts();
    }
  };

  const handleCreateWatch = async (watchData: any) => {
    if (!userToken) {
      setIsAuthModalOpen(true);
      return;
    }
    try {
      const meData = await apiFetch("/api/user/me", {}, userToken);
      const profile = meData.profile || {};
      const hasWhatsapp = Boolean(profile.whatsapp_number);

      if (!hasWhatsapp && !watchData.whatsapp_number) {
        showToast("WhatsApp number is compulsory before creating a ticket watch in India!", "error");
        setIsSettingsModalOpen(true);
        return;
      }

      await apiFetch(
        "/api/watches",
        {
          method: "POST",
          body: JSON.stringify(watchData),
        },
        userToken
      );
      playAlertChime();
      loadWatches();
      setActiveTab("watches");
      showToast("Ticket watch created! Real-time engine active ⚡", "success");
    } catch (e: any) {
      showToast(e?.message || "Could not create the watch", "error");
      throw e;
    }
  };

  const openWizardWithMovie = (movie: any) => {
    if (!user) {
      showToast("Please sign in to set up ticket alerts.", "info");
      setIsAuthModalOpen(true);
      return;
    }
    setSelectedMovieForWizard(movie);
    setIsWizardOpen(true);
  };

  const openMovieDetails = (movie: any) => {
    setSelectedMovieForDetail(movie);
    setIsDetailModalOpen(true);
  };

  const handleOpenSettings = () => {
    if (!user) {
      setIsAuthModalOpen(true);
      return;
    }
    setIsSettingsModalOpen(true);
  };

  // Filter movies according to homepage eligibility:
  // - Recently released: released within the last 3 days (rd >= threeDaysAgo and rd <= today)
  // - Upcoming: release date in the future (rd > today)
  // - Released > 3 days ago: excluded
  // - Missing / invalid date: excluded
  const isHomepageEligible = (m: any) => {
    if (!m.release_date) return false;
    const parts = m.release_date.split("-");
    if (parts.length !== 3) return false;
    const rd = new Date(parseInt(parts[0], 10), parseInt(parts[1], 10) - 1, parseInt(parts[2], 10));
    if (isNaN(rd.getTime())) return false;

    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const threeDaysAgo = new Date(today);
    threeDaysAgo.setDate(today.getDate() - 3);

    // If released more than 3 days ago -> excluded
    if (rd.getTime() < threeDaysAgo.getTime()) {
      return false;
    }
    // Eligible: released within last 3 days (0..3) or upcoming in future
    return true;
  };

  const filteredMovies = movies
    .filter((m) => isHomepageEligible(m))
    .sort((a, b) => {
      if (sortBy === "likes") {
        const likesA = a.likes_count || a.likes || 0;
        const likesB = b.likes_count || b.likes || 0;
        return likesB - likesA;
      }
      return 0;
    });

  // A new city or sort order is a new list: start it from the top again.
  useEffect(() => {
    setVisibleCount(CATALOG_PAGE);
  }, [city, sortBy, sourceFilter]);

  return (
    <div className="app-shell">
      {/* Navigation */}
      <Navbar
        currentCity={city}
        onCityChange={setCity}
        user={user}
        onOpenAuth={() => setIsAuthModalOpen(true)}
        onOpenSettings={handleOpenSettings}
        onLogout={handleLogout}
        activeWatchCount={watchGroups.filter((g) => g.isActive).length}
        onOpenWatches={() => setActiveTab("watches")}
      />

      {/* Hero · the promise, then the action */}
      <section className="hero">
        <div className="container hero-inner">
          <div className="hero-text">
            <h1>Tickets, the second they open.</h1>
            <p className="lead">
              We poll BookMyShow and District every few seconds, then alert you.
            </p>

            <div className="hero-actions">
              <button
                onClick={() => openWizardWithMovie(null)}
                className="btn-primary"
              >
                <Sparkles className="w-4 h-4" aria-hidden="true" />
                <span>Create ticket watch</span>
              </button>

              <button
                onClick={() => {
                  setActiveTab("discover");
                  setTimeout(() => {
                    document.getElementById("catalog-section")?.scrollIntoView({ behavior: "smooth" });
                  }, 50);
                }}
                className="btn-quiet"
              >
                <Film className="w-4 h-4" aria-hidden="true" />
                <span>Browse the catalog</span>
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* Main Content Area */}
      <main className="flex-1 w-full pb-8 md:pb-12">
        {/* The catalog is the section's object: a filter rail beside the grid */}
        {activeTab === "discover" && (
          <section id="catalog-section" className="catalog">
            <div className="container catalog-grid">
              <aside className="catalog-rail" aria-label="Filter the catalog">
                <div className="catalog-rail-head">
                  <h2 className="catalog-rail-title">What is showing</h2>
                  <p className="catalog-rail-city">{city}</p>
                </div>

                <div className="catalog-filters" role="group" aria-label="Catalog view">
                  <button
                    onClick={() => setActiveTab("discover")}
                    aria-pressed={true}
                    className="catalog-filter is-active"
                  >
                    <Film className="catalog-filter-icon" aria-hidden="true" />
                    <span className="catalog-filter-label">Now showing</span>
                    <span className="catalog-filter-count">{filteredMovies.length}</span>
                  </button>

                  <button
                    onClick={() => setActiveTab("watches")}
                    aria-pressed={false}
                    className="catalog-filter"
                  >
                    <Bell className="catalog-filter-icon" aria-hidden="true" />
                    <span className="catalog-filter-label">My active hunts</span>
                    <span className="catalog-filter-count">{watchGroups.length}</span>
                  </button>
                </div>

                <div className="catalog-search">
                  <label className="catalog-label" htmlFor="catalog-search">
                    Search
                  </label>
                  <div className="catalog-search-field">
                    <Search className="catalog-search-icon" aria-hidden="true" />
                    <input
                      id="catalog-search"
                      type="text"
                      value={searchQuery}
                      onChange={(e) => handleSearchChange(e.target.value)}
                      placeholder="Any film, any theatre"
                      autoComplete="off"
                      className="field catalog-search-input"
                    />
                    {isSearchingBms ? (
                      <Loader2 className="catalog-search-spin" aria-hidden="true" />
                    ) : searchQuery ? (
                      <button
                        onClick={handleClearSearch}
                        className="catalog-search-clear"
                        aria-label="Clear search"
                      >
                        <X className="w-4 h-4" aria-hidden="true" />
                      </button>
                    ) : null}
                  </div>
                </div>

                <div className="catalog-sort">
                  <label className="catalog-label" htmlFor="catalog-sort">
                    Sort
                  </label>
                  <select
                    id="catalog-sort"
                    value={sortBy}
                    onChange={(e) => setSortBy(e.target.value as any)}
                    className="field"
                  >
                    <option value="likes">Most popular</option>
                    <option value="date">Release date</option>
                  </select>
                </div>

                <button
                  onClick={() => loadCatalog()}
                  disabled={loadingMovies}
                  className="btn-quiet catalog-refresh"
                >
                  <RefreshCw
                    className={`w-4 h-4 ${loadingMovies ? "animate-spin" : ""}`}
                    aria-hidden="true"
                  />
                  <span>Refresh</span>
                </button>
              </aside>

              <div className="catalog-body">
                {catalogError && !loadingMovies && (
                  <div className="catalog-alert" role="status">
                    <AlertTriangle className="w-4 h-4 shrink-0" aria-hidden="true" />
                    <span>{catalogError}</span>
                    <button onClick={() => loadCatalog()} className="catalog-alert-retry">
                      Retry
                    </button>
                  </div>
                )}

                {searchQuery.trim().length >= 2 ? (
                  <>
                    <div className="catalog-body-head">
                      <p className="catalog-body-title">
                        Results for &ldquo;{searchQuery}&rdquo;
                      </p>
                      <button onClick={handleClearSearch} className="catalog-body-link">
                        Back to what is showing
                      </button>
                    </div>

                    {isSearchingBms ? (
                      <div className="catalog-grid-cards">
                        {[...Array(5)].map((_, i) => (
                          <div key={i} className="catalog-skeleton" aria-hidden="true" />
                        ))}
                      </div>
                    ) : bmsSearchResults.length > 0 ? (
                      <div className="catalog-grid-cards">
                        {bmsSearchResults.map((movie, idx) => (
                          <MovieCard
                            key={movie.id || movie.eventCode || idx}
                            movie={movie}
                            onSelectMovie={openWizardWithMovie}
                            onViewDetails={openMovieDetails}
                            eager={idx < 4}
                          />
                        ))}
                      </div>
                    ) : (
                      <div className="catalog-empty">
                        <Film className="catalog-empty-icon" aria-hidden="true" />
                        <h3 className="catalog-empty-title">
                          Nothing matches &ldquo;{searchQuery}&rdquo;
                        </h3>
                        <p className="catalog-empty-line">
                          Check the spelling, or watch this exact title and we will tell you the
                          moment a showtime appears.
                        </p>
                        <button
                          onClick={() => openWizardWithMovie({ title: searchQuery })}
                          className="btn-primary"
                        >
                          <Sparkles className="w-4 h-4" aria-hidden="true" />
                          <span>Watch &ldquo;{searchQuery}&rdquo;</span>
                        </button>
                      </div>
                    )}
                  </>
                ) : loadingMovies ? (
                  <div className="catalog-grid-cards">
                    {[...Array(10)].map((_, i) => (
                      <div key={i} className="catalog-skeleton" aria-hidden="true" />
                    ))}
                  </div>
                ) : filteredMovies.length > 0 ? (
                  <>
                    <div className="catalog-grid-cards">
                      {filteredMovies.slice(0, visibleCount).map((movie, idx) => (
                        <MovieCard
                          key={movie.id || movie.eventCode || idx}
                          movie={movie}
                          onSelectMovie={openWizardWithMovie}
                          onViewDetails={openMovieDetails}
                          eager={idx < 4}
                        />
                      ))}
                    </div>
                    {visibleCount < filteredMovies.length && (
                      <div className="catalog-more">
                        <button
                          type="button"
                          onClick={() => setVisibleCount((n) => n + CATALOG_PAGE)}
                          className="btn-quiet catalog-more-btn"
                        >
                          <span>
                            Show {Math.min(CATALOG_PAGE, filteredMovies.length - visibleCount)} more
                          </span>
                          <span className="catalog-more-count" aria-hidden="true">
                            {visibleCount} of {filteredMovies.length}
                          </span>
                        </button>
                      </div>
                    )}
                  </>
                ) : (
                  <div className="catalog-empty">
                    <Film className="catalog-empty-icon" aria-hidden="true" />
                    <h3 className="catalog-empty-title">Nothing is showing in {city} yet</h3>
                    <p className="catalog-empty-line">
                      Search any film above, or pick another city in the bar at the top. A watch
                      keeps running whether or not the film is listed today.
                    </p>
                  </div>
                )}
              </div>
            </div>
          </section>
        )}

        {/* The hunts tab: the same rail, the watches as the object */}
        {activeTab === "watches" && (
          <section className="catalog">
            <div className="container catalog-grid">
              <aside className="catalog-rail" aria-label="Filter the catalog">
                <div className="catalog-rail-head">
                  <h2 className="catalog-rail-title">Your hunts</h2>
                  <p className="catalog-rail-city">{city}</p>
                </div>

                <div className="catalog-filters" role="group" aria-label="Catalog view">
                  <button
                    onClick={() => setActiveTab("discover")}
                    aria-pressed={false}
                    className="catalog-filter"
                  >
                    <Film className="catalog-filter-icon" aria-hidden="true" />
                    <span className="catalog-filter-label">Now showing</span>
                    <span className="catalog-filter-count">{filteredMovies.length}</span>
                  </button>

                  <button
                    onClick={() => setActiveTab("watches")}
                    aria-pressed={true}
                    className="catalog-filter is-active"
                  >
                    <Bell className="catalog-filter-icon" aria-hidden="true" />
                    <span className="catalog-filter-label">My active hunts</span>
                    <span className="catalog-filter-count">{watchGroups.length}</span>
                  </button>
                </div>

                <button
                  onClick={() => {
                    if (!user) {
                      setIsAuthModalOpen(true);
                      return;
                    }
                    setSelectedMovieForWizard(null);
                    setIsWizardOpen(true);
                  }}
                  className="btn-primary catalog-refresh"
                >
                  <Sparkles className="w-4 h-4" aria-hidden="true" />
                  <span>New watch</span>
                </button>
              </aside>

              <div className="catalog-body">
                {!user ? (
                  <div className="catalog-empty">
                    <ShieldCheck className="catalog-empty-icon" aria-hidden="true" />
                    <h3 className="catalog-empty-title">Sign in to see your hunts</h3>
                    <p className="catalog-empty-line">
                      Your watches run in the background around the clock. Sign in with Google to
                      see what is armed and what has already fired.
                    </p>
                    <button
                      onClick={() => setIsAuthModalOpen(true)}
                      className="btn-primary"
                    >
                      <LogIn className="w-4 h-4" aria-hidden="true" />
                      <span>Sign in</span>
                    </button>
                  </div>
                ) : loadingWatches ? (
                  <div className="catalog-loading">
                    <Loader2 className="w-6 h-6 animate-spin" aria-hidden="true" />
                    <p>Loading your hunts</p>
                  </div>
                ) : watchGroups.length > 0 ? (
                  <>
                    <div className="hunts-bar">
                      <p className="hunts-counts">
                        <span>
                          {watchGroups.length} watch{watchGroups.length > 1 ? "es" : ""}
                        </span>
                        <span className="hunts-count is-live">
                          {watchGroups.filter((g) => g.isActive).length} active
                        </span>
                        {watchGroups.some((g) => g.isExpired) && (
                          <span className="hunts-count is-done">
                            {watchGroups.filter((g) => g.isExpired).length} expired
                          </span>
                        )}
                      </p>

                      <div className="hunts-actions">
                        {isBatchMode ? (
                          <>
                            <button onClick={handleSelectAllWatches} className="btn-quiet hunts-btn">
                              {selectedWatchIds.size === allWatchIds.length ? "Deselect all" : "Select all"}
                            </button>
                            <button
                              onClick={handleBatchDelete}
                              disabled={selectedWatchIds.size === 0}
                              className="btn-quiet hunts-btn is-danger"
                            >
                              <Trash2 className="w-4 h-4" aria-hidden="true" />
                              <span>Delete ({selectedWatchIds.size})</span>
                            </button>
                            <button
                              onClick={() => {
                                setIsBatchMode(false);
                                setSelectedWatchIds(new Set());
                              }}
                              className="btn-quiet hunts-btn"
                            >
                              Cancel
                            </button>
                          </>
                        ) : (
                          <button onClick={() => setIsBatchMode(true)} className="btn-quiet hunts-btn">
                            <Layers className="w-4 h-4" aria-hidden="true" />
                            <span>Bulk actions</span>
                          </button>
                        )}
                      </div>
                    </div>

                    <div className="hunts-list">
                      {watchGroups.map((group) => (
                        <WatchCard
                          key={group.key}
                          group={group}
                          onTogglePause={handleTogglePause}
                          onDelete={handleDeleteWatch}
                          onTestDrill={handleTestDrill}
                          isBatchMode={isBatchMode}
                          isSelected={group.ids.every((id) => selectedWatchIds.has(id))}
                          onToggleSelect={handleToggleSelectWatch}
                        />
                      ))}
                    </div>
                  </>
                ) : (
                  <div className="catalog-empty">
                    <Bell className="catalog-empty-icon" aria-hidden="true" />
                    <h3 className="catalog-empty-title">No watches yet</h3>
                    <p className="catalog-empty-line">
                      Pick a film and a city, and we will tell you the second a showtime opens at
                      any theatre running it.
                    </p>
                    <button
                      onClick={() => {
                        setSelectedMovieForWizard(null);
                        setIsWizardOpen(true);
                      }}
                      className="btn-primary"
                    >
                      <Sparkles className="w-4 h-4" aria-hidden="true" />
                      <span>Create your first watch</span>
                    </button>
                  </div>
                )}

                {/* Delivery history: every alert dispatched */}
                {user && <AlertHistory alerts={alerts} onRefresh={loadAlerts} />}
              </div>
            </div>
          </section>
        )}
      </main>

      {/* Auth Modal */}
      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
        onGoogleSignIn={handleGoogleSignIn}
        onShowToast={showToast}
      />

      {/* Settings Modal */}
      <SettingsModal
        isOpen={isSettingsModalOpen}
        onClose={() => setIsSettingsModalOpen(false)}
        userToken={userToken}
        onShowToast={showToast}
      />

      {/* Watch Setup Wizard Modal */}
      <WatchWizardModal
        isOpen={isWizardOpen}
        onClose={() => setIsWizardOpen(false)}
        city={city}
        initialMovie={selectedMovieForWizard}
        onSubmitWatch={handleCreateWatch}
        userToken={userToken}
        user={user}
      />

      {/* Movie Details Modal */}
      <MovieDetailModal
        isOpen={isDetailModalOpen}
        onClose={() => setIsDetailModalOpen(false)}
        movie={selectedMovieForDetail}
        city={city}
        onStartWatch={(m) => openWizardWithMovie(m)}
      />

      {/* Sticky Mobile Bottom Navigation */}
      <MobileNav
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        watchCount={watchGroups.length}
        onOpenSettings={() => {
          if (!user) {
            setIsAuthModalOpen(true);
          } else {
            setIsSettingsModalOpen(true);
          }
        }}
        onOpenWizard={() => {
          if (!user) {
            setIsAuthModalOpen(true);
            showToast("Please sign in to create a ticket watch.", "info");
          } else {
            setSelectedMovieForWizard(null);
            setIsWizardOpen(true);
          }
        }}
      />

      {/* Global Toast Container */}
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
    </div>
  );
}
