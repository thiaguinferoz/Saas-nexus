"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/v1";

export function AuthForm({ mode }: { mode: "login" | "register" }) {
  const router = useRouter();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setLoading(true); setError("");
    const values = Object.fromEntries(new FormData(event.currentTarget));
    try {
      const response = await fetch(`${API_URL}/auth/${mode}`, { method: "POST", credentials: "include", headers: { "Content-Type": "application/json" }, body: JSON.stringify(values) });
      if (!response.ok) { const body = await response.json(); throw new Error(typeof body.detail === "string" ? body.detail : "Não foi possível continuar."); }
      router.push("/app");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Erro inesperado."); } finally { setLoading(false); }
  }

  return <form className="form" onSubmit={submit}>{mode === "register" && <><label>Seu nome<input name="full_name" required minLength={2} placeholder="Como podemos chamar você?" /></label><label>Nome da empresa<input name="company_name" required minLength={2} placeholder="Sua empresa" /></label></>}<label>E-mail<input name="email" type="email" required placeholder="voce@empresa.com.br" /></label><label>Senha<input name="password" type="password" required minLength={10} placeholder="Mínimo de 10 caracteres" /></label>{error && <div className="form-message">{error}</div>}<button className="button" disabled={loading}>{loading ? "Só um momento..." : mode === "login" ? "Entrar no painel" : "Criar minha conta"}</button></form>;
}

