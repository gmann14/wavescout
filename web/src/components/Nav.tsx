"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/", label: "Map" },
  { href: "/methodology", label: "How It Works" },
  { href: "/about", label: "About" },
];

export default function Nav() {
  const pathname = usePathname();

  return (
    <nav className="bg-navy-900/95 backdrop-blur border-b border-navy-700 px-4 py-2.5 flex items-center justify-between z-50 relative">
      <Link href="/" className="flex items-center gap-2 group">
        <span className="text-teal-400 font-bold text-lg tracking-tight group-hover:text-teal-300 transition-colors">
          WaveScout
        </span>
        <span className="text-slate-500 text-xs hidden sm:inline">
          Nova Scotia
        </span>
      </Link>
      <div className="flex gap-1">
        {links.map((link) => {
          const active = pathname === link.href;
          return (
            <Link
              key={link.href}
              href={link.href}
              className={`px-3 py-1.5 rounded text-sm transition-colors ${
                active
                  ? "bg-navy-700 text-teal-400"
                  : "text-slate-400 hover:text-slate-200 hover:bg-navy-800"
              }`}
            >
              {link.label}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
