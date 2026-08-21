"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowSquareOut, BellSimple, BookOpen, Buildings, CalendarDots, CaretRight, ChartLineUp, ChatCircleDots, Check, Clock, CreditCard, FileCsv, Flask, Gear, Lightning, LinkSimple, ListChecks, LockKey, PaperPlaneTilt, RocketLaunch, ShieldCheck, SignOut, Sparkle, Target, UploadSimple, UserPlus, WhatsappLogo } from "@phosphor-icons/react";
import { NexusLogo } from "../shared/nexus-logo";
import { AdminPanel } from "./admin-panel";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/v1";
const dayLabels: Record<string, string> = { monday: "Segunda", tuesday: "Terça", wednesday: "Quarta", thursday: "Quinta", friday: "Sexta", saturday: "Sábado", sunday: "Domingo" };
const defaultHours = Object.fromEntries(Object.keys(dayLabels).map((day) => [day, { enabled: !["saturday", "sunday"].includes(day), opens_at: "09:00", closes_at: "18:00" }]));

type DayHours = { enabled: boolean; opens_at: string; closes_at: string };
type Settings = { company_name: string; timezone: string; assistant: { tone: string; instructions: string; human_handoff_message: string }; business_hours: Record<string, DayHours> };
const demoSettings: Settings = { company_name: "Minha empresa", timezone: "America/Sao_Paulo", assistant: { tone: "acolhedor", instructions: "Responda com clareza, seja breve e encaminhe para uma pessoa quando não tiver segurança.", human_handoff_message: "Vou chamar uma pessoa da nossa equipe para continuar com você." }, business_hours: defaultHours };
const tabs = [
  { id: "overview", label: "Visão geral", icon: Gear },
  { id: "company", label: "Empresa", icon: Buildings },
  { id: "catalog", label: "Catálogo e preços", icon: FileCsv },
  { id: "knowledge", label: "Base de conhecimento", icon: BookOpen },
  { id: "assistant", label: "Personalidade da IA", icon: ChatCircleDots },
  { id: "goals", label: "Objetivos e regras", icon: Target },
  { id: "hours", label: "Horários e equipe", icon: Clock },
  { id: "test", label: "Laboratório de testes", icon: Flask },
  { id: "whatsapp", label: "WhatsApp", icon: WhatsappLogo },
  { id: "support", label: "Suporte", icon: ChatCircleDots },
  { id: "billing", label: "Plano e cobrança", icon: CreditCard },
];
const adminTab = { id: "admin", label: "Administração Nexus", icon: ShieldCheck };
function readCookie(name: string) { return document.cookie.split("; ").find((row) => row.startsWith(`${name}=`))?.split("=")[1] ?? ""; }

