import Link from "next/link";
import { ResendVerificationForm } from "../shared/account-actions";
import { NexusLogo } from "../shared/nexus-logo";

export default function ResendVerificationPage() {
  return <main className="auth-page"><aside className="auth-aside"><NexusLogo light/><div className="auth-quote"><h1>Confirme seu e-mail e comece.</h1><p>O teste grátis de 3 dias só começa depois que seu endereço for confirmado.</p></div><small>Link individual • Válido por 24 horas</small></aside><section className="auth-main"><div className="auth-box"><h1>Reenviar confirmação.</h1><p>Informe o e-mail usado no cadastro.</p><ResendVerificationForm/><div className="auth-switch"><Link href="/login">Voltar para entrar</Link></div></div></section></main>;
}
