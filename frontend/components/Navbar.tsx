"use client";

import React, { useState, useRef, useEffect } from "react";
import {
  MapPin,
  LogOut,
  Settings,
  ChevronDown,
} from "lucide-react";
import TicketFoxLogo from "./TicketFoxLogo";
import UserAvatar from "./UserAvatar";
import { FALLBACK_CITIES, loadCities, type City } from "../lib/cities";

interface NavbarProps {
  currentCity: string;
  onCityChange: (city: string) => void;
  user: any;
  onOpenAuth: () => void;
  onOpenSettings: () => void;
  onLogout: () => void;
  activeWatchCount: number;
  onOpenWatches?: () => void;
}

export default function Navbar({
  currentCity,
  onCityChange,
  user,
  onOpenAuth,
  onOpenSettings,
  onLogout,
  activeWatchCount,
  onOpenWatches,
}: NavbarProps) {
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [cities, setCities] = useState<City[]>(FALLBACK_CITIES);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    loadCities().then(setCities);
  }, []);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleMouseEnter = () => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    setIsDropdownOpen(true);
  };

  const handleMouseLeave = () => {
    timeoutRef.current = setTimeout(() => {
      setIsDropdownOpen(false);
    }, 200);
  };

  const toggleDropdown = () => {
    setIsDropdownOpen((prev) => !prev);
  };

  return (
    <header className="nav">
      <div className="container nav-inner">
        {/* The wordmark, at the left edge */}
        <TicketFoxLogo size="md" />

        {/* Everything else, at the right edge */}
        <div className="nav-actions">
          {/* City: the one control the page's facts depend on */}
          <div className="nav-city">
            <MapPin className="nav-city-icon" aria-hidden="true" />
            <select
              value={currentCity}
              onChange={(e) => onCityChange(e.target.value)}
              aria-label="Select City"
              className="nav-city-select"
            >
              {cities.map((c) => (
                <option key={c.key} value={c.name}>
                  {c.name}
                </option>
              ))}
            </select>
            <ChevronDown className="nav-city-chevron" aria-hidden="true" />
          </div>

          {/* Active watches: a count, not a decorative dot */}
          {activeWatchCount > 0 && (
            <button
              onClick={onOpenWatches}
              title="View your active watches"
              className="nav-watch-count"
            >
              <span className="num">{activeWatchCount}</span>
              <span className="nav-watch-label">
                {activeWatchCount === 1 ? "watch" : "watches"}
              </span>
            </button>
          )}

          {/* The one action */}
          {user ? (
            <div
              className="nav-user"
              ref={dropdownRef}
              onMouseEnter={handleMouseEnter}
              onMouseLeave={handleMouseLeave}
            >
              <button
                onClick={toggleDropdown}
                aria-expanded={isDropdownOpen}
                aria-haspopup="true"
                className="nav-user-button"
              >
                <UserAvatar user={user} size="sm" />
                <span className="nav-user-name">
                  {user.displayName?.split(" ")[0] || user.email?.split("@")[0] || "User"}
                </span>
                <ChevronDown
                  className={`nav-user-chevron${isDropdownOpen ? " is-open" : ""}`}
                  aria-hidden="true"
                />
              </button>

              {isDropdownOpen && (
                <div className="nav-menu">
                  <div className="nav-menu-head">
                    <p className="nav-menu-name">{user.displayName || "TicketFox User"}</p>
                    <p className="nav-menu-email">{user.email || ""}</p>
                  </div>

                  <div className="nav-menu-items">
                    <button
                      onClick={() => {
                        setIsDropdownOpen(false);
                        onOpenSettings();
                      }}
                      className="nav-menu-item"
                    >
                      <Settings className="nav-menu-icon" aria-hidden="true" />
                      <span>Notification settings</span>
                    </button>

                    <div className="nav-menu-rule" />

                    <button
                      onClick={() => {
                        setIsDropdownOpen(false);
                        onLogout();
                      }}
                      className="nav-menu-item is-danger"
                    >
                      <LogOut className="nav-menu-icon" aria-hidden="true" />
                      <span>Sign out</span>
                    </button>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <button onClick={onOpenAuth} className="btn-primary nav-signin">
              <UserAvatar size="sm" />
              <span>Sign in</span>
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
