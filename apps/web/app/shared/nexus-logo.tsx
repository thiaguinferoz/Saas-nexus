import Image from "next/image";
import Link from "next/link";

const configuredMarketingUrl = process.env.NEXT_PUBLIC_MARKETING_URL?.trim();
const marketingUrl = configuredMarketingUrl && (configuredMarketingUrl.startsWith("https://") || configuredMarketingUrl.startsWith("/"))
  ? configuredMarketingUrl
  : "/";

export function NexusLogo({ light = false, landing = true }: { light?: boolean; landing?: boolean }) {
  return (
    <Link className={`nexus-brand ${light ? "is-light" : ""}`} href={landing ? marketingUrl : "/"} aria-label="Nexus — voltar para a página inicial">
      <span className="nexus-symbol"><Image src="/nexus-brand.jfif" alt="" width={96} height={96} priority /></span>
      <span>NEXUS<small>automações inteligentes</small></span>
    </Link>
  );
}
