import Image from "next/image";
import Link from "next/link";

export function NexusLogo({ light = false }: { light?: boolean }) {
  return (
    <Link className={`nexus-brand ${light ? "is-light" : ""}`} href="/" aria-label="Nexus — início">
      <span className="nexus-symbol"><Image src="/nexus-brand.jfif" alt="" width={96} height={96} priority /></span>
      <span>NEXUS<small>automações inteligentes</small></span>
    </Link>
  );
}

