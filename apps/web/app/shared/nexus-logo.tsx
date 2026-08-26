import Link from "next/link";

const configuredMarketingUrl = process.env.NEXT_PUBLIC_MARKETING_URL?.trim();
const marketingUrl = configuredMarketingUrl && (configuredMarketingUrl.startsWith("https://") || configuredMarketingUrl.startsWith("/"))
  ? configuredMarketingUrl
  : "/";

export function NexusLogo({
  light = false,
  landing = true,
  compact = false,
  className = "",
}: {
  light?: boolean;
  landing?: boolean;
  compact?: boolean;
  className?: string;
}) {
  return (
    <Link className={`nexus-brand nexus-brand-unified ${light ? "is-light" : ""} ${compact ? "is-compact" : ""} ${className}`.trim()} href={landing ? marketingUrl : "/"} aria-label="Nexus — voltar para a página inicial">
      <span className="nexus-symbol" aria-hidden="true">N</span>
      <span>NEXUS</span>
    </Link>
  );
}
