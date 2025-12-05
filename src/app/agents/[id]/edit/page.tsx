import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { PublishForm } from "@/components/publish-form";
import { getUserFromRequest } from "@/lib/auth";
import { prisma } from "@/lib/prisma";

type Params = { params: { id: string } };

export default async function EditAgentPage({ params }: Params) {
  const id = Number(params.id);
  if (Number.isNaN(id)) return notFound();

  const user = await getUserFromRequest();
  if (!user) {
    redirect("/login");
  }
  const agent = await prisma.agent.findUnique({ where: { id } });

  if (!agent) return notFound();
  if (!user || agent.ownerId !== user.id) {
    return (
      <main className="mx-auto flex max-w-4xl flex-col gap-4 px-6 py-12">
        <div className="glass rounded-3xl p-8">
          <div className="pill mb-3 inline-flex">Access restricted</div>
          <h1 className="text-3xl font-semibold text-[var(--foreground)]">
            You cannot edit this agent
          </h1>
          <p className="mt-2 text-[var(--muted)]">
            Switch accounts or choose one of your own agents.
          </p>
          <Link href="/dashboard" className="btn-primary mt-4 inline-block">
            Back to dashboard
          </Link>
        </div>
      </main>
    );
  }

  return (
    <main className="mx-auto flex max-w-5xl flex-col gap-6 px-6 py-12">
      <div className="glass rounded-3xl p-8">
        <div className="pill mb-3 inline-flex">Edit agent</div>
        <h1 className="text-3xl font-semibold text-[var(--foreground)]">
          Update your listing
        </h1>
        <p className="mt-2 max-w-3xl text-[var(--muted)]">
          Adjust details for your SpoonOS/Neo agent. Changes are saved to the DB.
        </p>
      </div>
      <PublishForm
        mode="edit"
        agentId={agent.id}
        initial={{
          title: agent.title,
          description: agent.description,
          category: agent.category ?? undefined,
          priceUsd: agent.priceUsd,
          tags: agent.tags ?? undefined,
          network: agent.network ?? undefined,
        }}
      />
    </main>
  );
}

