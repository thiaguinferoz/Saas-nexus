"use client";

import { useEffect, useRef, useState } from "react";
import { Armchair, CalendarCheck, ChatCircleDots, ClockCountdown, Pause, Play, Sparkle, WhatsappLogo } from "@phosphor-icons/react";

const scenarios = [
  {
    id: "atendimento", label: "Atendimento", icon: ChatCircleDots,
    title: "Entende produto, disponibilidade e entrega.",
    detail: "A Nexus combina imagem e texto, identifica o item e consulta as informações da empresa antes de responder.",
    messages: [
      { side: "client", kind: "image", text: "Olá! Vocês têm esse modelo na cor preta? Conseguem entregar hoje?", time: "14:31" },
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
    detail: "O áudio é transcrito, o plano é identificado e o valor mensal vem da fonte oficial configurada pela empresa.",
    messages: [
      { side: "client", kind: "audio", text: "Bom dia, quanto que é o plano anual básico do site de vocês?", duration: "0:05", audioSrc: "/audio/demo-plano-anual.ogg", time: "16:24" },
      { side: "system", kind: "transcript", text: "Plano Comum anual • intenção: consultar preço", time: "" },
      { side: "ai", text: "Bom dia! O Plano Comum, na contratação anual, custa R$ 450 por mês. O pagamento pode ser feito à vista ou parcelado em até 12 vezes.", time: "16:24" },
    ], badge: "Áudio compreendido em 2,1 s", signals: ["Áudio transcrito", "Plano identificado", "Preço mensal confirmado"],
  },
];

function formatAudioTime(seconds: number) {
  if (!Number.isFinite(seconds) || seconds < 0) return "0:00";
  const minutes = Math.floor(seconds / 60);
  return `${minutes}:${Math.floor(seconds % 60).toString().padStart(2, "0")}`;
}

function AudioMessage({ src, fallbackDuration, transcript }: { src: string; fallbackDuration: string; transcript: string }) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const progress = duration > 0 ? currentTime / duration : 0;

  useEffect(() => () => audioRef.current?.pause(), []);

  async function togglePlayback() {
    const audio = audioRef.current;
    if (!audio) return;
    if (audio.paused) {
      try { await audio.play(); } catch { setPlaying(false); }
    } else {
      audio.pause();
    }
  }

  return (
    <>
      <audio
        className="demo-audio-source"
        ref={audioRef}
        src={src}
        preload="metadata"
        onLoadedMetadata={(event) => setDuration(event.currentTarget.duration)}
        onTimeUpdate={(event) => setCurrentTime(event.currentTarget.currentTime)}
        onPlay={() => setPlaying(true)}
        onPause={() => setPlaying(false)}
        onEnded={(event) => { event.currentTarget.currentTime = 0; setPlaying(false); setCurrentTime(0); }}
      />
      <div className={`audio-bubble ${playing ? "is-playing" : ""}`}>
        <button type="button" aria-label={playing ? "Pausar exemplo de áudio" : "Reproduzir exemplo de áudio"} aria-pressed={playing} onClick={togglePlayback}>
          {playing ? <Pause weight="fill" /> : <Play weight="fill" />}
        </button>
        <div className="audio-wave" role="progressbar" aria-label="Progresso do áudio" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(progress * 100)}>
          {Array.from({ length: 25 }, (_, bar) => <i className={bar / 24 <= progress ? "played" : ""} key={bar}/>) }
        </div>
        <small>{duration > 0 ? formatAudioTime(playing || currentTime > 0 ? currentTime : duration) : fallbackDuration}</small>
      </div>
      <em>“{transcript}”</em>
    </>
  );
}

export function AiDemo() {
  const [active, setActive] = useState(scenarios[0]);
  return (
    <section className="demo-section shell" id="demonstracao">
      <div className="demo-intro">
        <span className="eyebrow"><Sparkle weight="fill" /> IA aplicada à conversa real</span>
        <h2>Veja como a Nexus transforma conversas em negócios.</h2>
        <p>Não é um menu engessado. A IA interpreta a mensagem, respeita suas regras e sabe o momento certo de envolver uma pessoa.</p>
        <div className="demo-tabs" role="tablist" aria-label="Exemplos de funcionamento">
          {scenarios.map((scenario) => { const Icon = scenario.icon; return <button key={scenario.id} role="tab" aria-selected={active.id === scenario.id} className={active.id === scenario.id ? "active" : ""} onClick={() => setActive(scenario)}><Icon />{scenario.label}</button>; })}
        </div>
        <div className="demo-copy" key={active.id}><span>{active.badge}</span><h3>{active.title}</h3><p>{active.detail}</p><div className="signal-list">{active.signals.map((signal) => <small key={signal}>✓ {signal}</small>)}</div></div>
      </div>
      <div className="demo-device">
        <div className="demo-camera" aria-hidden="true" />
        <div className="demo-top"><span className="mini-logo">N</span><div><strong>Nexus IA</strong><small><i /> online agora</small></div><WhatsappLogo weight="fill" /></div>
        <div className="demo-chat" key={`${active.id}-chat`}>
          <div className="privacy-note">As mensagens são protegidas e processadas com segurança</div>
        {active.messages.map((message, index) => message.kind === "transcript" ? <div className="transcript-chip" key={index}><Sparkle weight="fill"/><span><b>Áudio compreendido</b>{message.text}</span></div> : <div className={`demo-message ${message.side} ${message.kind ?? "text"}`} key={index}>{message.side === "ai" && <b><Sparkle weight="fill" /> NEXUS</b>}{message.kind === "image" && <div className="image-preview"><span className="product-glow"/><Armchair weight="duotone"/><i>imagem analisada</i></div>}{message.kind === "audio" && "audioSrc" in message ? <AudioMessage src={message.audioSrc ?? "/audio/demo-plano-anual.ogg"} fallbackDuration={message.duration ?? "0:05"} transcript={message.text}/> : <span>{message.text}</span>}<time>{message.time}{message.side === "ai" ? " ✓✓" : ""}</time></div>)}
          <div className="ai-status"><span><i /><i /><i /></span> IA analisou contexto, horário e intenção</div>
        </div>
        <div className="demo-input">Digite uma mensagem... <span>➤</span></div>
      </div>
    </section>
  );
}
