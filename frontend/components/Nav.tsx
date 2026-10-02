"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/", label: "Overview" },
  { href: "/datasets", label: "Datasets" },
  { href: "/search", label: "Entity Search" },
];

export function Nav() {
  const pathname = usePathname();
  return (
    <header className="sticky top-0 z-20 border-b border-white/10 bg-ink-950/80 backdrop-blur-md">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
        <Link href="/" className="flex items-center gap-3">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-accent-500 font-mono text-sm font-bold text-ink-950">
            ER
          </span>
          <div>
            <div className="text-sm font-semibold tracking-wide">Nexus Resolve</div>
            <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-white/50">
              Unified Entity Repository
            </div>
          </div>
        </Link>
        <nav className="flex items-center gap-1">
          {links.map((l) => {
            const active = pathname === l.href || (l.href !== "/" && pathname.startsWith(l.href));
            return (
              <Link
                key={l.href}
                href={l.href}
                className={`rounded-lg px-3 py-1.5 text-sm ${
                  active ? "bg-white/10 text-white" : "text-white/60 hover:text-white"
                }`}
              >
                {l.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
