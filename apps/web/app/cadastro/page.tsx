import Link from "next/link";
import { AuthForm } from "../shared/auth-form";
import { NexusLogo } from "../shared/nexus-logo";

export default function RegisterPage() {
  return <main className="auth-page"><aside className="auth-aside"><NexusLogo light/><div className="auth-quote"><h1>Comece simples. Cresça sem perder o cuidado.</h1><p>Crie sua conta e prepare seu atendimento inteligente em poucos passos.</p></div><small>Configuração guiada • Cancele quando quiser</small></aside><section className="auth-main"><div className="auth-box"><h1>Crie sua conta.</h1><p>Leva menos de dois minutos.</p><AuthForm mode="register"/><div className="auth-switch">Já tem uma conta? <Link href="/login">Entrar</Link></div></div></section></main>;
}
