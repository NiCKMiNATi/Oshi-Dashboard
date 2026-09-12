"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { oshiMarker } from "@/lib/display";
import { feedHref, useFeedFilters } from "@/lib/use-feed-filters";
import type { Category } from "@/lib/types";
import { useAppData } from "./app-shell";

export function NavItem({
  href,
  active,
  children,
  count,
}: {
  href: string;
  active: boolean;
  children: React.ReactNode;
  count?: number;
}) {
  return (
    <Link
      className={`nav-item ${active ? "selected" : ""}`}
      href={href}
      aria-current={active ? "page" : undefined}
    >
      <span>{children}</span>
      {count !== undefined && <span className="nav-count">{count}</span>}
    </Link>
  );
}

export function OshiSwitcher() {
  const { oshi, loading, error } = useAppData();
  const { filters } = useFeedFilters();
  const onFeed = usePathname() === "/";
  return (
    <nav className="oshi-switcher" aria-label="My oshi">
      <Link
        href={feedHref({ ...filters, oshi: undefined })}
        className={`oshi-link ${onFeed && !filters.oshi ? "selected" : ""}`}
        aria-current={onFeed && !filters.oshi ? "true" : undefined}
      >
        <span className="all-oshi-symbol" aria-hidden="true">
          ✧
        </span>
        <span>All following</span>
        <span className="nav-count">{oshi.length}</span>
      </Link>
      {loading && !oshi.length && (
        <p className="sidebar-hint" role="status">
          Loading your oshi…
        </p>
      )}
      {Boolean(error) && !oshi.length && (
        <p className="sidebar-hint">Oshi unavailable</p>
      )}
      {!loading && !error && !oshi.length && (
        <p className="sidebar-hint">Follow your first oshi to get started.</p>
      )}
      {oshi.map((item) => (
        <Link
          key={item.id}
          href={feedHref({ ...filters, oshi: item.id })}
          aria-current={onFeed && filters.oshi === item.id ? "true" : undefined}
          className={`oshi-link ${onFeed && filters.oshi === item.id ? "selected" : ""} ${!item.active ? "paused" : ""}`}
        >
          <Image
            src={oshiMarker(item)}
            width={8}
            height={8}
            alt=""
            unoptimized
          />
          <span className="oshi-link-name">{item.name}</span>
          {!item.active && <span className="paused-label">Paused</span>}
        </Link>
      ))}
    </nav>
  );
}

export function Sidebar() {
  const { stats, openOshiForm, error } = useAppData();
  const { filters } = useFeedFilters();
  const pathname = usePathname();
  const categories: [Category, string][] = [
    ["EVENT", "Events"],
    ["MERCH", "Merch"],
    ["COLLAB", "Collabs"],
    ["MOVIE", "Movies"],
  ];
  return (
    <aside className="sidebar">
      <Link className="brand" href="/" aria-label="OSHI home">
        <span>
          OSHI<span className="brand-dot">.</span>
        </span>
        <small>personal dashboard</small>
      </Link>
      <div className="sidebar-section">
        <p className="eyebrow">My oshi</p>
        <OshiSwitcher />
        <button className="button sidebar-add" onClick={() => openOshiForm()}>
          + Add oshi
        </button>
      </div>
      <div className="sidebar-divider" />
      <nav className="sidebar-section" aria-label="Main navigation">
        <p className="eyebrow">Navigation</p>
        <NavItem
          href={feedHref({ oshi: filters.oshi })}
          active={pathname === "/" && !filters.category && !filters.status}
          count={stats?.by_status.NEW}
        >
          For You
        </NavItem>
        {categories.map(([category, label]) => (
          <NavItem
            key={category}
            href={feedHref({ oshi: filters.oshi, category })}
            active={pathname === "/" && filters.category === category}
          >
            {label}
          </NavItem>
        ))}
        <NavItem
          href={feedHref({ oshi: filters.oshi, status: "SAVED" })}
          active={pathname === "/" && filters.status === "SAVED"}
          count={stats?.by_status.SAVED}
        >
          Saved
        </NavItem>
        <div className="sidebar-divider short" />
        <NavItem href="/oshi" active={pathname === "/oshi"}>
          Oshi Management
        </NavItem>
      </nav>
      <div className="sidebar-footer">
        <span
          className={`connection-dot ${error ? "offline" : ""}`}
          aria-hidden="true"
        />
        <span>
          {error ? "Backend unavailable" : "Your private space"}
          <small>Local only · v0.1</small>
        </span>
      </div>
    </aside>
  );
}
