"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { User } from "lucide-react";

type SessionUser = { id: number; email: string; name?: string | null };

export function Navbar() {
  const router = useRouter();
  const [user, setUser] = useState<SessionUser | null>(null);
  const [loading, setLoading] = useState(true);

  const displayName = useMemo(() => {
    if (!user) return "";
    if (user.name && user.name.trim().length > 0) {
      return user.name.split(" ")[0];
    }
    const localPart = user.email?.split("@")[0] || user.email;
    return localPart || "User";
  }, [user]);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const res = await fetch("/api/auth/me", {
          cache: "no-store",
          credentials: "include",
        });
        if (!res.ok) {
          if (!cancelled) setUser(null);
          return;
        }
        const data = await res.json();
        if (!cancelled) setUser(data.user);
      } catch {
        if (!cancelled) setUser(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleLogout = async () => {
    await fetch("/api/auth/logout", { method: "POST", credentials: "include" });
    setUser(null);
    router.refresh();
  };

  return (
    <header className="sticky top-0 z-30 border-b border-[var(--border)] bg-white/85 backdrop-blur-lg">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <Link href="/" className="flex items-center gap-2 font-semibold">
          <span className="pill">SpoonOS x Neo</span>
          <span className="text-lg text-[var(--accent-strong)]">Agent Hub</span>
        </Link>
        <nav className="flex items-center gap-4 text-sm font-medium text-[var(--muted)]">
          <Link href="/dashboard" className="hover:text-[var(--foreground)]">
            Dashboard
          </Link>
          <Link href="/agents/publish" className="hover:text-[var(--foreground)]">
            Publish
          </Link>
          {user ? (
            <div className="flex items-center gap-2">
              <span className="pill flex items-center gap-2">
                <User size={16} />
                {displayName}
              </span>
              <button
                className="btn-secondary"
                onClick={handleLogout}
                aria-label="Log out"
              >
                Logout
              </button>
            </div>
          ) : loading ? (
            <span className="text-[var(--muted)]">…</span>
          ) : (
            <Link href="/login" className="btn-secondary">
              Login
            </Link>
          )}
        </nav>
      </div>
    </header>
  );
}