export function DashboardShell() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState("overview");
  const [settings, setSettings] = useState<Settings>(demoSettings);
  const [version, setVersion] = useState(1);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [demoMode, setDemoMode] = useState(false);
  const [whatsappConnected, setWhatsappConnected] = useState(false);
  const [error, setError] = useState("");
  const [platformAdmin, setPlatformAdmin] = useState(false);
  const [profileName, setProfileName] = useState("");

  useEffect(() => {
    async function load() {
      try {
        const [response, meResponse] = await Promise.all([
          fetch(`${API_URL}/tenant/settings`, { credentials: "include" }),
          fetch(`${API_URL}/auth/me`, { credentials: "include" }),
        ]);
        if (response.status === 401 || meResponse.status === 401) { router.replace("/login"); return; }
        if (!response.ok || !meResponse.ok) throw new Error("Não foi possível carregar as configurações.");
        const [body, me] = await Promise.all([response.json(), meResponse.json()]);
        setSettings({ ...body.payload, business_hours: { ...defaultHours, ...body.payload.business_hours } }); setVersion(body.version);
        setPlatformAdmin(Boolean(me.user?.is_platform_admin));
        setProfileName(me.user?.full_name ?? "");
      } catch (reason) {
        if (reason instanceof TypeError) setDemoMode(true); else setError(reason instanceof Error ? reason.message : "Erro inesperado.");
      } finally { setLoading(false); }
    }
    load();
  }, [router]);

  const completed = useMemo(() => [settings.company_name.trim().length > 1, Object.values(settings.business_hours).some((day) => day.enabled), settings.assistant.instructions.trim().length >= 20, whatsappConnected], [settings, whatsappConnected]);
  const progress = completed.filter(Boolean).length * 25;
  function updateAssistant(field: keyof Settings["assistant"], value: string) { setSettings((current) => ({ ...current, assistant: { ...current.assistant, [field]: value } })); }
  function updateHours(day: string, value: Partial<DayHours>) { setSettings((current) => ({ ...current, business_hours: { ...current.business_hours, [day]: { ...current.business_hours[day], ...value } } })); }

  async function save(event?: FormEvent) {
    event?.preventDefault(); setSaving(true); setSaved(false); setError("");
    if (demoMode) { setTimeout(() => { setSaving(false); setSaved(true); }, 450); return; }
    try {
      const response = await fetch(`${API_URL}/tenant/settings`, { method: "PUT", credentials: "include", headers: { "Content-Type": "application/json", "If-Match": String(version), "X-CSRF-Token": decodeURIComponent(readCookie("csrf_token")) }, body: JSON.stringify(settings) });
      const body = await response.json();
      if (response.status === 409) throw new Error("As configurações foram alteradas em outra sessão. Atualize a página antes de salvar novamente.");
      if (!response.ok) throw new Error(typeof body.detail === "string" ? body.detail : "Não foi possível salvar.");
      setVersion(body.version); setSettings(body.payload); setSaved(true);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Erro inesperado."); } finally { setSaving(false); }
  }
  async function logout() { await fetch(`${API_URL}/auth/logout`, { method: "POST", credentials: "include", headers: { "X-CSRF-Token": decodeURIComponent(readCookie("csrf_token")) } }).catch(() => null); router.push("/login"); }

  const visibleTabs = useMemo(() => platformAdmin ? [...tabs, adminTab] : tabs, [platformAdmin]);
  const activeLabel = visibleTabs.find((tab) => tab.id === activeTab)?.label ?? "Visão geral";
  const companyInitial = settings.company_name.trim().charAt(0).toUpperCase() || "N";
  const moduleContent = activeTab === "catalog" ? <CatalogPanel demoMode={demoMode}/> : activeTab === "knowledge" ? <KnowledgePanel/> : activeTab === "goals" ? <GoalsPanel/> : activeTab === "test" ? <TestLabPanel goTo={setActiveTab}/> : activeTab === "support" ? <SupportPanel demoMode={demoMode}/> : activeTab === "admin" && platformAdmin ? <AdminPanel/> : null;
  const moduleDescriptions: Record<string, string> = {
    catalog: "Organize serviços, produtos e valores sem depender de planilhas durante cada conversa.",
    knowledge: "Centralize documentos, perguntas frequentes e páginas que a IA pode consultar.",
    goals: "Escolha o que a IA deve alcançar e em quais situações ela precisa chamar sua equipe.",
    test: "Simule conversas, confira as fontes utilizadas e publique somente quando estiver seguro.",
    support: "Abra solicitações, acompanhe o atendimento e fale diretamente com a equipe Nexus.",
    admin: "Acompanhe clientes, assinaturas, conexões e solicitações em toda a plataforma.",
  };

  if (moduleContent) {
    return <main className="dashboard nexus-dashboard client-portal"><aside className="sidebar"><NexusLogo/><div className="workspace-card"><span>{companyInitial}</span><div><small>Workspace</small><strong>{settings.company_name}</strong></div><i/></div><small className="sidebar-label">MENU PRINCIPAL</small><nav>{visibleTabs.map(({ id, label, icon: Icon }) => <button className={activeTab === id ? "active" : ""} key={id} onClick={() => setActiveTab(id)}><Icon weight={activeTab === id ? "fill" : "regular"}/><span>{label}</span>{activeTab === id && <i/>}</button>)}</nav><button type="button" className="sidebar-support" onClick={() => setActiveTab("support")}><Sparkle weight="fill"/><span><strong>Precisa de ajuda?</strong>Fale com a equipe Nexus.</span><CaretRight/></button><button className="logout-button" onClick={logout}><SignOut/> Sair</button><div className="sidebar-footer">Configuração v{version} {demoMode && "• demonstração local"}</div></aside><section className="dash-main"><div className="dashboard-topbar"><div className="portal-breadcrumb"><span>Painel</span><CaretRight/><strong>{activeLabel}</strong></div><div><button aria-label="Notificações"><BellSimple/><i/></button><span className="profile-copy"><strong>{profileName || settings.company_name}</strong><small>{platformAdmin ? "Administrador Nexus" : "Gestor do workspace"}</small></span><b>{companyInitial}</b></div></div><header className="dash-head"><div><small>{activeTab === "admin" ? "CENTRAL DA PLATAFORMA" : "CENTRAL DE PERSONALIZAÇÃO"}</small><h1>{activeLabel}</h1><p>{moduleDescriptions[activeTab]}</p></div><div className="dash-actions"><span className="status-pill"><i/>{activeTab === "admin" ? "Acesso protegido" : "Configuração self-service"}</span></div></header>{demoMode && <div className="demo-banner"><Sparkle weight="fill"/> Modo de demonstração: explore como seus clientes irão personalizar a própria IA.</div>}{moduleContent}</section></main>;
  }

  return <main className="dashboard nexus-dashboard client-portal"><aside className="sidebar"><NexusLogo/><div className="workspace-card"><span>{companyInitial}</span><div><small>Workspace</small><strong>{settings.company_name}</strong></div><i/></div><small className="sidebar-label">MENU PRINCIPAL</small><nav>{visibleTabs.map(({ id, label, icon: Icon }) => <button className={activeTab === id ? "active" : ""} key={id} onClick={() => setActiveTab(id)}><Icon weight={activeTab === id ? "fill" : "regular"}/><span>{label}</span>{activeTab === id && <i/>}</button>)}</nav><button type="button" className="sidebar-support" onClick={() => setActiveTab("support")}><Sparkle weight="fill"/><span><strong>Precisa de ajuda?</strong>Fale com a equipe Nexus.</span><CaretRight/></button><button className="logout-button" onClick={logout}><SignOut/> Sair</button><div className="sidebar-footer">Configuração v{version} {demoMode && "• demonstração local"}</div></aside><section className="dash-main"><div className="dashboard-topbar"><div className="portal-breadcrumb"><span>Painel</span><CaretRight/><strong>{activeLabel}</strong></div><div><button aria-label="Notificações"><BellSimple/><i/></button><span className="profile-copy"><strong>{profileName || settings.company_name}</strong><small>{platformAdmin ? "Administrador Nexus" : "Gestor do workspace"}</small></span><b>{companyInitial}</b></div></div><header className="dash-head"><div><small>{activeTab === "overview" ? "RESUMO DA OPERAÇÃO" : "CONFIGURAÇÕES DO PAINEL"}</small><h1>{activeTab === "overview" ? `Olá, ${settings.company_name}.` : activeLabel}</h1><p>{activeTab === "overview" ? "Tudo o que você precisa para acompanhar e preparar seu atendimento inteligente." : "Personalize esta etapa. A Nexus aplica as mudanças no atendimento da sua empresa."}</p></div><div className="dash-actions"><span className="status-pill"><i/>{progress === 100 ? "Operação pronta" : `${progress}% configurado`}</span>{!["overview", "billing", "whatsapp"].includes(activeTab) && <button className="button small" onClick={() => save()} disabled={saving}>{saving ? "Salvando..." : saved ? "Alterações salvas" : "Salvar alterações"}</button>}</div></header>{demoMode && <div className="demo-banner"><Sparkle weight="fill"/> Modo de demonstração: explore o painel enquanto a API não está conectada.</div>}{error && <div className="panel-error">{error}</div>}{loading ? <div className="dashboard-loading">Preparando seu painel...</div> : <>{activeTab === "overview" && <Overview progress={progress} completed={completed} goTo={setActiveTab}/>} {activeTab === "company" && <form className="settings-panel" onSubmit={save}><PanelTitle icon={Buildings} title="Dados da empresa" text="Essas informações identificam seu negócio em todo o atendimento."/><div className="settings-grid"><label>Nome da empresa<input value={settings.company_name} onChange={(e) => setSettings({ ...settings, company_name: e.target.value })}/></label><label>Fuso horário<select value={settings.timezone} onChange={(e) => setSettings({ ...settings, timezone: e.target.value })}><option value="America/Sao_Paulo">Brasília — São Paulo</option><option value="America/Manaus">Manaus</option><option value="America/Fortaleza">Fortaleza</option><option value="America/Recife">Recife</option></select></label></div></form>} {activeTab === "hours" && <section className="settings-panel"><PanelTitle icon={CalendarDots} title="Horários de atendimento" text="A IA usa estes horários para responder corretamente quando sua equipe estiver disponível ou ausente."/><div className="hours-list">{Object.entries(dayLabels).map(([day, label]) => { const value = settings.business_hours[day]; return <div className={`hours-row ${value.enabled ? "enabled" : ""}`} key={day}><label className="day-toggle"><input type="checkbox" checked={value.enabled} onChange={(e) => updateHours(day, { enabled: e.target.checked })}/><i/><strong>{label}</strong></label>{value.enabled ? <div className="time-range"><input type="time" value={value.opens_at} onChange={(e) => updateHours(day, { opens_at: e.target.value })}/><span>até</span><input type="time" value={value.closes_at} onChange={(e) => updateHours(day, { closes_at: e.target.value })}/></div> : <span className="closed-label">Fechado</span>}</div>})}</div></section>} {activeTab === "assistant" && <section className="settings-panel"><PanelTitle icon={ChatCircleDots} title="Comportamento da IA" text="Defina como a Nexus deve representar sua empresa nas conversas."/><div className="settings-stack"><label>Tom de voz<select value={settings.assistant.tone} onChange={(e) => updateAssistant("tone", e.target.value)}><option value="acolhedor">Acolhedor e próximo</option><option value="profissional">Profissional e objetivo</option><option value="descontraido">Descontraído</option><option value="consultivo">Consultivo</option></select></label><label>Instruções principais<textarea rows={8} maxLength={12000} value={settings.assistant.instructions} onChange={(e) => updateAssistant("instructions", e.target.value)} placeholder="Exemplo: responda de forma breve, nunca invente preços e peça o CEP antes de informar o prazo de entrega."/><small>{settings.assistant.instructions.length}/12.000 caracteres</small></label><label>Mensagem para atendimento humano<textarea rows={3} maxLength={500} value={settings.assistant.human_handoff_message} onChange={(e) => updateAssistant("human_handoff_message", e.target.value)}/></label></div><AssistantPreview settings={settings}/></section>} {activeTab === "whatsapp" && <WhatsAppPanel demoMode={demoMode} onConnectionChange={setWhatsappConnected}/>} {activeTab === "billing" && <BillingPanel demoMode={demoMode}/>}</>}</section></main>;
}

