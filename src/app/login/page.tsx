import { AuthForm } from "@/components/auth-form";
import { getUserFromRequest } from "@/lib/auth";
import { redirect } from "next/navigation";

export default async function LoginPage() {
  const user = await getUserFromRequest();
  if (user) {
    redirect("/");
  }
  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col items-center justify-center gap-6 px-6 py-12">
      <div className="glass w-full rounded-3xl p-8">
        <div className="pill mb-3 inline-flex">Secure login</div>
        <h1 className="text-3xl font-semibold text-[var(--foreground)]">
          Log in or sign up
        </h1>
        <p className="mt-2 max-w-2xl text-[var(--muted)]">
          Credentials live in our database; crypto transfers stay on-chain. Use
          wallet connect on agent checkout when you are ready to pay.
        </p>
      </div>
      <div className="w-full">
        <AuthForm />
      </div>
    </main>
  );
}

