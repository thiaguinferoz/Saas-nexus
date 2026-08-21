"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/v1";

async function request(endpoint: string, body: object) {
  const response = await fetch(`${API_URL}/auth/${endpoint}`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(typeof payload.detail === "string" ? payload.detail : "Não foi possível continuar.");
  return payload;
}

export function ForgotPasswordForm() {
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setLoading(true); setError("");
    const email = String(new FormData(event.currentTarget).get("email") || "");
    try { const body = await request("forgot-password", { email }); setMessage(body.message); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Erro inesperado."); }
    finally { setLoading(false); }
  }
  return <form className="form" onSubmit={submit}><label>E-mail<input name="email" type="email" required placeholder="voce@empresa.com.br"/></label>{error && <div className="form-message">{error}</div>}{message && <div className="form-message success">{message}</div>}<button className="button" disabled={loading}>{loading ? "Enviando..." : "Enviar instruções"}</button></form>;
}

export function ResendVerificationForm() {
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setLoading(true); setError("");
    const email = String(new FormData(event.currentTarget).get("email") || "");
    try { const body = await request("resend-verification", { email }); setMessage(body.message); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Erro inesperado."); }
    finally { setLoading(false); }
  }
  return <form className="form" onSubmit={submit}><label>E-mail<input name="email" type="email" required placeholder="voce@empresa.com.br"/></label>{error && <div className="form-message">{error}</div>}{message && <div className="form-message success">{message}</div>}<button className="button" disabled={loading}>{loading ? "Enviando..." : "Reenviar confirmação"}</button></form>;
}

export function VerifyEmailAction({ token }: { token: string }) {
  const router = useRouter();
  const requested = useRef(false);
  const [message, setMessage] = useState("Confirmando seu e-mail...");
  const [error, setError] = useState(false);
  useEffect(() => {
    if (requested.current) return;
    requested.current = true;
    if (!token) { setError(true); setMessage("Link de confirmação incompleto."); return; }
    request("verify-email", { token }).then(() => {
      setMessage("E-mail confirmado. Seus 3 dias grátis começaram agora.");
      setTimeout(() => router.replace("/app"), 1200);
    }).catch((reason) => { setError(true); setMessage(reason instanceof Error ? reason.message : "Link inválido."); });
  }, [router, token]);
  return <div className={`account-action-status ${error ? "error" : "success"}`}><strong>{message}</strong>{error && <a href="/login">Voltar para entrar</a>}</div>;
}

export function ResetPasswordForm({ token }: { token: string }) {
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setLoading(true); setError("");
    const password = String(new FormData(event.currentTarget).get("password") || "");
    try { const body = await request("reset-password", { token, password }); setMessage(body.message); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Erro inesperado."); }
    finally { setLoading(false); }
  }
  return <form className="form" onSubmit={submit}><label>Nova senha<input name="password" type="password" required minLength={10} placeholder="Mínimo de 10 caracteres"/></label>{error && <div className="form-message">{error}</div>}{message && <div className="form-message success">{message} <a href="/login">Entrar agora</a></div>}<button className="button" disabled={loading || !token || Boolean(message)}>{loading ? "Salvando..." : "Criar nova senha"}</button></form>;
}
