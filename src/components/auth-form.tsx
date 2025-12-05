"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

type Mode = "login" | "signup";

export function AuthForm() {
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    const endpoint = mode === "login" ? "/api/auth/login" : "/api/auth/signup";
    const res = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password, name }),
    });

    if (!res.ok) {
      const data = await res.json();
      setError(data.error ? JSON.stringify(data.error) : "Auth failed");
      setLoading(false);
      return;
    }

    setLoading(false);
    router.push("/");
    router.refresh();
  };

  return (
    <div className="card max-w-md">
      <div className="mb-4 flex items-center justify-between">
        <div className="text-lg font-semibold text-[var(--foreground)]">
          {mode === "login" ? "Welcome back" : "Create your account"}
        </div>
        <button
          className="text-sm text-[var(--accent-strong)]"
          onClick={() => setMode(mode === "login" ? "signup" : "login")}
        >
          {mode === "login" ? "Need an account?" : "Have an account?"}
        </button>
      </div>
      <form className="flex flex-col gap-3" onSubmit={onSubmit}>
        {mode === "signup" && (
          <label className="text-sm text-[var(--muted)]">
            Name
            <input
              className="mt-1 w-full rounded-lg border border-[var(--border)] bg-white px-3 py-2 text-[var(--foreground)]"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </label>
        )}
        <label className="text-sm text-[var(--muted)]">
          Email
          <input
            className="mt-1 w-full rounded-lg border border-[var(--border)] bg-white px-3 py-2 text-[var(--foreground)]"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            type="email"
            required
          />
        </label>
        <label className="text-sm text-[var(--muted)]">
          Password
          <input
            className="mt-1 w-full rounded-lg border border-[var(--border)] bg-white px-3 py-2 text-[var(--foreground)]"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            type="password"
            required
            minLength={6}
          />
        </label>
        <button className="btn-primary w-full" type="submit" disabled={loading}>
          {loading ? "Working..." : mode === "login" ? "Log in" : "Sign up"}
        </button>
        {error && <div className="text-xs text-red-600">{error}</div>}
      </form>
      <p className="mt-3 text-xs text-[var(--muted)]">
        We use password auth today; connect your wallet on agent checkout for
        crypto transfers.
      </p>
    </div>
  );
}

