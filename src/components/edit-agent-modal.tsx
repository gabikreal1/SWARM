"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { PublishForm } from "@/components/publish-form";
import type { Agent } from "@/components/agent-card";

type Props = {
  agent: Agent;
  onClose: () => void;
};

export function EditAgentModal({ agent, onClose }: Props) {
  const router = useRouter();
  const [backdropPulse, setBackdropPulse] = useState(false);

  // Close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  const handleSaved = () => {
    router.refresh();
    onClose();
  };

  const handleBackdropClick = () => {
    setBackdropPulse(true);
    setTimeout(() => {
      setBackdropPulse(false);
      onClose();
    }, 120);
  };

  return (
    <div
      className={`fixed inset-0 z-50 flex items-center justify-center px-4 modal-overlay ${backdropPulse ? "modal-overlay-pulse" : ""}`}
      onClick={handleBackdropClick}
    >
      <div
        className="relative w-full max-w-3xl modal-card"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          className="absolute right-3 top-3 rounded-full bg-white px-3 py-1 text-sm shadow"
          onClick={onClose}
        >
          Close
        </button>
        <div className="glass max-h-[90vh] overflow-y-auto rounded-3xl p-6">
          <div className="pill mb-3 inline-flex">Edit agent</div>
          <h2 className="text-2xl font-semibold text-[var(--foreground)]">
            {agent.title}
          </h2>
          <p className="text-sm text-[var(--muted)]">
            Update your agent details. Changes save to the DB.
          </p>
          <div className="mt-4">
            <PublishForm
              mode="edit"
              agentId={Number(agent.id)}
              initial={{
                title: agent.title,
                description: agent.description,
                category: agent.category ?? undefined,
                priceUsd: agent.priceUsd,
                tags: agent.tags ?? undefined,
                network: agent.network ?? undefined,
              }}
              onSaved={handleSaved}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

