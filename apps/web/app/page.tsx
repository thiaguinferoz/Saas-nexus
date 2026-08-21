import Link from "next/link";
import { ArrowRight, Brain, ChartLineUp, Check, CirclesThreePlus, FlowArrow, Lightning, Play, ShieldCheck, Sparkle, WhatsappLogo } from "@phosphor-icons/react/dist/ssr";
import { AiDemo } from "./shared/ai-demo";
import { NexusLogo } from "./shared/nexus-logo";

const outcomes = [
  { value: "24/7", label: "presença para seus clientes" },
  { value: "1 fluxo", label: "para toda a operação" },
  { value: "100%", label: "WhatsApp oficial" },
];

const features = [
  { icon: Brain, number: "01", title: "Entende antes de responder", text: "Interpreta intenção, contexto, áudio e imagem para construir respostas coerentes." },
  { icon: FlowArrow, number: "02", title: "Segue as regras do negócio", text: "Horários, linguagem, serviços e encaminhamentos configurados no seu painel." },
  { icon: CirclesThreePlus, number: "03", title: "Conecta sua operação", text: "Automatiza rotinas e integra sistemas sem mudar a experiência do seu cliente." },
  { icon: ChartLineUp, number: "04", title: "Evolui com os dados", text: "Acompanhe conversas, gargalos e oportunidades em uma visão centralizada." },
];

export default function Home() {
  const appUrl = "https://app.usenexusia.com";

  return (
    <main className="nexus-site">
      <nav className="nav shell">
        <NexusLogo />
        <div className="nav-links"><a href="#solucao">Solução</a><a href="#demonstracao">A IA em ação</a><a href="#como-funciona">Como funciona</a></div>
        <div className="nav-actions"><Link className="text-button" href={`${appUrl}/login`}>Entrar</Link><Link className="button small" href={`${appUrl}/cadastro`}>Criar conta <ArrowRight /></Link></div>
      </nav>

      <section className="hero nexus-hero shell">
        <div className="hero-copy">
          <span className="eyebrow"><Sparkle weight="fill" /> 3 dias grátis para começar</span>
          <h1>Converse melhor.<br/><em>Automatize além.</em></h1>
          <p>A Nexus transforma seu WhatsApp em uma operação inteligente: entende cada mensagem, responde com contexto e conecta clientes, equipe e processos.</p>
          <div className="hero-actions"><Link className="button" href={`${appUrl}/cadastro`}>Começar 3 dias grátis <ArrowRight weight="bold" /></Link><a className="secondary-button" href="#demonstracao"><Play weight="fill" /> Ver a IA funcionando</a></div>
          <div className="hero-proof"><span><Check weight="bold" /> Sem cobrança no teste</span><span><Check weight="bold" /> API oficial</span><span><Check weight="bold" /> Suporte humano</span></div>
        </div>
        <div className="nexus-visual" aria-label="Ecossistema de automação Nexus">
          <div className="orbit orbit-one"/><div className="orbit orbit-two"/>
          <div className="core-logo"><div className="core-n">N</div><small>NEXUS</small><span>IA OPERANDO</span></div>
          <div className="signal-card signal-whatsapp"><WhatsappLogo weight="fill"/><span><b>WhatsApp</b>nova conversa</span><i>+1</i></div>
          <div className="signal-card signal-ai"><Brain weight="duotone"/><span><b>IA contextual</b>intenção identificada</span></div>
          <div className="signal-card signal-flow"><Lightning weight="fill"/><span><b>Automação</b>ação executada</span><i className="done">✓</i></div>
          <div className="data-stream stream-a"/><div className="data-stream stream-b"/><div className="data-stream stream-c"/>
        </div>
      </section>

      <section className="outcomes"><div className="shell outcomes-grid"><p>Uma nova camada de inteligência para empresas que valorizam cada conversa.</p>{outcomes.map(item => <div key={item.value}><strong>{item.value}</strong><span>{item.label}</span></div>)}</div></section>

      <section className="feature-section shell" id="solucao">
        <div className="section-heading"><span className="eyebrow">Muito além de respostas automáticas</span><h2>Uma inteligência conectada a tudo que move seu negócio.</h2><p>O cliente sente uma conversa simples. Por trás dela, a Nexus coordena contexto, regras e ações em tempo real.</p></div>
        <div className="feature-grid">{features.map(({ icon: Icon, number, title, text }) => <article key={number}><span className="feature-number">{number}</span><div className="feature-icon"><Icon weight="duotone" /></div><h3>{title}</h3><p>{text}</p><a href="#demonstracao">Ver exemplo <ArrowRight /></a></article>)}</div>
      </section>

      <AiDemo />

      <section id="como-funciona" className="nexus-steps">
        <div className="shell steps-layout"><div><span className="eyebrow light">Da ideia à operação</span><h2>Comece rápido.<br/>Escale no seu ritmo.</h2><p>Teste a Nexus gratuitamente por 3 dias. Para continuar depois do período gratuito, basta assinar o plano no painel.</p><Link className="button white" href={`${appUrl}/cadastro`}>Iniciar meu teste grátis <ArrowRight /></Link></div><ol><li><b>01</b><span><strong>Confirme seu e-mail</strong>Seu período gratuito de 3 dias começa após a confirmação.</span></li><li><b>02</b><span><strong>Configure empresa e WhatsApp</strong>Defina as regras da IA e conecte seu número oficial.</span></li><li><b>03</b><span><strong>Assine para continuar</strong>Ao final do teste, escolha o plano e mantenha sua operação ativa.</span></li></ol></div>
      </section>

      <section className="nexus-cta shell"><div className="cta-glow"/><ShieldCheck weight="duotone"/><span className="eyebrow">Sua próxima evolução começa aqui</span><h2>Conecte sua empresa ao futuro das conversas.</h2><p>Use gratuitamente por 3 dias. Depois, assine o plano para continuar com a automação ativa.</p><Link className="button" href={`${appUrl}/cadastro`}>Começar 3 dias grátis <ArrowRight /></Link></section>

      <footer><div className="shell"><NexusLogo/><p>Automações inteligentes que conectam negócios e pessoas.</p><span>© 2026 Nexus. Todos os direitos reservados.</span></div></footer>
    </main>
  );
}
