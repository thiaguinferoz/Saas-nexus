"use client";

import Link from "next/link";
import {
  ArrowRight,
  Check,
  ChatCenteredDots,
  CircleNotch,
  Clock,
  Crown,
  Lightning,
  Play,
  Sparkle,
  TrendUp,
  UsersThree,
  WhatsappLogo,
} from "@phosphor-icons/react";

const appUrl = "https://app.usenexusia.com";

const audiences = [
  ["Negócios que atendem pelo WhatsApp", "Pare de perder oportunidades enquanto sua equipe tenta dar conta de cada conversa."],
  ["Equipes que precisam ganhar escala", "Crie uma operação que responde, qualifica e encaminha sem aumentar a complexidade."],
  ["Empresas que querem previsibilidade", "Centralize processos e acompanhe o que acontece em cada etapa do atendimento."],
];

const benefits = [
  ["Responda na hora", "Atendimento inteligente 24 horas, inclusive quando sua equipe está offline.", Lightning],
  ["Converta mais conversas", "Contexto e agilidade para transformar interesse em oportunidade real.", TrendUp],
  ["Controle em um só lugar", "Visão clara da operação, regras e informações que sua equipe precisa.", CircleNotch],
];

const plans = [
  { name: "Comum", subtitle: "Auto Personalização", monthly: 600, yearly: 450, featured: false, items: ["IA configurada para sua operação", "WhatsApp oficial integrado", "Painel de gestão centralizado", "Suporte humano especializado"] },
  { name: "Personalizado", subtitle: "Acompanhamento estratégico", monthly: 1000, yearly: 750, featured: true, items: ["Tudo do plano Comum", "Personalização feita com você", "Fluxos e estratégia sob medida", "Acompanhamento prioritário"] },
];

