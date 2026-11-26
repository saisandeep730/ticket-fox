"use client";

import React from "react";
import { Film, Bell, Settings, Plus, Search } from "lucide-react";

interface MobileNavProps {
  activeTab: "discover" | "watches";
  setActiveTab: (tab: "discover" | "watches") => void;
  watchCount: number;
  onOpenSettings: () => void;
  onOpenWizard: () => void;
}

export default function MobileNav({
  activeTab,
  setActiveTab,
  watchCount,
  onOpenSettings,
  onOpenWizard,
}: MobileNavProps) {
  const handleScrollToSearch = () => {
    setActiveTab("discover");
    window.scrollTo({ top: 0, behavior: "smooth" });
    setTimeout(() => {
      const input = document.querySelector('input[type="text"]') as HTMLInputElement;
      input?.focus();
    }, 200);
  };

  return (
    <nav aria-label="Mobile Navigation" className="mobile-nav">
      <div className="mobile-nav-inner">
        {/* 1. Movies Tab */}
        <button
          onClick={() => {
            setActiveTab("discover");
            window.scrollTo({ top: 0, behavior: "smooth" });
          }}
          className={`mobile-nav-item${activeTab === "discover" ? " is-active" : ""}`}
        >
          <Film className="w-5 h-5" aria-hidden="true" />
          <span>Movies</span>
        </button>

        {/* 2. Watches Tab */}
        <button
          onClick={() => {
            setActiveTab("watches");
            window.scrollTo({ top: 0, behavior: "smooth" });
          }}
          className={`mobile-nav-item${activeTab === "watches" ? " is-active" : ""}`}
        >
          <span className="mobile-nav-icon-wrap">
            <Bell className="w-5 h-5" aria-hidden="true" />
            {watchCount > 0 && <span className="mobile-nav-badge">{watchCount}</span>}
          </span>
          <span>Watches</span>
        </button>

        {/* 3. Center Elevated Plus Watch Button */}
        <div className="mobile-nav-center">
          <button
            onClick={onOpenWizard}
            className="mobile-nav-create"
            title="Create New Ticket Watch"
            aria-label="Create New Ticket Watch"
          >
            <Plus className="w-6 h-6 stroke-[3]" aria-hidden="true" />
          </button>
        </div>

        {/* 4. Quick Search */}
        <button onClick={handleScrollToSearch} className="mobile-nav-item">
          <Search className="w-5 h-5" aria-hidden="true" />
          <span>Search</span>
        </button>

        {/* 5. Settings */}
        <button onClick={onOpenSettings} className="mobile-nav-item">
          <Settings className="w-5 h-5" aria-hidden="true" />
          <span>Settings</span>
        </button>
      </div>
    </nav>
  );
}
