import Link from "next/link";
import type { ReactNode } from "react";

type LegalSection = {
  title: string;
  content: ReactNode;
};

export function LegalPage({
  eyebrow,
  title,
  summary,
  sections,
}: {
  eyebrow: string;
  title: string;
  summary: string;
  sections: LegalSection[];
}) {
  return (
    <main className="legal-page">
      <header className="legal-header">
        <div className="legal-shell legal-nav">
          <Link href="/" className="nx-brand" aria-label="Nexus, página inicial">
            <span>N</span>NEXUS
          </Link>
          <Link href="/" className="legal-back">Voltar ao início</Link>
        </div>
      </header>

      <section className="legal-hero">
        <div className="legal-shell">
          <p>{eyebrow}</p>
          <h1>{title}</h1>
          <strong>Versão vigente desde 22 de setembro de 2026</strong>
          <span>{summary}</span>
        </div>
      </section>

      <div className="legal-shell legal-layout">
        <aside className="legal-index" aria-label="Índice do documento">
          <b>NESTE DOCUMENTO</b>
          <nav>
            {sections.map((section, index) => (
              <a href={`#secao-${index + 1}`} key={section.title}>
                <span>{String(index + 1).padStart(2, "0")}</span>{section.title}
              </a>
            ))}
          </nav>
        </aside>

        <article className="legal-content">
          {sections.map((section, index) => (
            <section id={`secao-${index + 1}`} key={section.title}>
              <small>{String(index + 1).padStart(2, "0")}</small>
              <h2>{section.title}</h2>
              <div>{section.content}</div>
            </section>
          ))}

          <div className="legal-contact">
            <strong>Ficou com alguma dúvida?</strong>
            <p>Fale com a Nexus pelo e-mail <a href="mailto:contato@usenexusia.com">contato@usenexusia.com</a>.</p>
          </div>
        </article>
      </div>

      <footer className="legal-footer">
        <div className="legal-shell">
          <span>© 2026 Nexus. Todos os direitos reservados.</span>
          <nav><Link href="/termos-de-servico">Termos de Serviço</Link><Link href="/politica-de-privacidade">Política de Privacidade</Link></nav>
        </div>
      </footer>
    </main>
  );
}