function PanelTitle({ icon: Icon, title, text }: { icon: typeof Buildings; title: string; text: string }) { return <div className="panel-title"><span><Icon weight="duotone"/></span><div><h2>{title}</h2><p>{text}</p></div></div>; }
function Overview({ progress, completed, goTo }: { progress: number; completed: boolean[]; goTo: (tab: string) => void }) {
  const items = [{ icon: Buildings, title: "Empresa configurada", text: "Nome e fuso horário", tab: "company" }, { icon: Clock, title: "Horários definidos", text: "Disponibilidade da equipe", tab: "hours" }, { icon: Sparkle, title: "IA personalizada", text: "Tom, regras e fallback", tab: "assistant" }, { icon: WhatsappLogo, title: "WhatsApp oficial", text: "Conexão segura pela YCloud", tab: "whatsapp" }];
  const metrics = [{ icon: PaperPlaneTilt, label: "Mensagens este mês", value: "0", detail: "Conecte o WhatsApp para iniciar", featured: true }, { icon: ChatCircleDots, label: "Conversas ativas", value: "0", detail: "Em tempo real" }, { icon: UserPlus, label: "Novos contatos", value: "0", detail: "Últimos 30 dias" }, { icon: ChartLineUp, label: "Taxa de resposta", value: "—", detail: "Sem dados ainda" }];
  return <section className="overview-reference"><div className="overview-main"><div className="metric-grid">{metrics.map(({ icon: Icon, label, value, detail, featured }) => <article className={featured ? "featured" : ""} key={label}><span><Icon weight="duotone"/>{label}</span><strong>{value}</strong><small>{detail}</small></article>)}</div><section className="quick-actions-card"><div className="overview-section-title"><span><Lightning weight="fill"/></span><div><h2>Ações rápidas</h2><p>Continue sua configuração sem procurar pelo menu.</p></div></div><div className="quick-actions"><button className="primary" onClick={() => goTo("whatsapp")}><WhatsappLogo weight="fill"/><span><strong>Conectar WhatsApp</strong><small>Vincule seu número oficial</small></span><CaretRight/></button><button onClick={() => goTo("assistant")}><Sparkle weight="fill"/><span><strong>Configurar a IA</strong><small>Defina tom e instruções</small></span><CaretRight/></button><button onClick={() => goTo("hours")}><CalendarDots/><span><strong>Ajustar horários</strong><small>Informe quando sua equipe atende</small></span><CaretRight/></button></div></section></div><aside className="overview-side"><section className="setup-compact"><div className="setup-compact-head"><div><span>ATIVAÇÃO</span><h2>Prepare sua operação</h2></div><strong>{progress}%</strong></div><div className="progress"><i style={{ width: `${progress}%` }}/></div><div className="setup-compact-list">{items.map(({ icon: Icon, title, text, tab }, index) => <button key={title} onClick={() => goTo(tab)} className={completed[index] ? "done" : ""}><i>{completed[index] ? <Check weight="bold"/> : <Icon/>}</i><span><strong>{title}</strong><small>{text}</small></span><CaretRight/></button>)}</div></section><section className="activity-card"><div className="overview-section-title"><span><Clock/></span><div><h2>Atividade recente</h2><p>Atualizações da sua conta</p></div></div><ol><li><i className="purple"><Sparkle weight="fill"/></i><span><strong>Conta Nexus criada</strong><small>Seu ambiente está pronto</small></span><time>Hoje</time></li><li><i className="cyan"><Gear/></i><span><strong>Configuração iniciada</strong><small>{progress}% da ativação concluída</small></span><time>Agora</time></li></ol></section></aside></section>;
}

type CatalogItemSummary = { id?: string; name: string; category: string; price: string; status: string };

function CatalogPanel({ demoMode }: { demoMode: boolean }) {
  const [fileName, setFileName] = useState("");
  const [analyzed, setAnalyzed] = useState(false);
  const [items, setItems] = useState<CatalogItemSummary[]>([
    { name: "Consultoria inicial", category: "Serviços", price: "R$ 180,00", status: "Disponível" },
    { name: "Instalação padrão", category: "Serviços", price: "R$ 350,00", status: "Disponível" },
    { name: "Plano de manutenção", category: "Planos", price: "R$ 129,90", status: "Sob consulta" },
  ]);
  useEffect(() => {
    if (demoMode) return;
    fetch(`${API_URL}/catalog/items`, { credentials: "include" })
      .then(async (response) => response.ok ? response.json() : [])
      .then((body: Array<{ id: string; name: string; category?: string; price?: string; currency: string; is_active: boolean }>) => {
        setItems(body.map((item) => ({
          id: item.id,
          name: item.name,
          category: item.category || "Sem categoria",
          price: item.price == null ? "Sob consulta" : new Intl.NumberFormat("pt-BR", { style: "currency", currency: item.currency || "BRL" }).format(Number(item.price)),
          status: item.is_active ? "Disponível" : "Inativo",
        })));
      }).catch(() => null);
  }, [demoMode]);
  return <section className="personalization-view"><div className="automation-explainer"><span><Lightning weight="fill"/></span><div><strong>Catálogo padrão para qualquer tipo de negócio</strong><p>O cliente envia a planilha, confirma o significado das colunas e publica. Produtos, serviços e valores ficam estruturados no banco e isolados por empresa.</p></div><b>AUTOMÁTICO</b></div><div className="personalization-grid catalog-layout"><article className="module-card import-card"><div className="module-card-head"><span><UploadSimple/></span><div><h2>Importar catálogo</h2><p>CSV ou Excel com produtos, serviços e valores.</p></div></div><label className={`upload-zone ${fileName ? "has-file" : ""}`}><input type="file" accept=".csv,.xlsx,.xls" onChange={(event) => { setFileName(event.target.files?.[0]?.name ?? ""); setAnalyzed(false); }}/><FileCsv weight="duotone"/><strong>{fileName || "Arraste a planilha ou selecione um arquivo"}</strong><small>{fileName ? "Arquivo selecionado. Agora analise as colunas." : "Até 20 MB • CSV, XLS ou XLSX"}</small></label><button className="module-primary-button" disabled={!fileName} onClick={() => setAnalyzed(true)}><Sparkle weight="fill"/> Analisar colunas automaticamente</button>{analyzed && <div className="mapping-preview"><div><span>Coluna encontrada</span><span>Usar como</span></div><p><b>Nome</b><em>Nome do item <Check/></em></p><p><b>Valor</b><em>Preço <Check/></em></p><p><b>Categoria</b><em>Tipo do item <Check/></em></p><small>O cliente revisa este mapeamento antes de publicar.</small></div>}</article><article className="module-card catalog-card"><div className="module-card-head"><span><FileCsv/></span><div><h2>Catálogo publicado</h2><p>{demoMode ? "Exemplo genérico da estrutura padrão." : `${items.length} itens disponíveis para a IA.`}</p></div><button className="ghost-action">+ Novo item</button></div><div className="catalog-table"><div className="catalog-table-head"><span>Item</span><span>Categoria</span><span>Valor</span><span>Status</span></div>{items.length ? items.map((item) => <div className="catalog-table-row" key={item.id || item.name}><strong>{item.name}</strong><span>{item.category}</span><b>{item.price}</b><em>{item.status}</em></div>) : <div className="catalog-empty">Seu catálogo ainda está vazio. Importe uma planilha ou crie o primeiro item.</div>}</div><div className="structured-note"><LockKey/><span><strong>Valores sempre exatos</strong>Preços são consultados diretamente no catálogo estruturado, e não na memória do modelo.</span></div></article></div></section>;
}

