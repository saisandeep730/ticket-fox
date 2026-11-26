"use client";

import React, { useState, useEffect } from "react";
import {
  X,
  Mail,
  MessageSquare,
  Save,
  Zap,
  Loader2,
  Smartphone,
} from "lucide-react";
import { apiFetch } from "../lib/api";
import { toE164India, toIndianDigits } from "../lib/phone";

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  userToken: string;
  user?: any;
  onShowToast: (msg: string, type?: "success" | "error" | "info") => void;
}

export default function SettingsModal({
  isOpen,
  onClose,
  userToken,
  user,
  onShowToast,
}: SettingsModalProps) {
  const [email, setEmail] = useState("");
  const [whatsappDigits, setWhatsappDigits] = useState("");
  const [channels, setChannels] = useState<{ email?: boolean; whatsapp?: boolean }>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);

  useEffect(() => {
    if (!isOpen || !userToken) return;
    setLoading(true);
    apiFetch("/api/user/me", {}, userToken)
      .then((data) => {
        const p = data.profile || {};
        setEmail(p.email || user?.email || "");
        setWhatsappDigits(toIndianDigits(p.whatsapp_number || ""));
        if (data.channels) {
          setChannels(data.channels);
        }
      })
      .catch((err) => console.error(err))
      .finally(() => setLoading(false));
  }, [isOpen, userToken, user]);

  if (!isOpen) return null;

  const handlePhoneChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const raw = e.target.value.replace(/\D/g, "");
    if (raw.length <= 10) {
      setWhatsappDigits(raw);
    } else if (raw.length === 12 && raw.startsWith("91")) {
      setWhatsappDigits(raw.slice(2));
    } else if (raw.length === 11 && raw.startsWith("0")) {
      setWhatsappDigits(raw.slice(1));
    } else {
      setWhatsappDigits(raw.slice(-10));
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!whatsappDigits.trim() || whatsappDigits.length !== 10) {
      onShowToast(
        "WhatsApp number is compulsory! Please enter a valid 10-digit Indian mobile number.",
        "error"
      );
      return;
    }
    setSaving(true);
    try {
      await apiFetch(
        "/api/user/me",
        {
          method: "PATCH",
          body: JSON.stringify({
            whatsapp_number: toE164India(whatsappDigits),
            email: email.trim(),
          }),
        },
        userToken
      );
      onShowToast("Notification channels saved successfully!", "success");
      onClose();
    } catch (e: any) {
      onShowToast(e?.message || "Failed to save preferences", "error");
    } finally {
      setSaving(false);
    }
  };

  const handleTestAlert = async () => {
    if (!whatsappDigits.trim() || whatsappDigits.length !== 10) {
      onShowToast("Enter a 10-digit WhatsApp number first to test alert delivery.", "error");
      return;
    }
    setTesting(true);
    try {
      await apiFetch(
        "/api/user/me",
        {
          method: "PATCH",
          body: JSON.stringify({
            whatsapp_number: toE164India(whatsappDigits),
            email: email.trim(),
          }),
        },
        userToken
      );
      const data = await apiFetch("/api/user/me/test-alert", { method: "POST" }, userToken);
      onShowToast(data.message || "Test alert dispatched! Check WhatsApp / Email", "success");
    } catch (e: any) {
      onShowToast(e?.message || "Could not dispatch test alert", "error");
    } finally {
      setTesting(false);
    }
  };

  return (
    <div role="dialog" aria-modal="true" className="modal-backdrop">
      <div className="modal-panel modal-panel--lg">
        <div className="modal-body modal-stack">
          {/* Close Button */}
          <button onClick={onClose} aria-label="Close dialog" className="modal-close">
            <X className="w-4 h-4" aria-hidden="true" />
          </button>

          {/* Modal Header */}
          <div className="modal-head-row">
            <div className="modal-head-icon">
              <Smartphone className="w-5 h-5" aria-hidden="true" />
            </div>
            <div>
              <h3 className="modal-title">Notification Preferences</h3>
              <p className="modal-subtitle">
                Configure where TicketFox sends immediate ticket opening alerts
              </p>
            </div>
          </div>

          {loading ? (
            <div className="modal-loading">
              <Loader2 className="w-8 h-8 text-accent animate-spin" aria-hidden="true" />
              <p>Loading your preferences...</p>
            </div>
          ) : (
            <form onSubmit={handleSave} className="modal-stack">
              {/* WhatsApp Field */}
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="field-label flex items-center gap-1.5 mb-0">
                    <MessageSquare className="w-3.5 h-3.5 text-emerald-400" aria-hidden="true" />
                    <span>WhatsApp Mobile Number</span>
                    <span className="text-rose-400">*</span>
                  </label>
                  <span className="badge badge--success">Instant Drop Alerts</span>
                </div>

                <div className="modal-phone-group">
                  <div className="modal-phone-prefix">+91</div>
                  <input
                    type="tel"
                    value={whatsappDigits}
                    onChange={handlePhoneChange}
                    placeholder="9876543210 (10 digits)"
                    maxLength={10}
                    className="modal-phone-input"
                    required
                  />
                </div>
                <p className="field-hint">
                  Compulsory for instant alerts in India. We scan every few seconds so you grab
                  premiere tickets immediately!
                </p>
              </div>

              {/* Email Field */}
              <div>
                <label className="field-label flex items-center gap-1.5">
                  <Mail className="w-3.5 h-3.5 text-muted" aria-hidden="true" />
                  <span>Email Address (Optional)</span>
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@domain.com"
                  className="field-input"
                />
              </div>

              {/* Test Alert Button */}
              <div className="modal-note">
                <div>
                  <p className="text-xs font-bold text-secondary">Want to test your alerts now?</p>
                  <p className="text-[11px] text-muted">
                    Sends a sample ticket-opening ping to verify your channels.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={handleTestAlert}
                  disabled={testing}
                  className="modal-btn-test"
                >
                  {testing ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" aria-hidden="true" />
                  ) : (
                    <Zap className="w-3.5 h-3.5" aria-hidden="true" />
                  )}
                  <span>Send Test Drill</span>
                </button>
              </div>

              {/* Action Buttons */}
              <div className="modal-actions">
                <button type="button" onClick={onClose} className="modal-btn-quiet">
                  Cancel
                </button>
                <button type="submit" disabled={saving} className="modal-btn-accent">
                  {saving ? (
                    <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
                  ) : (
                    <Save className="w-4 h-4" aria-hidden="true" />
                  )}
                  <span>Save Notification Settings</span>
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
