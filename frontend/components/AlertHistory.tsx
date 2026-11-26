"use client";

import React, { useState } from "react";
import {
  History,
  RefreshCw,
  Mail,
  MessageSquare,
  CheckCircle2,
  XCircle,
  ServerCrash,
} from "lucide-react";

interface AlertHistoryProps {
  alerts: any[];
  onRefresh: () => void;
}

const CHANNEL_ICONS: Record<string, React.ReactNode> = {
  email: <Mail className="w-3.5 h-3.5 text-emerald-400" aria-hidden="true" />,
  whatsapp: <MessageSquare className="w-3.5 h-3.5 text-emerald-400" aria-hidden="true" />,
};

function formatAlertDate(isoString: string | null): string {
  if (!isoString) return "";
  try {
    const formatted = isoString.endsWith("Z") ? isoString : isoString + "Z";
    return new Date(formatted).toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return isoString;
  }
}

export default function AlertHistory({ alerts, onRefresh }: AlertHistoryProps) {
  const [isRefreshing, setIsRefreshing] = useState(false);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      await onRefresh();
    } finally {
      setTimeout(() => setIsRefreshing(false), 500);
    }
  };

  return (
    <section className="alert-log">
      <div className="alert-log-head">
        <h3 className="alert-log-title">
          <History className="w-4 h-4 text-accent" aria-hidden="true" />
          <span>Delivered Alert Log</span>
          <span className="alert-log-count">{alerts.length}</span>
        </h3>
        <button
          onClick={handleRefresh}
          disabled={isRefreshing}
          className="alert-log-refresh"
        >
          <RefreshCw
            className={`w-3 h-3 ${isRefreshing ? "animate-spin text-accent" : ""}`}
            aria-hidden="true"
          />
          <span>Refresh</span>
        </button>
      </div>

      {alerts.length === 0 ? (
        <div className="alert-log-empty">
          <p className="text-xs text-muted font-medium">No alerts dispatched yet.</p>
          <p className="text-[11px] text-muted max-w-sm mx-auto mt-1.5">
            Use <strong className="text-secondary">Test Drill</strong> on any active watch or in{" "}
            <strong className="text-secondary">Settings</strong> to verify your WhatsApp and Email delivery.
          </p>
        </div>
      ) : (
        <ul className="alert-log-list">
          {alerts.map((alert) => {
            const statusUpper = String(alert.status).toUpperCase();
            const sent = statusUpper === "SENT";
            const unavailable = statusUpper === "UNAVAILABLE";

            return (
              <li key={alert.id} className="alert-log-item">
                <span className="mt-0.5 shrink-0">
                  {sent ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" aria-hidden="true" />
                  ) : unavailable ? (
                    <ServerCrash className="w-4 h-4 text-amber-400" aria-hidden="true" />
                  ) : (
                    <XCircle className="w-4 h-4 text-rose-400" aria-hidden="true" />
                  )}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="alert-log-item-head">
                    <span className="alert-log-channel">
                      {CHANNEL_ICONS[alert.channel] || null}
                      <span>{alert.channel}</span>
                    </span>
                    <span
                      className={`badge ${sent
                          ? "badge--success"
                          : unavailable
                            ? "badge--warning"
                            : "badge--danger"
                        }`}
                    >
                      {statusUpper}
                    </span>
                    {alert.created_at && (
                      <span className="alert-log-time">{formatAlertDate(alert.created_at)}</span>
                    )}
                  </div>
                  <p className="alert-log-message">
                    {(alert.message || "")
                      .split("\n")
                      .filter(Boolean)
                      .slice(0, 2)
                      .join(" · ")}
                  </p>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
