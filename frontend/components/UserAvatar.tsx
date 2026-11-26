"use client";

import React, { useState } from "react";

interface UserAvatarProps {
  user?: any;
  size?: "sm" | "md" | "lg";
  className?: string;
}

/**
 * Checks if a Google photoURL appears to be a generic/letter default placeholder
 * rather than a user-uploaded photo.
 */
function isGoogleDefaultLetterAvatar(url: string | null | undefined): boolean {
  if (!url) return true;
  const lower = url.toLowerCase();
  // Google default placeholder URLs or missing photos
  if (lower.includes("default-user") || lower.includes("/ogw/default") || lower.includes("/a/default")) {
    return true;
  }
  return false;
}

export default function UserAvatar({ user, size = "md", className = "" }: UserAvatarProps) {
  const [imageError, setImageError] = useState(false);

  const sizeClasses = {
    sm: "w-7 h-7 rounded-xl text-[10px]",
    md: "w-8 h-8 sm:w-9 sm:h-9 rounded-2xl text-xs",
    lg: "w-12 h-12 rounded-2xl text-sm",
  }[size];

  // If user is not logged in: consistent guest DiceBear avatar
  if (!user) {
    const guestDicebear = "https://api.dicebear.com/7.x/bottts/svg?seed=ticketfox-guest&backgroundColor=transparent";
    return (
      <div className={`avatar avatar--guest ${sizeClasses} ${className}`}>
        <img
          src={guestDicebear}
          alt="Guest Avatar"
          className="avatar-img avatar-img--padded"
          loading="lazy"
        />
      </div>
    );
  }

  const rawPhoto = user.photoURL || user.picture;
  const isEmailPasswordUser = Boolean(user.providerData?.[0]?.providerId === "password" || user.isEmailAuth);
  const isDefaultLetter = isGoogleDefaultLetterAvatar(rawPhoto);

  // If user has a real custom photo and not marked as default letter, try loading it
  const canUseCustomPhoto = rawPhoto && !isEmailPasswordUser && !isDefaultLetter && !imageError;

  // DiceBear seed based on stable user identity (email or UID)
  const seed = encodeURIComponent((user.email || user.uid || "ticketfox-user").trim().toLowerCase());
  const dicebearUrl = `https://api.dicebear.com/7.x/bottts/svg?seed=${seed}&backgroundColor=transparent`;

  if (canUseCustomPhoto) {
    return (
      <div className={`avatar avatar--photo ${sizeClasses} ${className}`}>
        <img
          src={rawPhoto}
          alt={user.displayName || "User"}
          referrerPolicy="no-referrer"
          onError={() => setImageError(true)}
          className="avatar-img"
          loading="lazy"
        />
      </div>
    );
  }

  // Fallback to DiceBear personal avatar
  return (
    <div className={`avatar avatar--fallback ${sizeClasses} ${className}`}>
      <img
        src={dicebearUrl}
        alt={user.displayName || user.email || "Avatar"}
        className="avatar-img avatar-img--padded"
        loading="lazy"
      />
    </div>
  );
}
