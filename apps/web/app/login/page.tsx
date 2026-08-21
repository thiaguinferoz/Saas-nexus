import Link from "next/link";
import { AuthForm } from "../shared/auth-form";
import { NexusLogo } from "../shared/nexus-logo";

export default function LoginPage() {
  return <main className="auth-page"><aside className="auth-aside"><NexusLogo light/><div className="auth-quote"><h1>Boas conversas constroem grandes negócios.</h1><p>Entre no painel para acompanhar e configurar seu atendimento.</p></div><small>WhatsApp oficial • Seus dados protegidos</small></aside><section className="auth-main"><div className="auth-box"><h1>Que bom ter você aqui.</h1><p>Entre com os dados da sua conta.</p><AuthForm mode="login"/><div className="auth-switch">Ainda não possui uma conta? <Link href="/cadastro">Cadastrar-se</Link></div></div></section></main>;
}
