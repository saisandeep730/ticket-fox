"use client";

import React, { useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { Flame } from "lucide-react";

interface TicketFoxLogoProps {
  size?: "sm" | "md" | "lg" | "xl";
  showText?: boolean;
  href?: string | null;
}

export default function TicketFoxLogo({
  size = "md",
  showText = true,
  href = "/",
}: TicketFoxLogoProps) {
  const [imgError, setImgError] = useState(false);

  const sizeDimensions = {
    sm: { box: "logo-box-sm", px: 28 },
    md: { box: "logo-box-md", px: 36 },
    lg: { box: "logo-box-lg", px: 44 },
    xl: { box: "logo-box-xl", px: 56 },
  };

  const { box, px } = sizeDimensions[size];

  const logoNode = (
    <span className="logo">
      <span className={`logo-box ${box}`}>
        {!imgError ? (
          <Image
            src="/logo.jpg"
            alt="TicketFox"
            width={px}
            height={px}
            className="logo-img"
            priority
            onError={() => setImgError(true)}
          />
        ) : (
          <Flame className="logo-fallback" aria-hidden="true" />
        )}
      </span>

      {showText && (
        <span className="logo-text">
          Ticket<span className="logo-text-accent">Fox</span>
        </span>
      )}
    </span>
  );

  if (href) {
    return (
      <Link href={href} className="logo-link" title="TicketFox home">
        {logoNode}
      </Link>
    );
  }

  return logoNode;
}
