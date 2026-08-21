import Link from "next/link";
import { ResetPasswordForm } from "../shared/account-actions";
import { NexusLogo } from "../shared/nexus-logo";

export default async function ResetPasswordPage({ searchParams }: { searchParams: Promise<{ token?: string }> }) {
  const { token = "" } = await searchParams;
  return <main className="auth-page"><aside className="auth-aside"><NexusLogo light/><div className="auth-quote"><h1>Uma nova senha, com segurança.</h1><p>O link só pode ser usado uma vez e expira automaticamente.</p></div><small>Dados protegidos • Token individual</small></aside><section className="auth-main"><div className="auth-box"><h1>Crie sua nova senha.</h1><p>Use pelo menos 10 caracteres.</p><ResetPasswordForm token={token}/><div className="auth-switch"><Link href="/login">Voltar para entrar</Link></div></div></section></main>;
}