export default function NexusLanding() {
  const [annual, setAnnual] = useState(false);
  return (
    <main className="nx">
      <nav className="nx-nav nx-shell">
        <Link href="/" className="nx-brand" aria-label="Nexus, página inicial"><span>N</span>NEXUS</Link>
        <div className="nx-nav-links"><a href="#beneficios">Benefícios</a><a href="#para-quem">Para quem é</a><a href="#planos">Planos</a></div>
        <Link className="nx-nav-cta" href={`${appUrl}/cadastro`}>Testar grátis <ArrowRight weight="bold" /></Link>
      </nav>

      <section className="nx-hero nx-shell">
        <div className="nx-hero-copy nx-reveal">
          <p className="nx-trial"><Sparkle weight="fill" /> 3 DIAS DE TESTE GRÁTIS</p>
          <h1>Seu WhatsApp.<br /><i>Seu negócio em movimento.</i></h1>
          <p className="nx-lead">A Nexus transforma cada conversa em uma oportunidade, com uma IA que atende, entende e faz sua operação avançar.</p>
          <div className="nx-actions">
            <Link className="nx-primary" href={`${appUrl}/cadastro`}>Começar 3 dias grátis <ArrowRight weight="bold" /></Link>
            <a className="nx-secondary" href="#como-funciona"><Play weight="fill" /> Ver como funciona</a>
          </div>
          <p className="nx-no-card"><Check weight="bold" /> Sem cartão de crédito. Cancele quando quiser.</p>
        </div>
        <div className="nx-orbit-scene" aria-label="Nexus conectando atendimento, inteligência e conversão">
          <div className="nx-grid" /><div className="nx-glow" /><div className="nx-ring nx-ring-a" /><div className="nx-ring nx-ring-b" />
          <div className="nx-core"><span>N</span><b>NEXUS</b><small>IA ATIVA</small></div>
          <div className="nx-node nx-node-wa"><WhatsappLogo weight="fill" /><span><b>WhatsApp</b><small>Nova mensagem</small></span><em>+1</em></div>
          <div className="nx-node nx-node-ai"><Sparkle weight="fill" /><span><b>IA Nexus</b><small>Entendeu o contexto</small></span></div>
          <div className="nx-node nx-node-sale"><TrendUp weight="bold" /><span><b>Oportunidade</b><small>Lead qualificado</small></span><em className="nx-ok">✓</em></div>
          <i className="nx-pulse nx-pulse-a" /><i className="nx-pulse nx-pulse-b" />
        </div>
      </section>

      <section className="nx-strip"><div className="nx-shell"><strong>Uma plataforma. Uma operação mais inteligente.</strong><span><Clock /> 3 dias grátis para testar sem compromisso</span></div></section>

      <section id="beneficios" className="nx-section nx-shell">
        <header className="nx-heading nx-reveal"><p>O VALOR QUE VOCÊ PERCEBE</p><h2>Menos esforço operacional.<br />Mais conversas que viram resultado.</h2></header>
        <div className="nx-benefits">{benefits.map(([title, text, Icon]) => <article className="nx-reveal" key={title as string}><div className="nx-icon"><Icon weight="duotone" /></div><h3>{title as string}</h3><p>{text as string}</p><span>0{benefits.findIndex(item => item[0] === title) + 1}</span></article>)}</div>
      </section>

      <section id="para-quem" className="nx-audience">
        <div className="nx-shell nx-audience-grid"><div className="nx-audience-copy nx-reveal"><p className="nx-kicker">PARA QUEM É A NEXUS?</p><h2>Para quem sabe que cada mensagem merece uma resposta à altura.</h2><p>Se o WhatsApp é parte importante das suas vendas ou do seu atendimento, a Nexus tira sua operação do modo reativo e coloca inteligência no centro dela.</p><Link className="nx-outline" href={`${appUrl}/cadastro`}>Experimentar agora <ArrowRight weight="bold" /></Link></div><div className="nx-audience-list">{audiences.map(([title, text], index) => <article className="nx-reveal" key={title}><b>0{index + 1}</b><div><h3>{title}</h3><p>{text}</p></div><ArrowRight /></article>)}</div></div>
      </section>

      <section id="como-funciona" className="nx-section nx-shell nx-flow">
        <header className="nx-heading nx-reveal"><p>TECNOLOGIA QUE TRABALHA POR VOCÊ</p><h2>Conecte. Configure.<br />Comece a evoluir.</h2></header>
        <div className="nx-flow-grid"><article className="nx-reveal"><span>01</span><UsersThree weight="duotone" /><h3>Conecte seu canal</h3><p>Integre o WhatsApp oficial à sua operação em poucos passos.</p></article><article className="nx-reveal"><span>02</span><ChatCenteredDots weight="duotone" /><h3>Defina sua inteligência</h3><p>Configure contexto, regras e o jeito que sua empresa conversa.</p></article><article className="nx-reveal"><span>03</span><Crown weight="duotone" /><h3>Veja a operação acontecer</h3><p>A Nexus cuida das conversas enquanto você foca em crescer.</p></article></div>
      </section>

      <section id="planos" className="nx-pricing">
        <div className="nx-shell"><header className="nx-pricing-head nx-reveal"><p className="nx-kicker">PLANOS SIMPLES. RESULTADOS GRANDES.</p><h2>Escolha o ritmo da sua evolução.</h2><p>Comece com 3 dias gratuitos. Depois, fique com o plano que acompanha sua operação.</p><div className="nx-toggle" role="group" aria-label="Período de contrato"><button className={!annual ? "active" : ""} onClick={() => setAnnual(false)}>Contrato mensal</button><button className={annual ? "active" : ""} onClick={() => setAnnual(true)}>Contrato anual <small>Economize 25%</small></button></div></header><div className="nx-plan-grid">{plans.map(plan => { const price = annual ? plan.yearly : plan.monthly; return <article className={`nx-plan ${plan.featured ? "featured" : ""} nx-reveal`} key={plan.name}>{plan.featured && <p className="nx-popular">MAIS ESCOLHIDO</p>}<div><h3>{plan.name}</h3><p>{plan.subtitle}</p></div><div className="nx-price"><small>R$</small><strong>{price}</strong><span>/mês</span></div><p className="nx-contract">{annual ? "no contrato anual" : "no contrato mensal"}</p><ul>{plan.items.map(item => <li key={item}><Check weight="bold" />{item}</li>)}</ul><Link className={plan.featured ? "nx-primary" : "nx-plan-button"} href={`${appUrl}/cadastro`}>Começar teste grátis <ArrowRight weight="bold" /></Link></article>})}</div><p className="nx-price-note"><Sparkle weight="fill" /> Todo plano começa com 3 dias de teste grátis.</p></div>
      </section>

      <section className="nx-final nx-shell"><div className="nx-final-orb" /><p className="nx-trial"><Sparkle weight="fill" /> 3 DIAS DE TESTE GRÁTIS</p><h2>A próxima conversa pode<br /><i>mudar seu negócio.</i></h2><p>Coloque a Nexus para trabalhar hoje e descubra o que sua operação pode fazer com mais inteligência.</p><Link className="nx-primary" href={`${appUrl}/cadastro`}>Quero testar a Nexus <ArrowRight weight="bold" /></Link></section>
      <footer className="nx-footer"><div className="nx-shell"><Link href="/" className="nx-brand"><span>N</span>NEXUS</Link><p>Inteligência que aproxima empresas e pessoas.</p><small>© 2026 Nexus. Todos os direitos reservados.</small></div></footer>
    </main>
  );
}

import { useState } from "react";
