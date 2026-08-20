"use client";

import { useState } from "react";
import { CalendarCheck, ChatCircleDots, ClockCountdown, Sparkle, WhatsappLogo } from "@phosphor-icons/react";

const scenarios = [
  {
    id: "atendimento", label: "Atendimento", icon: ChatCircleDots,
    title: "Entende produto, disponibilidade e entrega.",
    detail: "A Nexus combina imagem e texto, identifica o item e consulta as informações da empresa antes de responder.",
    messages: [
      { side: "client", kind: "image", media: "🪑", text: "Olá! Vocês têm esse modelo na cor preta? Conseguem entregar hoje?", time: "14:31" },
      { side: "ai", text: "Olá! Temos esse modelo na cor preta. Para o seu CEP, a entrega pode ser feita hoje até as 19h. Quer que eu separe uma unidade?", time: "14:31" },
    ], badge: "Imagem + estoque + entrega", signals: ["Produto identificado", "Estoque consultado", "Prazo verificado"],
  },
  {
    id: "agendamento", label: "Agendamento", icon: CalendarCheck,
    title: "Conduz o cliente sem perguntas repetidas.",
    detail: "A intenção é reconhecida, as informações já enviadas são preservadas e a IA solicita apenas o dado que falta.",
    messages: [
      { side: "client", text: "Gostaria de agendar uma visita técnica amanhã à tarde.", time: "10:08" },
      { side: "ai", text: "Claro! Temos disponibilidade às 14h30 ou às 16h. Qual horário fica melhor para você?", time: "10:08" },
      { side: "client", text: "Pode ser às 16h.", time: "10:09" },
      { side: "ai", text: "Perfeito! Sua visita técnica ficou agendada para amanhã. A confirmação será enviada por aqui. 😊", time: "10:09" },
    ], badge: "Agendamento concluído", signals: ["Serviço identificado", "Agenda consultada", "Confirmação enviada"],
  },
  {
    id: "fallback", label: "Fora do horário", icon: ClockCountdown,
    title: "Mantém o atendimento mesmo quando a equipe saiu.",
    detail: "A Nexus informa o horário correto, coleta o necessário e deixa o próximo passo preparado para sua equipe.",
    messages: [
      { side: "client", text: "Oi! Preciso alterar os dados do meu contrato. Alguém consegue me ajudar agora?", time: "23:47" },
      { side: "ai", text: "Olá! Nossa equipe encerrou o atendimento de hoje e retorna amanhã às 8h. Posso adiantar sua solicitação: qual dado você precisa alterar?", time: "23:47" },
    ], badge: "Continuidade fora do horário", signals: ["Horário verificado", "Assunto identificado", "Próximo passo definido"],
  },
  {
    id: "audio", label: "Áudio e preço", icon: WhatsappLogo,
    title: "O cliente fala. A Nexus entende e responde.",
    detail: "O áudio é transcrito, o serviço é identificado e o valor vem da fonte oficial configurada pela empresa.",
    messages: [
      { side: "client", kind: "audio", text: "Oi, tudo bem? Eu queria saber quanto custa o serviço de instalação.", duration: "0:07", time: "11:22" },
      { side: "system", kind: "transcript", text: "Serviço de instalação • intenção: consultar preço", time: "" },
      { side: "ai", text: "Olá! A instalação padrão custa R$ 180,00. Se você me informar o modelo e o local, verifico se há algum adicional.", time: "11:22" },
    ], badge: "Áudio compreendido em 2,1 s", signals: ["Áudio transcrito", "Serviço identificado", "Preço confirmado"],
  },
];

export function AiDemo() {
  const [active, setActive] = useState(scenarios[0]);
  return (
    <section className="demo-section shell" id="demonstracao">
      <div className="demo-intro">
        <span className="eyebrow"><Sparkle weight="fill" /> IA aplicada à conversa real</span>
        <h2>Veja a Nexus pensando junto com a sua operação.</h2>
        <p>Não é um menu engessado. A IA interpreta a mensagem, respeita suas regras e sabe o momento certo de envolver uma pessoa.</p>
        <div className="demo-tabs" role="tablist" aria-label="Exemplos de funcionamento">
          {scenarios.map((scenario) => { const Icon = scenario.icon; return <button key={scenario.id} role="tab" aria-selected={active.id === scenario.id} className={active.id === scenario.id ? "active" : ""} onClick={() => setActive(scenario)}><Icon />{scenario.label}</button>; })}
        </div>
        <div className="demo-copy" key={active.id}><span>{active.badge}</span><h3>{active.title}</h3><p>{active.detail}</p><div className="signal-list">{active.signals.map((signal) => <small key={signal}>✓ {signal}</small>)}</div></div>
      </div>
      <div className="demo-device">
        <div className="demo-top"><span className="mini-logo">N</span><div><strong>Nexus IA</strong><small><i /> online agora</small></div><WhatsappLogo weight="fill" /></div>
        <div className="demo-chat" key={`${active.id}-chat`}>
          <div className="privacy-note">As mensagens são protegidas e processadas com segurança</div>
          {active.messages.map((message, index) => message.kind === "transcript" ? <div className="transcript-chip" key={index}><Sparkle weight="fill"/><span><b>Áudio compreendido</b>{message.text}</span></div> : <div className={`demo-message ${message.side} ${message.kind ?? "text"}`} key={index}>{message.side === "ai" && <b><Sparkle weight="fill" /> NEXUS</b>}{message.kind === "image" && <div className="image-preview"><span>{"media" in message ? message.media : ""}</span><i>imagem analisada</i></div>}{message.kind === "audio" ? <div className="audio-bubble"><button aria-label="Reproduzir exemplo de áudio">▶</button><div className="audio-wave">{Array.from({ length: 25 }, (_, bar) => <i key={bar}/>)}</div><small>{"duration" in message ? message.duration : ""}</small></div> : <span>{message.text}</span>}{message.kind === "audio" && <em>“{message.text}”</em>}<time>{message.time}{message.side === "ai" ? " ✓✓" : ""}</time></div>)}
          <div className="ai-status"><span><i /><i /><i /></span> IA analisou contexto, horário e intenção</div>
        </div>
        <div className="demo-input">Digite uma mensagem... <span>➤</span></div>
      </div>
    </section>
  );
}