function KnowledgePanel() {
  const [sourceType, setSourceType] = useState("files");
  const sources = [{ name: "Políticas comerciais.pdf", type: "Documento", detail: "18 trechos indexados", status: "Pronto" }, { name: "Perguntas frequentes", type: "FAQ", detail: "12 respostas", status: "Pronto" }, { name: "Página de serviços", type: "Site", detail: "Atualizado hoje", status: "Sincronizado" }];
  return <section className="personalization-view"><div className="automation-explainer knowledge"><span><BookOpen weight="fill"/></span><div><strong>Uma biblioteca exclusiva para cada empresa</strong><p>Arquivos e textos são processados em segundo plano, separados pelo tenant e utilizados somente quando forem relevantes para a pergunta.</p></div><b>ISOLADO POR CLIENTE</b></div><div className="source-picker"><button className={sourceType === "files" ? "active" : ""} onClick={() => setSourceType("files")}><UploadSimple/><strong>Arquivos</strong><small>PDF, DOCX e planilhas</small></button><button className={sourceType === "faq" ? "active" : ""} onClick={() => setSourceType("faq")}><ListChecks/><strong>Perguntas frequentes</strong><small>Respostas validadas</small></button><button className={sourceType === "url" ? "active" : ""} onClick={() => setSourceType("url")}><LinkSimple/><strong>Páginas do site</strong><small>Conteúdo sincronizado</small></button></div><div className="personalization-grid knowledge-layout"><article className="module-card source-builder"><div className="module-card-head"><span>{sourceType === "files" ? <UploadSimple/> : sourceType === "faq" ? <ListChecks/> : <LinkSimple/>}</span><div><h2>{sourceType === "files" ? "Adicionar documentos" : sourceType === "faq" ? "Criar pergunta frequente" : "Importar página"}</h2><p>A Nexus valida antes de disponibilizar para a IA.</p></div></div>{sourceType === "files" && <label className="upload-zone"><input type="file" accept=".pdf,.doc,.docx,.csv,.xlsx"/><BookOpen weight="duotone"/><strong>Selecione os arquivos da empresa</strong><small>O processamento acontece automaticamente</small></label>}{sourceType === "faq" && <div className="source-form"><label>Pergunta<input placeholder="Ex.: Quais formas de pagamento vocês aceitam?"/></label><label>Resposta validada<textarea rows={5} placeholder="Escreva a resposta oficial da empresa."/></label></div>}{sourceType === "url" && <div className="source-form"><label>Endereço da página<input placeholder="https://empresa.com.br/servicos"/></label><div className="sync-choice"><Check/> Verificar atualizações automaticamente uma vez por dia</div></div>}<button className="module-primary-button"><PlusIcon/> Adicionar à base</button></article><article className="module-card source-list-card"><div className="module-card-head"><span><BookOpen/></span><div><h2>Fontes disponíveis</h2><p>Conteúdo que a IA pode consultar agora.</p></div></div><div className="source-list">{sources.map((source) => <div key={source.name}><i>{source.type === "Documento" ? <BookOpen/> : source.type === "FAQ" ? <ListChecks/> : <LinkSimple/>}</i><span><strong>{source.name}</strong><small>{source.type} • {source.detail}</small></span><b><Check/> {source.status}</b></div>)}</div></article></div></section>;
}

function PlusIcon() { return <span aria-hidden="true">+</span>; }

function GoalsPanel() {
  const goalOptions = [{ id: "questions", title: "Responder dúvidas", text: "Consulta catálogo, documentos e FAQs", icon: BookOpen }, { id: "leads", title: "Qualificar oportunidades", text: "Coleta dados importantes antes do contato", icon: Target }, { id: "quotes", title: "Preparar orçamentos", text: "Usa valores exatos do catálogo", icon: FileCsv }, { id: "appointments", title: "Agendar atendimento", text: "Encaminha para agenda ou equipe", icon: CalendarDots }, { id: "orders", title: "Consultar solicitações", text: "Aciona integrações autorizadas", icon: Lightning }, { id: "handoff", title: "Chamar um humano", text: "Transfere conversas sensíveis ou complexas", icon: UserPlus }];
  const [enabledGoals, setEnabledGoals] = useState(["questions", "leads", "quotes", "handoff"]);
  function toggleGoal(id: string) { setEnabledGoals((current) => current.includes(id) ? current.filter((goal) => goal !== id) : [...current, id]); }
  return <section className="personalization-view"><div className="automation-explainer goals"><span><Target weight="fill"/></span><div><strong>O cliente escolhe resultados, não constrói workflows</strong><p>A Nexus transforma as escolhas abaixo em regras e ferramentas disponíveis para a IA. Integrações especiais continuam como serviço adicional.</p></div><b>SEM CÓDIGO</b></div><article className="module-card"><div className="module-card-head"><span><Target/></span><div><h2>O que a IA deve fazer?</h2><p>Ative apenas os objetivos que fazem sentido para esta operação.</p></div><strong className="selection-count">{enabledGoals.length} ativos</strong></div><div className="goal-grid">{goalOptions.map(({ id, title, text, icon: Icon }) => { const active = enabledGoals.includes(id); return <button key={id} className={active ? "active" : ""} aria-pressed={active} onClick={() => toggleGoal(id)}><i><Icon weight={active ? "fill" : "duotone"}/></i><span><strong>{title}</strong><small>{text}</small></span><em>{active ? <Check/> : "+"}</em></button>; })}</div></article><div className="personalization-grid rules-layout"><article className="module-card rules-card"><div className="module-card-head"><span><ListChecks/></span><div><h2>Regras obrigatórias</h2><p>Informações que devem orientar todas as conversas.</p></div></div><div className="source-form"><label>A IA sempre deve<textarea rows={5} defaultValue="Confirmar os dados antes de concluir uma solicitação. Informar quando um valor estiver sujeito a avaliação."/></label><label>A IA nunca deve<textarea rows={5} defaultValue="Inventar preços, prometer prazos não cadastrados ou responder sobre assuntos que não pertencem à empresa."/></label></div></article><article className="module-card handoff-card"><div className="module-card-head"><span><UserPlus/></span><div><h2>Encaminhamento humano</h2><p>Situações que interrompem a automação.</p></div></div><div className="handoff-tags"><button className="active"><Check/> Cliente pediu uma pessoa</button><button className="active"><Check/> Reclamação ou cancelamento</button><button className="active"><Check/> IA sem informação segura</button><button>+ Adicionar condição</button></div><div className="structured-note"><UserPlus/><span><strong>A equipe recebe o contexto</strong>A conversa e o motivo do encaminhamento acompanham a transferência.</span></div></article></div></section>;
}

