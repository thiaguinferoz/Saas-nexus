import Link from "next/link";
import { ForgotPasswordForm } from "../shared/account-actions";
import { NexusLogo } from "../shared/nexus-logo";

export default function ForgotPasswordPage() {
  return <main className="auth-page"><aside className="auth-aside"><NexusLogo light/><div className="auth-quote"><h1>Recupere o acesso com segurança.</h1><p>Enviaremos um link temporário para o e-mail confirmado da sua conta.</p></div><small>Link individual • Expira em 60 minutos</small></aside><section className="auth-main"><div className="auth-box"><h1>Esqueceu sua senha?</h1><p>Informe seu e-mail para continuar.</p><ForgotPasswordForm/><div className="auth-switch"><Link href="/login">Voltar para entrar</Link></div></div></section></main>;
}
