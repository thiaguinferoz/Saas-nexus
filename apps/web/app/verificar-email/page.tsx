import { VerifyEmailAction } from "../shared/account-actions";
import { NexusLogo } from "../shared/nexus-logo";

export default async function VerifyEmailPage({ searchParams }: { searchParams: Promise<{ token?: string }> }) {
  const { token = "" } = await searchParams;
  return <main className="account-action-page"><NexusLogo/><section><span>CONFIRMAÇÃO DE CONTA</span><h1>Estamos preparando sua Nexus.</h1><p>Depois da confirmação, seu período gratuito de 3 dias começa automaticamente.</p><VerifyEmailAction token={token}/></section></main>;
}