function TestLabPanel({ goTo }: { goTo: (tab: string) => void }) {
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState([{ role: "client", text: "Quanto custa a instalação padrão?" }, { role: "ai", text: "A instalação padrão custa R$ 350,00. Se quiser, posso verificar os horários disponíveis para você." }]);
  function runTest(event: FormEvent) { event.preventDefault(); const clean = message.trim(); if (!clean) return; const answer = clean.toLowerCase().includes("preço") || clean.toLowerCase().includes("custa") ? "Encontrei o valor no catálogo publicado. A consultoria inicial custa R$ 180,00." : "Posso ajudar com informações da empresa, valores, disponibilidade ou encaminhar você para a equipe."; setMessages((current) => [...current, { role: "client", text: clean }, { role: "ai", text: answer }]); setMessage(""); }
  return <section className="personalization-view"><div className="lab-layout"><article className="module-card conversation-lab"><div className="module-card-head"><span><Flask/></span><div><h2>Simulador de conversa</h2><p>Teste como a IA responderá antes de publicar.</p></div><b className="lab-status"><i/> AMBIENTE DE TESTE</b></div><div className="lab-chat">{messages.map((item, index) => <div className={`lab-message ${item.role}`} key={`${item.role}-${index}`}><small>{item.role === "ai" ? "NEXUS IA" : "CLIENTE"}</small><p>{item.text}</p>{item.role === "ai" && <span><BookOpen/> Fonte: Catálogo publicado</span>}</div>)}</div><form className="lab-composer" onSubmit={runTest}><input value={message} onChange={(event) => setMessage(event.target.value)} placeholder="Digite uma pergunta como se fosse um cliente..."/><button aria-label="Enviar teste"><PaperPlaneTilt weight="fill"/></button></form></article><aside className="lab-side"><article className="module-card readiness-card"><span>PRONTO PARA PUBLICAR?</span><h2>Revisão da versão</h2><div><p><i><Check/></i><span><strong>Empresa configurada</strong><small>Identidade e horários</small></span></p><p><i><Check/></i><span><strong>Catálogo estruturado</strong><small>3 itens neste exemplo</small></span></p><p><i><Check/></i><span><strong>Fontes processadas</strong><small>Documentos e FAQs disponíveis</small></span></p><p className="attention"><i>!</i><span><strong>WhatsApp pendente</strong><small>Conecte antes de ativar</small></span></p></div><button className="publish-button" onClick={() => goTo("whatsapp")}><RocketLaunch weight="fill"/> Preparar ativação</button></article><article className="module-card version-card"><div><span>VERSÃO ATUAL</span><strong>Rascunho 1.0</strong></div><b>Alterações protegidas</b><p>Publicar cria uma versão recuperável. A operação anterior permanece disponível para restauração.</p><button onClick={() => goTo("catalog")}>Revisar catálogo <CaretRight/></button></article></aside></div></section>;
}

type SupportTicketSummary = { id: string; category: string; priority: string; status: string; subject: string; created_at: string };

function SupportPanel({ demoMode }: { demoMode: boolean }) {
  const [category, setCategory] = useState("support");
  const [subject, setSubject] = useState("");
  const [message, setMessage] = useState("");
  const [channel, setChannel] = useState("platform");
  const [contact, setContact] = useState("");
  const [tickets, setTickets] = useState<SupportTicketSummary[]>([]);
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState("");

  useEffect(() => {
    if (demoMode) return;
    fetch(`${API_URL}/support/tickets`, { credentials: "include" })
      .then(async (response) => response.ok ? response.json() : [])
      .then(setTickets).catch(() => null);
  }, [demoMode]);

  function chooseCustomPlan() {
    setCategory("custom_plan");
    setSubject("Quero falar sobre o plano personalizado");
    setFeedback("");
  }

  async function submitTicket(event: FormEvent) {
    event.preventDefault();
    if (!subject.trim() || !message.trim() || (channel !== "platform" && !contact.trim())) return;
    setBusy(true); setFeedback("");
    const payload = { category, subject: subject.trim(), message: message.trim(), preferred_channel: channel, contact_value: contact.trim() || null };
    try {
      let ticket: SupportTicketSummary;
      if (demoMode) {
        ticket = { id: `demo-${Date.now()}`, category, priority: category === "custom_plan" ? "high" : "normal", status: "open", subject: payload.subject, created_at: new Date().toISOString() };
      } else {
        const response = await fetch(`${API_URL}/support/tickets`, { method: "POST", credentials: "include", headers: { "Content-Type": "application/json", "X-CSRF-Token": decodeURIComponent(readCookie("csrf_token")) }, body: JSON.stringify(payload) });
        const body = await response.json();
        if (!response.ok) throw new Error(typeof body.detail === "string" ? body.detail : "Não foi possível enviar a solicitação.");
        ticket = body;
      }
      setTickets((current) => [ticket, ...current]);
      setMessage(""); setContact(""); setFeedback(category === "custom_plan" ? "Pedido prioritário enviado. Um especialista Nexus entrará em contato pelo canal escolhido." : "Solicitação enviada. Você pode acompanhar o andamento nesta página.");
    } catch (reason) { setFeedback(reason instanceof Error ? reason.message : "Não foi possível enviar a solicitação."); } finally { setBusy(false); }
  }

  const statusLabels: Record<string, string> = { open: "Aberto", in_progress: "Em atendimento", resolved: "Resolvido" };
  return <section className="personalization-view support-view"><div className="support-hero"><span><ChatCircleDots weight="duotone"/></span><div><small>CENTRAL DE SUPORTE</small><h2>A Nexus está ao seu lado</h2><p>Tire dúvidas sobre a plataforma ou solicite atendimento especializado sem sair do painel.</p></div><b>ATENDIMENTO DIRETO</b></div><div className="support-layout"><form className="module-card support-form" onSubmit={submitTicket}><div className="module-card-head"><span><PaperPlaneTilt/></span><div><h2>Nova solicitação</h2><p>Conte o que precisa e escolha como prefere receber o retorno.</p></div></div><div className="support-category"><button type="button" className={category === "support" ? "active" : ""} onClick={() => setCategory("support")}><ChatCircleDots/><span><strong>Suporte da plataforma</strong><small>Configuração, uso ou problemas</small></span></button><button type="button" className={category === "custom_plan" ? "active custom" : "custom"} onClick={chooseCustomPlan}><Sparkle weight="fill"/><span><strong>Plano personalizado</strong><small>Fale direto com um especialista</small></span></button></div><label>Assunto<input maxLength={200} value={subject} onChange={(event) => setSubject(event.target.value)} placeholder="Como podemos ajudar?" required/></label><label>Detalhes<textarea rows={6} value={message} onChange={(event) => setMessage(event.target.value)} placeholder="Descreva sua necessidade com o máximo de contexto." required/></label><div className="support-contact-grid"><label>Canal de retorno<select value={channel} onChange={(event) => setChannel(event.target.value)}><option value="platform">Pela plataforma</option><option value="email">E-mail</option><option value="whatsapp">WhatsApp</option><option value="phone">Telefone</option></select></label>{channel !== "platform" && <label>Seu contato<input maxLength={320} value={contact} onChange={(event) => setContact(event.target.value)} placeholder={channel === "email" ? "voce@empresa.com" : "(00) 00000-0000"} required/></label>}</div><button className="module-primary-button" disabled={busy}>{busy ? "Enviando..." : category === "custom_plan" ? "Solicitar contato prioritário" : "Enviar ao suporte"}</button>{feedback && <div className="support-feedback"><Check weight="bold"/> {feedback}</div>}</form><aside className="support-side"><article className="module-card custom-contact-card"><span><Sparkle weight="fill"/></span><small>EXCLUSIVO DO PLANO PERSONALIZADO</small><h2>Converse com quem vai desenhar sua solução</h2><p>Integrações com ERP, regras exclusivas e fluxos sob medida recebem acompanhamento direto da equipe Nexus.</p><ul><li><Check/> Solicitação com prioridade alta</li><li><Check/> Canal de retorno escolhido por você</li><li><Check/> Contexto registrado no seu workspace</li></ul><button type="button" onClick={chooseCustomPlan}>Quero falar com um especialista <CaretRight/></button></article><article className="module-card ticket-history"><div className="module-card-head"><span><ListChecks/></span><div><h2>Suas solicitações</h2><p>Acompanhe os contatos deste workspace.</p></div></div>{tickets.length ? <div className="ticket-list">{tickets.slice(0, 5).map((ticket) => <div key={ticket.id}><i className={ticket.priority === "high" ? "high" : ""}/><span><strong>{ticket.subject}</strong><small>{ticket.category === "custom_plan" ? "Plano personalizado" : "Suporte"} • {new Date(ticket.created_at).toLocaleDateString("pt-BR")}</small></span><b>{statusLabels[ticket.status] || ticket.status}</b></div>)}</div> : <div className="ticket-empty"><ChatCircleDots/><strong>Nenhuma solicitação ainda</strong><small>Quando precisar, sua conversa com a Nexus começa aqui.</small></div>}</article></aside></div></section>;
}

