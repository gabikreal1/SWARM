"use client";

"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

type Props = {
  mode?: "create" | "edit";
  agentId?: number;
  initial?: {
    title: string;
    description: string;
    category?: string | null;
    priceUsd: number;
    tags?: string | null;
    network?: string | null;
  };
  onSaved?: () => void;
};

export function PublishForm({ mode = "create", agentId, initial, onSaved }: Props) {
  const [title, setTitle] = useState(initial?.title ?? "");
  const [description, setDescription] = useState(initial?.description ?? "");
  const [category, setCategory] = useState(initial?.category ?? "Automation");
  const [priceUsd, setPriceUsd] = useState(
    initial ? String(initial.priceUsd) : "25",
  );
  const [tags, setTags] = useState(initial?.tags ?? "ai,automation");
  const [network, setNetwork] = useState(initial?.network ?? "neox-testnet");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    const idForEdit = mode === "edit" ? Number(agentId) : null;
    if (mode === "edit" && (!idForEdit || Number.isNaN(idForEdit))) {
      setError("Missing or invalid agent id");
      setLoading(false);
      return;
    }
    const payload = {
      title,
      description,
      category,
      priceUsd: Number(priceUsd),
      tags,
      network,
      id: idForEdit ?? undefined,
    };
    const res =
      mode === "edit" && idForEdit
        ? await fetch(`/api/agents/${encodeURIComponent(String(idForEdit))}`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
            cache: "no-store",
          })
        : await fetch("/api/agents", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
            cache: "no-store",
          });
    const data = await res.json();
    setLoading(false);
    if (!res.ok) {
      const err =
        typeof data?.error === "string"
          ? data.error
          : data?.error
          ? JSON.stringify(data.error)
          : "Unable to save";
      setError(err);
      return;
    }
    if (onSaved) {
      onSaved();
    } else {
      router.push("/dashboard");
    }
  };

  return (
    <form className="card flex flex-col gap-3" onSubmit={onSubmit}>
      <h2 className="text-lg font-semibold text-[var(--foreground)]">
        {mode === "edit" ? "Edit your agent" : "Publish your agent"}
      </h2>
      <label className="text-sm text-[var(--muted)]">
        Title
        <input
          className="mt-1 w-full rounded-lg border border-[var(--border)] bg-white px-3 py-2 text-[var(--foreground)]"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
        />
      </label>
      <label className="text-sm text-[var(--muted)]">
        Description
        <textarea
          className="mt-1 w-full rounded-lg border border-[var(--border)] bg-white px-3 py-2 text-[var(--foreground)]"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={4}
          required
        />
      </label>
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="text-sm text-[var(--muted)]">
          Category
          <input
            className="mt-1 w-full rounded-lg border border-[var(--border)] bg-white px-3 py-2 text-[var(--foreground)]"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
          />
        </label>
        <label className="text-sm text-[var(--muted)]">
          Price (USD)
          <input
            className="mt-1 w-full rounded-lg border border-[var(--border)] bg-white px-3 py-2 text-[var(--foreground)]"
            value={priceUsd}
            onChange={(e) => setPriceUsd(e.target.value)}
            type="number"
            min="0"
          />
        </label>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="text-sm text-[var(--muted)]">
          Tags (comma separated)
          <input
            className="mt-1 w-full rounded-lg border border-[var(--border)] bg-white px-3 py-2 text-[var(--foreground)]"
            value={tags}
            onChange={(e) => setTags(e.target.value)}
          />
        </label>
        <label className="text-sm text-[var(--muted)]">
          Network
          <input
            className="mt-1 w-full rounded-lg border border-[var(--border)] bg-white px-3 py-2 text-[var(--foreground)]"
            value={network}
            onChange={(e) => setNetwork(e.target.value)}
          />
        </label>
      </div>
      <button className="btn-primary mt-2" type="submit" disabled={loading}>
        {loading ? "Saving..." : mode === "edit" ? "Save changes" : "Publish agent"}
      </button>
      {error && <div className="text-xs text-red-600">{error}</div>}
      <p className="text-xs text-[var(--muted)]">
        Agents are stored via SpoonOS/Neo-backed catalog; crypto checkout uses
        Arc/Neo X testnet by default.
      </p>
    </form>
  );
}
