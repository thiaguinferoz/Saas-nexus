import Image from "next/image";
import Link from "next/link";

export function NexusLogo({ light = false, landing = true }: { light?: boolean; landing?: boolean }) {
  return (
    <Link className={`nexus-brand ${light ? "is-light" : ""}`} href={landing ? "https://usenexusia.com/" : "/"} aria-label="Nexus — voltar para a página inicial">
      <span className="nexus-symbol"><Image src="/nexus-brand.jfif" alt="" width={96} height={96} priority /></span>
      <span>NEXUS<small>automações inteligentes</small></span>
    </Link>
  );
}
