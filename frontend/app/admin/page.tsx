"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  Shield,
  Key,
  Lock,
  Unlock,
  Activity,
  RefreshCw,
  Send,
  Users,
  AlertTriangle,
  AlertCircle,
  CheckCircle2,
  ArrowLeft,
  Eye,
  EyeOff,
  Play,
  Pencil,
  X,
} from "lucide-react";
import TicketFoxLogo from "../../components/TicketFoxLogo";
import { apiFetch } from "../../lib/api";
import { ADMIN_EMAIL, isAdminUser, MAIN_SITE_URL } from "../../lib/admin";
import { auth } from "../../lib/firebase";
import { onIdTokenChanged, User } from "firebase/auth";

type TabId = "overview" | "failing_keys" | "broadcasts" | "users_watches";

export default function AdminPage() {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [adminKey, setAdminKey] = useState<string>("");
  const [keyInput, setKeyInput] = useState<string>("");
  const [showKey, setShowKey] = useState<boolean>(false);
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [authError, setAuthError] = useState<string>("");
  const [activeTab, setActiveTab] = useState<TabId>("overview");

  // Subscribe to auth state to identify administrator
  useEffect(() => {
    if (!auth) return;
    const unsub = onIdTokenChanged(auth, (fu: User | null) => {
      setCurrentUser(fu);
    });
    return () => unsub();
  }, []);

  const isDesignatedAdmin = !currentUser || isAdminUser(currentUser);

  // Dashboard Data State
  const [stats, setStats] = useState<any>(null);
  const [pollKeys, setPollKeys] = useState<any[]>([]);
  const [broadcasts, setBroadcasts] = useState<any[]>([]);
  const [usersList, setUsersList] = useState<any[]>([]);
  const [watchesList, setWatchesList] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [refreshing, setRefreshing] = useState<boolean>(false);

  // Manual Trigger State
  const [triggeringWorker, setTriggeringWorker] = useState<boolean>(false);
  const [workerResult, setWorkerResult] = useState<any>(null);

  // Broadcast Composer State
  const [bTitle, setBTitle] = useState("");
  const [bMessage, setBMessage] = useState("");
  const [bCtaText, setBCtaText] = useState("Book Tickets");
  const [bCtaUrl, setBCtaUrl] = useState("");
  const [bChannels, setBChannels] = useState<string[]>(["email", "whatsapp"]);
  const [sendingBroadcast, setSendingBroadcast] = useState(false);
  const [broadcastNotice, setBroadcastNotice] = useState<string | null>(null);
  const [broadcastDetails, setBroadcastDetails] = useState<any[] | null>(null);
  const [previewChannel, setPreviewChannel] = useState<"whatsapp" | "email">("whatsapp");

  // User Notification Channel Edit State
  const [editingUser, setEditingUser] = useState<any>(null);
  const [editWhatsapp, setEditWhatsapp] = useState<string>("");
  const [editEmail, setEditEmail] = useState<string>("");
  const [savingUser, setSavingUser] = useState<boolean>(false);

  const adminHeaders = (key: string) => ({
    "X-Admin-Key": key,
  });

  const loadExtraData = useCallback(async (key: string) => {
    try {
      const [keysRes, bRes, uRes, wRes] = await Promise.all([
        apiFetch("/api/admin/poll-keys", { headers: adminHeaders(key) }).catch(() => ({ poll_keys: [] })),
        apiFetch("/api/admin/broadcasts", { headers: adminHeaders(key) }).catch(() => ({ campaigns: [] })),
        apiFetch("/api/admin/users?limit=100", { headers: adminHeaders(key) }).catch(() => ({ users: [] })),
        apiFetch("/api/admin/watches?limit=100", { headers: adminHeaders(key) }).catch(() => ({ watches: [] })),
      ]);
      setPollKeys(keysRes.poll_keys || []);
      setBroadcasts(bRes.campaigns || []);
      setUsersList(uRes.users || []);
      setWatchesList(wRes.watches || []);
    } catch (e) {
      console.error("Failed to load secondary admin data", e);
    }
  }, []);

  const verifyAndLoad = useCallback(async (keyToTest: string) => {
    setLoading(true);
    setAuthError("");
    try {
      const data = await apiFetch("/api/admin/stats", {
        headers: adminHeaders(keyToTest),
      });
      setStats(data);
      setIsAuthenticated(true);
      setAdminKey(keyToTest);
      localStorage.setItem("ticketfox_admin_key", keyToTest);
      loadExtraData(keyToTest);
    } catch (err: any) {
      setIsAuthenticated(false);
      setAuthError(err?.message || "Invalid Admin Key. Access Denied.");
    } finally {
      setLoading(false);
    }
  }, [loadExtraData]);

  useEffect(() => {
    const saved = localStorage.getItem("ticketfox_admin_key");
    if (saved) {
      setAdminKey(saved);
      setKeyInput(saved);
      verifyAndLoad(saved);
    }
  }, [verifyAndLoad]);

  const handleRefreshAll = async () => {
    if (!adminKey) return;
    setRefreshing(true);
    try {
      const data = await apiFetch("/api/admin/stats", {
        headers: adminHeaders(adminKey),
      });
      setStats(data);
      await loadExtraData(adminKey);
    } catch (err: any) {
      setAuthError(err?.message || "Failed to refresh");
    } finally {
      setRefreshing(false);
    }
  };

  const handleAuthorize = (e: React.FormEvent) => {
    e.preventDefault();
    if (!keyInput.trim()) return;
    verifyAndLoad(keyInput.trim());
  };

  const handleLogout = () => {
    localStorage.removeItem("ticketfox_admin_key");
    setAdminKey("");
    setKeyInput("");
    setIsAuthenticated(false);
    setStats(null);
  };

  const handleTriggerWorkerCycle = async () => {
    if (!adminKey) return;
    setTriggeringWorker(true);
    setWorkerResult(null);
    try {
      const res = await apiFetch("/api/worker/cycle", {
        method: "POST",
        headers: adminHeaders(adminKey),
      });
      setWorkerResult(res);
      handleRefreshAll();
    } catch (e: any) {
      setWorkerResult({ error: e?.message || "Failed to trigger cycle" });
    } finally {
      setTriggeringWorker(false);
    }
  };

  const handleSendBroadcast = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!adminKey || !bTitle || !bMessage) return;
    if (bChannels.length === 0) {
      alert("Please select at least one delivery channel (Email or WhatsApp).");
      return;
    }
    setSendingBroadcast(true);
    setBroadcastNotice(null);
    setBroadcastDetails(null);
    try {
      const res = await apiFetch("/api/admin/broadcast", {
        method: "POST",
        headers: adminHeaders(adminKey),
        body: JSON.stringify({
          title: bTitle,
          message: bMessage,
          cta_text: bCtaText,
          cta_url: bCtaUrl,
          channels: bChannels,
        }),
      });
      setBroadcastNotice(res.message || `Delivered to ${res.sent_count} user(s).`);
      if (res.details) {
        setBroadcastDetails(res.details);
      }
      setBTitle("");
      setBMessage("");
      setBCtaUrl("");
      handleRefreshAll();
    } catch (e: any) {
      setBroadcastNotice(`Broadcast failed: ${e?.message || "Error"}`);
    } finally {
      setSendingBroadcast(false);
    }
  };

  const handleSaveUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingUser || !adminKey) return;
    setSavingUser(true);
    try {
      await apiFetch(`/api/admin/users/${editingUser.uid || editingUser.id}`, {
        method: "PATCH",
        headers: adminHeaders(adminKey),
        body: JSON.stringify({
          whatsapp_number: editWhatsapp.trim(),
          email: editEmail.trim(),
        }),
      });
      setEditingUser(null);
      await loadExtraData(adminKey);
    } catch (err: any) {
      alert(`Failed to update user: ${err?.message || "Error"}`);
    } finally {
      setSavingUser(false);
    }
  };

  const toggleChannel = (ch: string) => {
    setBChannels((prev) =>
      prev.includes(ch) ? prev.filter((c) => c !== ch) : [...prev, ch]
    );
  };

  const failingCount = pollKeys.filter(
    (k) => (k.fail_count ?? k.consecutive_failures ?? 0) > 0
  ).length;

  const tabs: { id: TabId; label: string; icon: typeof Activity; count?: number }[] = [
    { id: "overview", label: "Overview", icon: Activity },
    { id: "failing_keys", label: "Poll keys", icon: AlertTriangle, count: failingCount },
    { id: "broadcasts", label: "Broadcasts", icon: Send },
    { id: "users_watches", label: "Users and watches", icon: Users, count: usersList.length },
  ];

  const whatsappReach = usersList.filter((u) => Boolean(u.whatsapp_number || u.phone)).length;
  const emailReach = usersList.filter((u) => Boolean(u.email)).length;

  return (
    <div className="console">
      <header className="console-bar">
        <div className="container console-bar-inner">
          <div className="console-bar-brand">
            <TicketFoxLogo size="sm" />
            <span className="console-bar-rule" aria-hidden="true" />
            <span className="console-bar-title">Control plane</span>
          </div>

          <div className="console-bar-actions">
            <a href={MAIN_SITE_URL} className="console-btn console-btn-quiet">
              <ArrowLeft className="console-icon" aria-hidden="true" />
              <span>Return to app</span>
            </a>

            {isAuthenticated && (
              <>
                <button
                  id="admin-refresh-button"
                  onClick={handleRefreshAll}
                  disabled={refreshing}
                  className="console-btn console-btn-quiet"
                >
                  <RefreshCw
                    className={`console-icon ${refreshing ? "is-spinning" : ""}`}
                    aria-hidden="true"
                  />
                  <span>Refresh</span>
                </button>
                <button onClick={handleLogout} className="console-btn console-btn-danger">
                  <Lock className="console-icon" aria-hidden="true" />
                  <span>Lock</span>
                </button>
              </>
            )}
          </div>
        </div>
      </header>

      <main className="container console-body">
        {currentUser && !isDesignatedAdmin ? (
          <div className="console-gate">
            <span className="console-gate-mark" aria-hidden="true">
              <Shield className="console-icon-lg" />
            </span>
            <h1 className="console-gate-title">Access denied</h1>
            <p className="console-gate-line">
              The control plane is restricted to the TicketFox administrator account, {ADMIN_EMAIL}.
            </p>
            <a href={MAIN_SITE_URL} className="console-btn console-btn-accent">
              <ArrowLeft className="console-icon" aria-hidden="true" />
              <span>Return to catalog</span>
            </a>
          </div>
        ) : !isAuthenticated ? (
          <div className="console-gate">
            <span className="console-gate-mark" aria-hidden="true">
              <Key className="console-icon-lg" />
            </span>
            <h1 className="console-gate-title">Admin authentication</h1>
            <p className="console-gate-line">
              Enter the admin secret key to reach the worker engine, the poll key monitor, and
              broadcasts.
            </p>

            <form onSubmit={handleAuthorize} className="console-gate-form">
              <div className="console-field">
                <label className="console-label" htmlFor="admin-secret-key-input">
                  Secret key
                </label>
                <div className="console-input-wrap">
                  <input
                    id="admin-secret-key-input"
                    type={showKey ? "text" : "password"}
                    value={keyInput}
                    onChange={(e) => setKeyInput(e.target.value)}
                    placeholder="Enter secret key"
                    className="console-input"
                  />
                  <button
                    type="button"
                    onClick={() => setShowKey(!showKey)}
                    className="console-input-toggle"
                    aria-label={showKey ? "Hide secret key" : "Show secret key"}
                  >
                    {showKey ? (
                      <EyeOff className="console-icon" aria-hidden="true" />
                    ) : (
                      <Eye className="console-icon" aria-hidden="true" />
                    )}
                  </button>
                </div>
              </div>

              {authError && (
                <p className="console-note is-error">
                  <AlertCircle className="console-icon" aria-hidden="true" />
                  <span>{authError}</span>
                </p>
              )}

              <button
                id="admin-authorize-submit"
                type="submit"
                disabled={loading}
                className="console-btn console-btn-accent console-btn-block"
              >
                {loading ? (
                  <RefreshCw className="console-icon is-spinning" aria-hidden="true" />
                ) : (
                  <Unlock className="console-icon" aria-hidden="true" />
                )}
                <span>Open control plane</span>
              </button>
            </form>
          </div>
        ) : (
          <div className="console-workspace">
            <nav className="console-rail" aria-label="Control plane sections">
              {tabs.map((tab) => {
                const Icon = tab.icon;
                const isActive = activeTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    aria-current={isActive ? "page" : undefined}
                    className={`console-tab ${isActive ? "is-active" : ""}`}
                  >
                    <Icon className="console-icon" aria-hidden="true" />
                    <span className="console-tab-label">{tab.label}</span>
                    {typeof tab.count === "number" && tab.count > 0 && (
                      <span className="console-tab-count">{tab.count}</span>
                    )}
                  </button>
                );
              })}
            </nav>

            <div className="console-pane">
              {/* OVERVIEW */}
              {activeTab === "overview" && stats && (
                <>
                  <div className="console-metrics">
                    <div className="metric">
                      <span className="metric-label">Total users</span>
                      <span className="metric-value">{stats.total_users ?? 0}</span>
                      <span className="metric-note">Registered on TicketFox</span>
                    </div>

                    <div className="metric">
                      <span className="metric-label">Active watches</span>
                      <span className="metric-value">
                        {stats.active_watches ?? 0}
                        <span className="metric-of">of {stats.total_watches ?? 0}</span>
                      </span>
                      <span className="metric-note">
                        {stats.expired_watches ?? 0} expired date filters
                      </span>
                    </div>

                    <div className="metric">
                      <span className="metric-label">Alerts delivered</span>
                      <span className="metric-value">
                        {stats.total_alerts_sent ?? stats.alerts_sent ?? 0}
                      </span>
                      <span className="metric-note">Over WhatsApp and email</span>
                    </div>

                    <div className="metric">
                      <span className="metric-label">Worker cadence</span>
                      <span className="metric-value">
                        {stats.worker?.surge_active ? "60s" : "180s"}
                      </span>
                      <span className="metric-note">
                        {stats.worker?.surge_active ? "Surge on an active drop" : "Normal interval"}
                      </span>
                    </div>
                  </div>

                  <section className="console-panel" aria-labelledby="engine-title">
                    <div className="console-panel-head">
                      <div>
                        <h2 className="console-panel-title" id="engine-title">
                          Polling engine
                        </h2>
                        <p className="console-panel-line">
                          One worker scans BookMyShow and District for every active watch.
                        </p>
                      </div>

                      <button
                        id="admin-manual-sweep-button"
                        onClick={handleTriggerWorkerCycle}
                        disabled={triggeringWorker}
                        className="console-btn console-btn-accent"
                      >
                        {triggeringWorker ? (
                          <>
                            <RefreshCw className="console-icon is-spinning" aria-hidden="true" />
                            <span>Polling</span>
                          </>
                        ) : (
                          <>
                            <Play className="console-icon" aria-hidden="true" />
                            <span>Run sweep</span>
                          </>
                        )}
                      </button>
                    </div>

                    {workerResult && (
                      <p className={`console-note ${workerResult.error ? "is-error" : "is-ok"}`}>
                        {workerResult.error ? (
                          <AlertCircle className="console-icon" aria-hidden="true" />
                        ) : (
                          <CheckCircle2 className="console-icon" aria-hidden="true" />
                        )}
                        <span>
                          {workerResult.error
                            ? `Sweep error: ${workerResult.error}`
                            : `Cycle finished. Polled ${workerResult.keys_polled} key(s) in ${workerResult.duration_seconds}s.`}
                        </span>
                        <span className="console-note-time">
                          {new Date().toLocaleTimeString()}
                        </span>
                      </p>
                    )}

                    <dl className="console-facts">
                      <div className="console-fact">
                        <dt>Last cycle duration</dt>
                        <dd>
                          {stats.worker?.last_cycle_duration_seconds != null
                            ? `${stats.worker.last_cycle_duration_seconds} seconds`
                            : "Idle"}
                        </dd>
                      </div>
                      <div className="console-fact">
                        <dt>Keys handled last sweep</dt>
                        <dd>{stats.worker?.last_cycle_keys_count ?? 0} unique targets</dd>
                      </div>
                      <div className="console-fact">
                        <dt>Delivery transports</dt>
                        <dd>
                          <span className={stats.channels?.email ? "is-live" : "is-dark"}>
                            Email (Resend)
                          </span>
                          <span className={stats.channels?.whatsapp ? "is-live" : "is-dark"}>
                            WhatsApp (OpenWA)
                          </span>
                        </dd>
                      </div>
                    </dl>
                  </section>
                </>
              )}

              {/* FAILING KEYS */}
              {activeTab === "failing_keys" && (
                <section className="console-panel" aria-labelledby="keys-title">
                  <div className="console-panel-head">
                    <div>
                      <h2 className="console-panel-title" id="keys-title">
                        Poll key health
                      </h2>
                      <p className="console-panel-line">
                        Consecutive scraping failures per source key, and the recovery when it comes.
                      </p>
                    </div>
                    <span className="console-count">
                      {pollKeys.length} monitored
                    </span>
                  </div>

                  {pollKeys.length === 0 ? (
                    <div className="console-empty">
                      <CheckCircle2 className="console-icon-lg" aria-hidden="true" />
                      <p className="console-empty-title">Every key is resolving</p>
                      <p className="console-empty-line">
                        No poll key has hit a persistent failure. BookMyShow and District requests
                        are coming back clean.
                      </p>
                    </div>
                  ) : (
                    <div className="console-table-wrap">
                      <table className="console-table">
                        <thead>
                          <tr>
                            <th scope="col">Target poll key</th>
                            <th scope="col">Failures</th>
                            <th scope="col">Status</th>
                            <th scope="col">Last error</th>
                            <th scope="col">Last success</th>
                          </tr>
                        </thead>
                        <tbody>
                          {pollKeys.map((pk) => {
                            const keyName = pk.poll_key || pk.key;
                            const failCount = pk.fail_count ?? pk.consecutive_failures ?? 0;
                            const isEscalated = pk.users_alerted || failCount >= 20;
                            const hasFailed = failCount > 0;
                            const lastSuccess = pk.last_ok_at || pk.last_success_at;
                            return (
                              <tr key={keyName}>
                                <td className="is-mono">{keyName}</td>
                                <td>
                                  <span
                                    className={`console-tag ${isEscalated ? "is-bad" : hasFailed ? "is-warn" : "is-ok"
                                      }`}
                                  >
                                    {failCount} fails
                                  </span>
                                </td>
                                <td>
                                  {isEscalated ? (
                                    <span className="console-state is-bad">Outage escalated</span>
                                  ) : hasFailed ? (
                                    <span className="console-state is-warn">Transient glitch</span>
                                  ) : (
                                    <span className="console-state is-ok">Healthy</span>
                                  )}
                                </td>
                                <td className="is-mono is-truncate" title={pk.last_error || "None"}>
                                  {pk.last_error || "None"}
                                </td>
                                <td className="is-muted">
                                  {lastSuccess ? new Date(lastSuccess).toLocaleString() : "Never"}
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  )}
                </section>
              )}

              {/* BROADCASTS */}
              {activeTab === "broadcasts" && (
                <div className="console-split">
                  <section className="console-panel" aria-labelledby="compose-title">
                    <div className="console-panel-head">
                      <div>
                        <h2 className="console-panel-title" id="compose-title">
                          Compose a broadcast
                        </h2>
                        <p className="console-panel-line">
                          Send an announcement to every user over email and WhatsApp.
                        </p>
                      </div>
                    </div>

                    <form onSubmit={handleSendBroadcast} className="console-form">
                      <div className="console-field">
                        <label className="console-label" htmlFor="broadcast-title">
                          Campaign title
                        </label>
                        <input
                          id="broadcast-title"
                          type="text"
                          value={bTitle}
                          onChange={(e) => setBTitle(e.target.value)}
                          placeholder="Midnight shows are live for Game Changer"
                          required
                          className="console-input"
                        />
                      </div>

                      <div className="console-field">
                        <label className="console-label" htmlFor="broadcast-message">
                          Message
                        </label>
                        <textarea
                          id="broadcast-message"
                          rows={4}
                          value={bMessage}
                          onChange={(e) => setBMessage(e.target.value)}
                          placeholder="Tickets just dropped for midnight screenings at Prasad's IMAX and AMB Cinemas. Book before seats sell out."
                          required
                          className="console-input console-textarea"
                        />
                      </div>

                      <div className="console-field-row">
                        <div className="console-field">
                          <label className="console-label" htmlFor="broadcast-cta-text">
                            Button text
                          </label>
                          <input
                            id="broadcast-cta-text"
                            type="text"
                            value={bCtaText}
                            onChange={(e) => setBCtaText(e.target.value)}
                            placeholder="Book now"
                            className="console-input"
                          />
                        </div>

                        <div className="console-field">
                          <label className="console-label" htmlFor="broadcast-cta-url">
                            Button URL
                          </label>
                          <input
                            id="broadcast-cta-url"
                            type="url"
                            value={bCtaUrl}
                            onChange={(e) => setBCtaUrl(e.target.value)}
                            placeholder="https://in.bookmyshow.com"
                            className="console-input"
                          />
                        </div>
                      </div>

                      <fieldset className="console-fieldset">
                        <legend className="console-label">Delivery channels</legend>
                        <div className="console-checks">
                          <label className="console-check">
                            <input
                              type="checkbox"
                              checked={bChannels.includes("email")}
                              onChange={() => toggleChannel("email")}
                            />
                            <span>Email (Resend)</span>
                            <span className="console-check-reach">{emailReach} reachable</span>
                          </label>

                          <label className="console-check">
                            <input
                              type="checkbox"
                              checked={bChannels.includes("whatsapp")}
                              onChange={() => toggleChannel("whatsapp")}
                            />
                            <span>WhatsApp (OpenWA)</span>
                            <span className="console-check-reach">{whatsappReach} reachable</span>
                          </label>
                        </div>
                      </fieldset>

                      <div className="console-preview">
                        <div className="console-preview-head">
                          <span className="console-preview-label">Message preview</span>
                          <div className="console-seg">
                            <button
                              type="button"
                              onClick={() => setPreviewChannel("whatsapp")}
                              className={`console-seg-btn ${previewChannel === "whatsapp" ? "is-active" : ""
                                }`}
                            >
                              WhatsApp
                            </button>
                            <button
                              type="button"
                              onClick={() => setPreviewChannel("email")}
                              className={`console-seg-btn ${previewChannel === "email" ? "is-active" : ""
                                }`}
                            >
                              Email
                            </button>
                          </div>
                        </div>

                        <div className="console-preview-body">
                          <p className="console-preview-kicker">TicketFox announcement</p>
                          <p className="console-preview-title">
                            {bTitle || "Campaign title"}
                          </p>
                          <p className="console-preview-text">
                            {bMessage || "Your message body."}
                          </p>
                          {bCtaUrl && (
                            <span className="console-preview-cta">
                              {bCtaText || "Book tickets"}
                            </span>
                          )}
                        </div>
                      </div>

                      {broadcastNotice && (
                        <div className="console-notice">
                          <p className="console-notice-title">{broadcastNotice}</p>
                          {broadcastDetails && broadcastDetails.length > 0 && (
                            <ul className="console-recipients">
                              {broadcastDetails.map((det: any, idx: number) => (
                                <li
                                  key={idx}
                                  className={`console-recipient ${det.status === "delivered"
                                    ? "is-ok"
                                    : det.status === "skipped"
                                      ? "is-warn"
                                      : "is-bad"
                                    }`}
                                >
                                  <span className="is-mono is-truncate">
                                    {det.email || det.whatsapp || det.uid}
                                  </span>
                                  <span className="console-recipient-detail">
                                    {det.detail || det.status}
                                  </span>
                                </li>
                              ))}
                            </ul>
                          )}
                        </div>
                      )}

                      <button
                        type="submit"
                        disabled={sendingBroadcast}
                        className="console-btn console-btn-accent console-btn-block"
                      >
                        {sendingBroadcast ? (
                          <>
                            <RefreshCw className="console-icon is-spinning" aria-hidden="true" />
                            <span>Sending</span>
                          </>
                        ) : (
                          <>
                            <Send className="console-icon" aria-hidden="true" />
                            <span>Send to all</span>
                          </>
                        )}
                      </button>
                    </form>
                  </section>

                  <section className="console-panel" aria-labelledby="history-title">
                    <div className="console-panel-head">
                      <div>
                        <h2 className="console-panel-title" id="history-title">
                          Campaign history
                        </h2>
                        <p className="console-panel-line">What has already gone out.</p>
                      </div>
                    </div>

                    {broadcasts.length === 0 ? (
                      <div className="console-empty">
                        <p className="console-empty-title">Nothing sent yet</p>
                        <p className="console-empty-line">
                          The first campaign you dispatch will be listed here with its delivery
                          counts.
                        </p>
                      </div>
                    ) : (
                      <ul className="console-campaigns">
                        {broadcasts.map((camp) => (
                          <li key={camp.id} className="console-campaign">
                            <div className="console-campaign-head">
                              <span className="console-campaign-title">{camp.title}</span>
                              <span className="console-tag is-ok">{camp.status}</span>
                            </div>
                            <p className="console-campaign-line">{camp.message}</p>
                            <div className="console-campaign-foot">
                              <span>
                                Delivered <strong>{camp.sent_count}</strong>
                              </span>
                              <span>
                                Failed <strong>{camp.failed_count}</strong>
                              </span>
                              <span className="is-muted">
                                {new Date(camp.created_at).toLocaleDateString()}
                              </span>
                            </div>
                          </li>
                        ))}
                      </ul>
                    )}
                  </section>
                </div>
              )}

              {/* USERS & WATCHES */}
              {activeTab === "users_watches" && (
                <>
                  <section className="console-panel" aria-labelledby="users-title">
                    <div className="console-panel-head">
                      <div>
                        <h2 className="console-panel-title" id="users-title">
                          Registered accounts
                        </h2>
                        <p className="console-panel-line">
                          Every account, its delivery channels, and its watch count.
                        </p>
                      </div>
                      <span className="console-count">{usersList.length} accounts</span>
                    </div>

                    <div className="console-table-wrap">
                      <table className="console-table">
                        <thead>
                          <tr>
                            <th scope="col">User</th>
                            <th scope="col">Email</th>
                            <th scope="col">WhatsApp</th>
                            <th scope="col">Watches</th>
                            <th scope="col">Joined</th>
                            <th scope="col" className="is-right">
                              Actions
                            </th>
                          </tr>
                        </thead>
                        <tbody>
                          {usersList.map((u) => (
                            <tr key={u.uid || u.id}>
                              <td>
                                <span className="console-cell-strong">
                                  {u.name ||
                                    u.display_name ||
                                    (u.email ? u.email.split("@")[0] : "User")}
                                </span>
                                <span className="console-cell-sub is-mono">{u.uid || u.id}</span>
                              </td>
                              <td>{u.email || "Not set"}</td>
                              <td>
                                {u.whatsapp_number ? (
                                  <span className="is-mono">{u.whatsapp_number}</span>
                                ) : (
                                  <span className="is-muted">Missing</span>
                                )}
                              </td>
                              <td>
                                <span className="console-tag is-quiet">{u.watch_count ?? 0}</span>
                              </td>
                              <td className="is-muted">
                                {u.created_at
                                  ? new Date(u.created_at).toLocaleDateString()
                                  : "Not set"}
                              </td>
                              <td className="is-right">
                                <button
                                  type="button"
                                  onClick={() => {
                                    setEditingUser(u);
                                    setEditWhatsapp(u.whatsapp_number || u.phone || "");
                                    setEditEmail(u.email || "");
                                  }}
                                  className="console-btn console-btn-quiet console-btn-small"
                                >
                                  <Pencil className="console-icon" aria-hidden="true" />
                                  <span>{u.whatsapp_number ? "Edit" : "Add mobile"}</span>
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </section>

                  <section className="console-panel" aria-labelledby="watches-title">
                    <div className="console-panel-head">
                      <div>
                        <h2 className="console-panel-title" id="watches-title">
                          All watches
                        </h2>
                        <p className="console-panel-line">
                          Every watch in the system, its source, and its current state.
                        </p>
                      </div>
                      <span className="console-count">{watchesList.length} watches</span>
                    </div>

                    <div className="console-table-wrap">
                      <table className="console-table">
                        <thead>
                          <tr>
                            <th scope="col">Film</th>
                            <th scope="col">User</th>
                            <th scope="col">City</th>
                            <th scope="col">Source</th>
                            <th scope="col">State</th>
                            <th scope="col">Created</th>
                          </tr>
                        </thead>
                        <tbody>
                          {watchesList.map((w) => (
                            <tr key={w.id}>
                              <td>
                                <span className="console-cell-strong">{w.movie_title}</span>
                                <span className="console-cell-sub is-mono">
                                  #{w.id} {w.movie_id}
                                </span>
                              </td>
                              <td>
                                <span className="console-cell-strong">
                                  {w.user_name || "User"}
                                </span>
                                <span className="console-cell-sub is-truncate">
                                  {w.user_email || w.user_uid}
                                </span>
                              </td>
                              <td>{w.city}</td>
                              <td>
                                <span className="console-tag is-quiet">
                                  {w.source === "bookmyshow" ? "BookMyShow" : "District"}
                                </span>
                              </td>
                              <td>
                                <span
                                  className={`console-tag ${w.expired_at
                                    ? "is-bad"
                                    : w.state === "AVAILABLE"
                                      ? "is-ok"
                                      : "is-warn"
                                    }`}
                                >
                                  {w.expired_at ? "Expired" : w.state}
                                </span>
                              </td>
                              <td className="is-muted">
                                {w.created_at
                                  ? new Date(w.created_at).toLocaleDateString()
                                  : "Not set"}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </section>
                </>
              )}
            </div>
          </div>
        )}
      </main>

      {/* Edit user */}
      {editingUser && (
        <div className="console-modal" role="dialog" aria-modal="true" aria-labelledby="edit-user-title">
          <div className="console-dialog">
            <div className="console-dialog-head">
              <h2 className="console-dialog-title" id="edit-user-title">
                Edit delivery channels
              </h2>
              <button
                type="button"
                onClick={() => setEditingUser(null)}
                className="console-dialog-close"
                aria-label="Close"
              >
                <X className="console-icon" aria-hidden="true" />
              </button>
            </div>

            <p className="console-dialog-line">
              Update the channels for{" "}
              <strong>{editingUser.name || editingUser.email || editingUser.uid}</strong> so their
              alerts land.
            </p>

            <form onSubmit={handleSaveUser} className="console-form">
              <div className="console-field">
                <label className="console-label" htmlFor="edit-user-email">
                  Email address
                </label>
                <input
                  id="edit-user-email"
                  type="email"
                  value={editEmail}
                  onChange={(e) => setEditEmail(e.target.value)}
                  placeholder="user@example.com"
                  className="console-input"
                />
              </div>

              <div className="console-field">
                <label className="console-label" htmlFor="edit-user-whatsapp">
                  WhatsApp number
                </label>
                <input
                  id="edit-user-whatsapp"
                  type="text"
                  value={editWhatsapp}
                  onChange={(e) => setEditWhatsapp(e.target.value)}
                  placeholder="+919876543210"
                  className="console-input"
                />
                <span className="console-hint">
                  Ten digits, or the full number with country code.
                </span>
              </div>

              <div className="console-dialog-actions">
                <button
                  type="button"
                  onClick={() => setEditingUser(null)}
                  className="console-btn console-btn-quiet"
                >
                  <span>Cancel</span>
                </button>
                <button
                  type="submit"
                  disabled={savingUser}
                  className="console-btn console-btn-accent"
                >
                  {savingUser ? (
                    <>
                      <RefreshCw className="console-icon is-spinning" aria-hidden="true" />
                      <span>Saving</span>
                    </>
                  ) : (
                    <span>Save changes</span>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
