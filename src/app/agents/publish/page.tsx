import { redirect } from "next/navigation";
import { PublishForm } from "@/components/publish-form";
import { getUserFromRequest } from "@/lib/auth";

export default async function PublishPage() {
  const user = await getUserFromRequest();
  if (!user) {
    redirect("/login");
  }
  return (
    <main className="mx-auto flex max-w-5xl flex-col gap-6 px-6 py-12">
      <div className="glass rounded-3xl p-8">
        <div className="pill mb-3 inline-flex">Publish</div>
        <h1 className="text-3xl font-semibold text-[var(--foreground)]">
          List your agent on the marketplace
        </h1>
        <p className="mt-2 max-w-3xl text-[var(--muted)]">
          Capture the basics, set pricing, and we keep the data in our DB.
          Buyers can log in and pay over EVM (Sepolia) with wallet connect.
        </p>
      </div>
      <PublishForm />
    </main>
  );
}