function AssistantPreview({ settings }: { settings: Settings }) { return <aside className="assistant-preview"><span>PRÉVIA DO ATENDIMENTO</span><div className="preview-bubble client">Olá! Vocês conseguem me ajudar?</div><div className="preview-bubble ai"><b><Sparkle weight="fill"/> NEXUS</b>Olá! Claro, será um prazer ajudar. Pode me contar o que você precisa?</div><small>Tom selecionado: {settings.assistant.tone}</small></aside>; }

type WhatsAppConnection = { waba_id: string; phone_number: string; phone_number_id?: string; display_name?: string; quality_rating?: string; status: string };
type EmbeddedSession = { app_id: string; configuration_id: string; state: string };

function WhatsAppPanel({ demoMode, onConnectionChange }: { demoMode: boolean; onConnectionChange: (connected: boolean) => void }) {
  const [connection, setConnection] = useState<WhatsAppConnection | null>(null);
  const [phone, setPhone] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  useEffect(() => {
    if (demoMode) return;
    fetch(`${API_URL}/whatsapp/connection`, { credentials: "include" }).then(async (response) => response.ok ? response.json() : null).then((body) => { setConnection(body); onConnectionChange(body?.status === "connected"); }).catch(() => null);
  }, [demoMode, onConnectionChange]);

  async function finishOnboarding(session: EmbeddedSession, data: { waba_id: string; phone_number_id?: string }) {
    const response = await fetch(`${API_URL}/whatsapp/onboarding/complete`, { method: "POST", credentials: "include", headers: { "Content-Type": "application/json", "X-CSRF-Token": decodeURIComponent(readCookie("csrf_token")) }, body: JSON.stringify({ state: session.state, waba_id: data.waba_id, phone_number_id: data.phone_number_id, phone_number: phone }) });
    const body = await response.json();
    if (!response.ok) throw new Error(typeof body.detail === "string" ? body.detail : "Não foi possível concluir a conexão.");
    setConnection(body); onConnectionChange(true); setMessage(""); setBusy(false);
  }

  async function connect() {
    setBusy(true); setMessage("");
    if (demoMode) { setTimeout(() => { const demo = { waba_id: "demo", phone_number: phone || "+55 13 99999-0000", display_name: "Nexus Demonstração", quality_rating: "GREEN", status: "connected" }; setConnection(demo); onConnectionChange(true); setBusy(false); }, 700); return; }
    if (!/^\+[1-9]\d{7,14}$/.test(phone)) { setMessage("Informe o número com país e DDD, por exemplo: +5513999990000."); setBusy(false); return; }
    try {
      const response = await fetch(`${API_URL}/whatsapp/onboarding/session`, { method: "POST", credentials: "include", headers: { "X-CSRF-Token": decodeURIComponent(readCookie("csrf_token")) } });
      const session = await response.json() as EmbeddedSession & { detail?: string };
      if (!response.ok) throw new Error(session.detail || "Não foi possível iniciar a autorização.");
      const fbWindow = window as typeof window & { FB?: { init: (options: Record<string, unknown>) => void; login: (callback: (response: unknown) => void, options: Record<string, unknown>) => void } };
      if (!fbWindow.FB) throw new Error("O serviço de autorização da Meta ainda está carregando. Tente novamente em alguns segundos.");
      fbWindow.FB.init({ appId: session.app_id, cookie: true, xfbml: true, version: "v23.0" });
      const receiveMessage = (event: MessageEvent) => {
        if (!event.origin.endsWith("facebook.com")) return;
        try {
          const data = typeof event.data === "string" ? JSON.parse(event.data) : event.data;
          if (data?.type === "WA_EMBEDDED_SIGNUP" && data?.event === "FINISH") {
            window.removeEventListener("message", receiveMessage);
            finishOnboarding(session, { waba_id: data.data.waba_id, phone_number_id: data.data.phone_number_id }).catch((reason) => { setMessage(reason instanceof Error ? reason.message : "Erro inesperado."); setBusy(false); });
          }
        } catch { /* mensagens externas que não pertencem ao onboarding */ }
      };
      window.addEventListener("message", receiveMessage);
      fbWindow.FB.login(() => undefined, { config_id: session.configuration_id, response_type: "code", override_default_response_type: true, extras: { setup: {} } });
      setMessage("Conclua a autorização na janela da Meta. Esta tela será atualizada automaticamente.");
    } catch (reason) { setMessage(reason instanceof Error ? reason.message : "Erro inesperado."); setBusy(false); }
  }

  useEffect(() => {
    if (document.getElementById("facebook-jssdk")) return;
    const script = document.createElement("script"); script.id = "facebook-jssdk"; script.async = true; script.defer = true; script.crossOrigin = "anonymous"; script.src = "https://connect.facebook.net/pt_BR/sdk.js"; document.body.appendChild(script);
  }, []);

  const connected = connection?.status === "connected";
  return <section className="whatsapp-view"><div className="whatsapp-hero"><div className="whatsapp-orbit"><i/><i/><i/></div><div className="whatsapp-hero-copy"><span><WhatsappLogo weight="fill"/> CANAL OFICIAL</span><h2>{connected ? "WhatsApp conectado e pronto." : "Conecte seu número. A Nexus cuida do restante."}</h2><p>{connected ? "Seu canal está vinculado ao tenant correto e pode receber o workflow inteligente da Nexus." : "A autorização acontece no ambiente seguro da Meta. Você não precisa compartilhar senha, token ou acesso ao n8n."}</p>{connected ? <div className="connected-number"><i><WhatsappLogo weight="fill"/></i><span><small>{connection.display_name || "Sua empresa"}</small><strong>{connection.phone_number}</strong></span><b><Check weight="bold"/> CONECTADO</b></div> : <div className="connect-form"><label>Número que será conectado<input value={phone} onChange={(event) => setPhone(event.target.value)} placeholder="+5513999990000"/></label><button className="button whatsapp-button" onClick={connect} disabled={busy}>{busy ? "Aguardando autorização..." : demoMode ? "Simular conexão" : "Conectar com a Meta"}<ArrowSquareOut/></button></div>}{message && <small className="whatsapp-message">{message}</small>}</div></div><aside className="whatsapp-guide"><span>COMO FUNCIONA</span><ol><li className={connected ? "done" : "current"}><i>{connected ? <Check/> : "1"}</i><div><strong>Autorize sua empresa</strong><small>Login e permissões diretamente na Meta</small></div></li><li className={connected ? "done" : ""}><i>{connected ? <Check/> : "2"}</i><div><strong>Vinculação automática</strong><small>YCloud e Nexus identificam seu número</small></div></li><li className={connected ? "done" : ""}><i>{connected ? <Check/> : "3"}</i><div><strong>Ativação do atendimento</strong><small>O workflow recebe as configurações do painel</small></div></li></ol><div className="whatsapp-safe"><LockKey weight="duotone"/><span><strong>Seus acessos ficam protegidos</strong>A Nexus não solicita sua senha do WhatsApp ou Facebook.</span></div></aside></section>;
}

