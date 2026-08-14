"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth-provider";
import { SiteHeader } from "@/components/site-header";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function LoginPage() {
  const { signIn, signUp, configured } = useAuth();
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setNotice(null);
    if (mode === "login") {
      const { error } = await signIn(email, password);
      if (error) setError(error);
      else router.push("/");
    } else {
      const { error, needsConfirm } = await signUp(email, password);
      if (error) setError(error);
      else if (needsConfirm)
        setNotice("Account created — check your email to confirm, then log in.");
      else router.push("/");
    }
    setBusy(false);
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      <SiteHeader />
      <main className="mx-auto flex max-w-md flex-col px-6 py-12">
        <Card>
          <CardHeader>
            <CardTitle className="text-xl">
              {mode === "login" ? "Log in" : "Create an account"}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {!configured ? (
              <p className="text-sm text-muted-foreground">
                Accounts aren&apos;t available yet — Supabase auth isn&apos;t
                configured on this deployment.
              </p>
            ) : (
              <form onSubmit={submit} className="space-y-3">
                <Input
                  type="email"
                  placeholder="Email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  autoComplete="email"
                />
                <Input
                  type="password"
                  placeholder="Password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  minLength={6}
                  autoComplete={
                    mode === "login" ? "current-password" : "new-password"
                  }
                />
                {error && <p className="text-sm text-destructive">{error}</p>}
                {notice && (
                  <p className="text-sm text-emerald-600 dark:text-emerald-400">
                    {notice}
                  </p>
                )}
                <Button type="submit" disabled={busy} className="w-full">
                  {busy
                    ? "Please wait…"
                    : mode === "login"
                    ? "Log in"
                    : "Create account"}
                </Button>
                <p className="text-center text-sm text-muted-foreground">
                  {mode === "login" ? (
                    <>
                      No account?{" "}
                      <button
                        type="button"
                        onClick={() => {
                          setMode("register");
                          setError(null);
                        }}
                        className="text-primary hover:underline"
                      >
                        Register
                      </button>
                    </>
                  ) : (
                    <>
                      Already have one?{" "}
                      <button
                        type="button"
                        onClick={() => {
                          setMode("login");
                          setError(null);
                        }}
                        className="text-primary hover:underline"
                      >
                        Log in
                      </button>
                    </>
                  )}
                </p>
              </form>
            )}
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