type BillingState = {
  status: string;
  trial_ends_at: string | null;
  trial_days_remaining: number;
  access_allowed: boolean;
  cancel_at_period_end: boolean;
  management_available: boolean;
};

function BillingPanel({ demoMode }: { demoMode: boolean }) {
  const [billing, setBilling] = useState<BillingState | null>(null);
  const [loadState, setLoadState] = useState<"loading" | "ready" | "error" | "demo">(demoMode ? "demo" : "loading");
  const [loadError, setLoadError] = useState("");
  const [reloadToken, setReloadToken] = useState(0);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    let cancelled = false;
    if (demoMode) {
      setBilling(null);
      setLoadError("");
      setLoadState("demo");
      return;
    }

    setLoadError("");
    setLoadState("loading");
    fetch(`${API_URL}/billing/subscription`, { credentials: "include" })
      .then(async (response) => {
        const body = await response.json().catch(() => null) as (BillingState & { detail?: string }) | null;
        if (!response.ok) throw new Error(body?.detail || "Não foi possível consultar sua assinatura.");
        return body;
      })
      .then((body) => {
        if (cancelled) return;
        setBilling(body?.status ? body : null);
        setLoadState("ready");
      })
      .catch((reason) => {
        if (cancelled) return;
        setBilling(null);
        setLoadError(reason instanceof Error ? reason.message : "Não foi possível consultar sua assinatura.");
        setLoadState("error");
      });

    return () => { cancelled = true; };
  }, [demoMode, reloadToken]);

  async function openBilling(endpoint: "checkout" | "portal") {
    setBusy(true); setMessage("");
    if (demoMode) { setTimeout(() => { setBusy(false); setMessage("O checkout abrirá aqui assim que as chaves do gateway forem configuradas."); }, 450); return; }
    try {
      const response = await fetch(`${API_URL}/billing/${endpoint}`, { method: "POST", credentials: "include", headers: { "X-CSRF-Token": decodeURIComponent(readCookie("csrf_token")) } });
      const body = await response.json();
      if (!response.ok) throw new Error(typeof body.detail === "string" ? body.detail : "Não foi possível abrir a cobrança.");
      if (typeof body.url !== "string" || !body.url) throw new Error("O gateway não retornou um endereço de pagamento válido.");
      window.location.assign(body.url);
    } catch (reason) { setMessage(reason instanceof Error ? reason.message : "Erro inesperado."); setBusy(false); }
  }

  const status = billing?.status ?? "none";
  const paid = loadState === "ready" && status === "active";
  const trialing = loadState === "ready" && status === "trialing" && Boolean(billing?.access_allowed);
  const trialEndTimestamp = billing?.trial_ends_at ? Date.parse(billing.trial_ends_at) : Number.NaN;
  const endedTrialStoredAsIncomplete = status === "incomplete" && Number.isFinite(trialEndTimestamp) && trialEndTimestamp <= Date.now();
  const expiredTrial = loadState === "ready" && !billing?.access_allowed && (status === "trialing" || endedTrialStoredAsIncomplete);
  const paymentIssue = status === "past_due" || status === "unpaid";
  const cancelScheduled = loadState === "ready" && Boolean(billing?.cancel_at_period_end);
  const managementAvailable = loadState === "ready" && Boolean(billing?.management_available);
  const trialDays = billing?.trial_days_remaining ?? 0;
  const trialLabel = trialDays === 1 ? "1 dia grátis restante" : `${trialDays} dias grátis restantes`;

  let badge = "Plano não assinado";
  let headline = "Assinatura mensal com checkout seguro.";
  let description = "Confira o valor e as condições vigentes no checkout antes de confirmar o pagamento.";
  let actionLabel = "Assinar plano";
  let actionEndpoint: "checkout" | "portal" = "checkout";

  if (loadState === "loading") {
    badge = "Consultando plano";
    headline = "Consultando sua assinatura.";
    description = "Estamos confirmando o período gratuito e a situação de pagamento da sua conta.";
    actionLabel = "Consultando...";
  } else if (loadState === "error") {
    badge = "Status indisponível";
    headline = "Não foi possível consultar seu plano.";
    description = `${loadError} Nenhuma situação de teste ou cobrança foi presumida.`;
    actionLabel = "Tentar novamente";
  } else if (loadState === "demo") {
    badge = "Modo de demonstração";
    headline = "Assinatura mensal com checkout seguro.";
    description = "Na conta ativa, esta área confirma o teste gratuito e abre o checkout do gateway sem expor seus dados financeiros à Nexus.";
    actionLabel = "Conhecer o checkout";
  } else if (paid) {
    badge = cancelScheduled ? "Cancelamento agendado" : "Assinatura ativa";
    headline = cancelScheduled ? "Sua assinatura continua ativa por enquanto." : "Sua assinatura mensal está ativa.";
    description = cancelScheduled
      ? "O acesso permanece ativo até o encerramento do período atual. Gerencie a assinatura no portal seguro do gateway."
      : "Seu pagamento está confirmado. Você pode gerenciar a assinatura no portal seguro do gateway.";
    actionLabel = "Gerenciar assinatura";
    actionEndpoint = "portal";
  } else if (trialing) {
    badge = managementAvailable ? "Assinatura configurada" : trialLabel;
    headline = managementAvailable ? "Sua assinatura já está configurada." : "Seu teste grátis está em andamento.";
    description = managementAvailable
      ? "Seu teste grátis continua ativo, e a primeira cobrança será feita após o término do teste conforme as condições confirmadas no checkout."
      : "Você pode usar todos os recursos por 3 dias. Assine o plano mensal para manter a IA e as automações ativas depois desse período.";
    actionLabel = managementAvailable ? "Gerenciar assinatura" : "Assinar agora e continuar";
    actionEndpoint = managementAvailable ? "portal" : "checkout";
  } else if (expiredTrial) {
    badge = "Teste encerrado";
    headline = "Seu período gratuito terminou.";
    description = managementAvailable
      ? "Abra o portal seguro para consultar a assinatura e as opções disponíveis."
      : "Assine o plano mensal pelo checkout seguro para reativar a IA e as automações.";
  } else if (status === "past_due") {
    badge = "Pagamento pendente";
    headline = "Regularize sua assinatura mensal.";
    description = "Abra o portal seguro do gateway para conferir a pendência e atualizar a forma de pagamento.";
    actionLabel = "Regularizar pagamento";
    actionEndpoint = "portal";
  } else if (status === "unpaid") {
    badge = "Pagamento não confirmado";
    headline = "Atualize os dados da assinatura.";
    description = "Abra o portal seguro do gateway para revisar a cobrança e a forma de pagamento.";
    actionLabel = "Revisar pagamento";
    actionEndpoint = "portal";
  } else if (status === "canceled") {
    badge = "Assinatura cancelada";
    headline = "Assine novamente quando quiser continuar.";
    description = managementAvailable
      ? "Abra o portal seguro para consultar a assinatura e as opções disponíveis."
      : "Uma nova assinatura mensal pode ser iniciada pelo checkout seguro. Confira o valor e as condições antes de confirmar.";
    actionLabel = managementAvailable ? "Gerenciar cobrança" : "Assinar novamente";
  } else if (status === "incomplete") {
    badge = "Checkout não concluído";
    headline = "Conclua sua assinatura mensal.";
    description = managementAvailable
      ? "Abra o portal seguro para consultar a assinatura e as opções disponíveis."
      : "Inicie um novo checkout seguro e revise o valor e as condições antes da confirmação.";
    actionLabel = managementAvailable ? "Gerenciar cobrança" : "Continuar assinatura";
  } else if (status !== "none" && status !== "pending") {
    badge = "Situação a confirmar";
    headline = "Confira sua assinatura no checkout seguro.";
  }

  const trialStepDone = trialing || expiredTrial || paid || paymentIssue || status === "canceled";
  const trialStepDetail = loadState === "loading"
    ? "Consultando período gratuito..."
    : loadState === "error"
      ? "Situação temporariamente indisponível"
      : loadState === "demo"
        ? "Exibido na conta ativa"
        : trialing
          ? trialLabel
          : paid || paymentIssue || status === "canceled"
            ? "Período inicial concluído"
            : expiredTrial
              ? "Período gratuito encerrado"
              : "Nenhum período ativo encontrado";
  const subscriptionStepDetail = loadState === "loading"
    ? "Consultando assinatura..."
    : loadState === "error"
      ? "Situação temporariamente indisponível"
      : trialing && managementAvailable
        ? "Configurada; primeira cobrança após o teste"
        : paid
        ? cancelScheduled ? "Ativa; cancelamento agendado" : "Pagamento confirmado"
        : status === "past_due"
          ? "Pagamento pendente"
          : status === "unpaid"
            ? "Pagamento não confirmado"
            : status === "canceled"
              ? "Cancelada; você pode assinar novamente"
              : "Contratação pelo checkout seguro";

  if (managementAvailable) {
    if (actionEndpoint === "checkout") actionLabel = "Gerenciar cobrança";
    actionEndpoint = "portal";
  }

  function handlePrimaryAction() {
    if (loadState === "error") {
      setMessage("");
      setReloadToken((current) => current + 1);
      return;
    }
    void openBilling(actionEndpoint);
  }

  return (
    <section className="billing-view">
      <div className="billing-plan-card">
        <div className="billing-orb"/>
        <div className="billing-plan-head">
          <span><Sparkle weight="fill"/> PLANO NEXUS</span>
          <strong className={paid || trialing ? "active" : "pending"}>{badge}</strong>
        </div>
        <h2>{headline}</h2>
        <p>{description}</p>
        {trialing && billing?.trial_ends_at && <div className="trial-deadline"><Clock weight="duotone"/><span><strong>Teste válido até</strong>{new Intl.DateTimeFormat("pt-BR", { dateStyle: "long", timeStyle: "short" }).format(new Date(billing.trial_ends_at))}</span></div>}
        {cancelScheduled && <div className="billing-account-notice"><Clock weight="duotone"/><span><strong>Cancelamento agendado</strong>{paid || trialing ? "O acesso permanece ativo até o fim do período atual." : "O gateway informa encerramento ao fim do período atual."}</span></div>}
        <div className="plan-features"><span><Check weight="bold"/> Painel e configurações da IA</span><span><Check weight="bold"/> Workflow padrão multi-tenant</span><span><Check weight="bold"/> Conexão oficial com a YCloud</span><span><Check weight="bold"/> Monitoramento e atualizações</span></div>
        <button className="button" onClick={handlePrimaryAction} disabled={busy || loadState === "loading"}>{busy ? "Abrindo..." : actionLabel}<CaretRight/></button>
        {message && <small className="billing-message">{message}</small>}
      </div>
      <aside className="billing-side">
        <div className="billing-status-card">
          <span>SUA JORNADA</span>
          <ol>
            <li className="done"><i><Check/></i><div><strong>E-mail confirmado</strong><small>Conta e empresa verificadas</small></div></li>
            <li className={trialStepDone ? "done" : ""}><i>{trialStepDone ? <Check/> : "2"}</i><div><strong>3 dias grátis</strong><small>{trialStepDetail}</small></div></li>
            <li className={paid || managementAvailable ? "done" : loadState === "ready" || loadState === "demo" ? "current" : ""}><i>{paid || managementAvailable ? <Check/> : "3"}</i><div><strong>Assinatura mensal</strong><small>{subscriptionStepDetail}</small></div></li>
            <li><i>4</i><div><strong>WhatsApp e ativação</strong><small>Conecte seu número oficial pela YCloud</small></div></li>
          </ol>
        </div>
        <div className="billing-security"><CreditCard weight="duotone"/><span><strong>Checkout seguro</strong>O valor e as condições aparecem antes da confirmação; os dados financeiros são processados pelo gateway.</span></div>
      </aside>
    </section>
  );
}
