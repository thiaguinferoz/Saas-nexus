"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowSquareOut, BellSimple, BookOpen, Buildings, CalendarDots, CaretRight, ChartLineUp, ChatCircleDots, Check, Clock, CreditCard, FileCsv, FloppyDisk, Gear, Lightning, LinkSimple, ListChecks, LockKey, PaperPlaneTilt, ShieldCheck, SignOut, Sparkle, Target, Trash, UploadSimple, UserPlus, WarningCircle, WhatsappLogo } from "@phosphor-icons/react";
import { NexusLogo } from "../shared/nexus-logo";
import { AdminPanel } from "./admin-panel";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/v1";
const dayLabels: Record<string, string> = { monday: "Segunda", tuesday: "Terça", wednesday: "Quarta", thursday: "Quinta", friday: "Sexta", saturday: "Sábado", sunday: "Domingo" };
const defaultHours = Object.fromEntries(Object.keys(dayLabels).map((day) => [day, { enabled: !["saturday", "sunday"].includes(day), opens_at: "09:00", closes_at: "18:00" }]));

type DayHours = { enabled: boolean; opens_at: string; closes_at: string };
type GoalsSettings = { enabled: string[]; always_rules: string; never_rules: string; handoff_conditions: string[] };
type Settings = { company_name: string; timezone: string; assistant: { tone: string; instructions: string; human_handoff_message: string }; business_hours: Record<string, DayHours>; goals: GoalsSettings };
const defaultGoals: GoalsSettings = { enabled: ["questions", "leads", "quotes", "handoff"], always_rules: "Confirmar os dados antes de concluir uma solicitação. Informar quando um valor estiver sujeito a avaliação.", never_rules: "Inventar preços, prometer prazos não cadastrados ou responder sobre assuntos que não pertencem à empresa.", handoff_conditions: ["customer_requested", "complaint_or_cancellation", "unsafe_information"] };
const demoSettings: Settings = { company_name: "Minha empresa", timezone: "America/Sao_Paulo", assistant: { tone: "acolhedor", instructions: "Responda com clareza, seja breve e encaminhe para uma pessoa quando não tiver segurança.", human_handoff_message: "Vou chamar uma pessoa da nossa equipe para continuar com você." }, business_hours: defaultHours, goals: defaultGoals };
const tabs = [
  { id: "overview", label: "Visão geral", icon: Gear },
  { id: "company", label: "Empresa", icon: Buildings },
  { id: "catalog", label: "Catálogo e preços", icon: FileCsv },
  { id: "knowledge", label: "Base de conhecimento", icon: BookOpen },
  { id: "assistant", label: "Personalidade da IA", icon: ChatCircleDots },
  { id: "goals", label: "Objetivos e regras", icon: Target },
  { id: "hours", label: "Horários e equipe", icon: Clock },
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
      if (process.env.NODE_ENV !== "production" && new URLSearchParams(window.location.search).get("demo") === "1") {
        setDemoMode(true);
        setLoading(false);
        return;
      }
      try {
        const [response, meResponse] = await Promise.all([
          fetch(`${API_URL}/tenant/settings`, { credentials: "include" }),
          fetch(`${API_URL}/auth/me`, { credentials: "include" }),
        ]);
        if (response.status === 401 || meResponse.status === 401) { router.replace("/login"); return; }
        if (!response.ok || !meResponse.ok) throw new Error("Não foi possível carregar as configurações.");
        const [body, me] = await Promise.all([response.json(), meResponse.json()]);
        setSettings({ ...body.payload, business_hours: { ...defaultHours, ...body.payload.business_hours }, goals: body.payload.goals ?? defaultGoals }); setVersion(body.version);
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
  const moduleContent = activeTab === "catalog" ? <CatalogPanel demoMode={demoMode}/> : activeTab === "knowledge" ? <KnowledgePanel/> : activeTab === "goals" ? <GoalsPanel goals={settings.goals} onChange={(goals) => setSettings((current) => ({ ...current, goals }))} onSave={() => void save()} saving={saving} saved={saved}/> : activeTab === "support" ? <SupportPanel demoMode={demoMode}/> : activeTab === "admin" && platformAdmin ? <AdminPanel/> : null;
  const moduleDescriptions: Record<string, string> = {
    catalog: "Organize serviços, produtos e valores sem depender de planilhas durante cada conversa.",
    knowledge: "Centralize documentos, perguntas frequentes e páginas que a IA pode consultar.",
    goals: "Escolha o que a IA deve alcançar e em quais situações ela precisa chamar sua equipe.",
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

type CatalogItemSummary = { id?: string; name: string; category: string; price: string; status: string; source?: string };

function CatalogPanel({ demoMode }: { demoMode: boolean }) {
  return <div className="catalog-page"><CatalogPanelBody demoMode={demoMode}/><CatalogManagementPanel demoMode={demoMode}/></div>;
}

function CatalogManagementPanel({ demoMode }: { demoMode: boolean }) {
  const [items, setItems] = useState<CatalogItemSummary[]>([]);
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState("");
  async function loadItems() {
    if (demoMode) return;
    const response = await fetch(`${API_URL}/catalog/items`, { credentials: "include" });
    if (!response.ok) return;
    const body = await response.json() as Array<{ id: string; name: string; category?: string; price?: string; currency: string; is_active: boolean; source: string }>;
    setItems(body.map((item) => ({ id: item.id, name: item.name, category: item.category || "Sem categoria", price: item.price == null ? "Sob consulta" : new Intl.NumberFormat("pt-BR", { style: "currency", currency: item.currency || "BRL" }).format(Number(item.price)), status: item.is_active ? "Disponível" : "Inativo", source: item.source })));
  }
  useEffect(() => {
    void loadItems();
    const reload = () => { void loadItems(); };
    window.addEventListener("catalog-changed", reload);
    return () => window.removeEventListener("catalog-changed", reload);
  }, [demoMode]);
  async function removeItem(item: CatalogItemSummary) {
    if (!item.id || !window.confirm(`Remover “${item.name}” do catálogo?`)) return;
    setBusy(true); setFeedback("");
    try {
      const response = await fetch(`${API_URL}/catalog/items/${item.id}`, { method: "DELETE", credentials: "include", headers: { "X-CSRF-Token": decodeURIComponent(readCookie("csrf_token")) } });
      if (!response.ok) throw new Error("Não foi possível remover o item.");
      setItems((current) => current.filter((currentItem) => currentItem.id !== item.id));
      setFeedback("Item removido do catálogo.");
    } catch (reason) { setFeedback(reason instanceof Error ? reason.message : "Não foi possível remover o item."); }
    finally { setBusy(false); }
  }
  async function removeSpreadsheet() {
    const count = items.filter((item) => item.source === "import").length;
    if (!count || !window.confirm(`Apagar os ${count} itens importados? Produtos criados manualmente serão preservados.`)) return;
    setBusy(true); setFeedback("");
    try {
      const response = await fetch(`${API_URL}/catalog/imported-items`, { method: "DELETE", credentials: "include", headers: { "X-CSRF-Token": decodeURIComponent(readCookie("csrf_token")) } });
      if (!response.ok) throw new Error("Não foi possível apagar a planilha.");
      setItems((current) => current.filter((item) => item.source !== "import"));
      setFeedback("Planilha apagada. Itens manuais foram preservados.");
    } catch (reason) { setFeedback(reason instanceof Error ? reason.message : "Não foi possível apagar a planilha."); }
    finally { setBusy(false); }
  }
  async function saveCatalog() {
    setBusy(true); setFeedback("");
    try {
      const response = await fetch(`${API_URL}/catalog/items/publish`, { method: "POST", credentials: "include", headers: { "X-CSRF-Token": decodeURIComponent(readCookie("csrf_token")) } });
      if (!response.ok) throw new Error("Não foi possível salvar o catálogo.");
      setItems((current) => current.map((item) => ({ ...item, status: "Disponível" })));
      setFeedback("Catálogo salvo e publicado para a IA.");
    } catch (reason) { setFeedback(reason instanceof Error ? reason.message : "Não foi possível salvar o catálogo."); }
    finally { setBusy(false); }
  }
  if (demoMode) return null;
  return <section className="module-card catalog-management-card"><div className="module-card-head"><span><FileCsv/></span><div><h2>Gerenciar catálogo</h2><p>Salve, remova produtos ou apague os itens importados da planilha.</p></div><div className="catalog-actions"><button className="ghost-action" disabled={busy || !items.length} onClick={saveCatalog}><FloppyDisk/> Salvar catálogo</button><button className="ghost-action danger-action" disabled={busy || !items.some((item) => item.source === "import")} onClick={removeSpreadsheet}><Trash/> Apagar planilha</button></div></div>{feedback && <div className="mapping-preview"><small>{feedback}</small></div>}<div className="catalog-table"><div className="catalog-table-head"><span>Item</span><span>Categoria</span><span>Valor</span><span>Status</span><span>Ações</span></div>{items.length ? items.map((item) => <div className="catalog-table-row" key={item.id}><strong>{item.name}</strong><span>{item.category}</span><b>{item.price}</b><em>{item.status}</em><button className="catalog-delete-button" type="button" aria-label={`Remover ${item.name}`} title="Remover item" disabled={busy} onClick={() => removeItem(item)}><Trash/></button></div>) : <div className="catalog-empty">Nenhum item publicado.</div>}</div></section>;
}

function CatalogPanelBody({ demoMode }: { demoMode: boolean }) {
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState("");
  const [mappingHeaders, setMappingHeaders] = useState<string[]>([]);
  const [columnMapping, setColumnMapping] = useState({ name: "", price: "", category: "", sku: "" });
  const [creating, setCreating] = useState(false);
  const [newItem, setNewItem] = useState({ name: "", category: "", price: "", sku: "" });
  const [items, setItems] = useState<CatalogItemSummary[]>([
    { name: "Consultoria inicial", category: "Serviços", price: "R$ 180,00", status: "Disponível" },
    { name: "Instalação padrão", category: "Serviços", price: "R$ 350,00", status: "Disponível" },
    { name: "Plano de manutenção", category: "Planos", price: "R$ 129,90", status: "Sob consulta" },
  ]);
  useEffect(() => {
    if (demoMode) return;
    fetch(`${API_URL}/catalog/items`, { credentials: "include" })
      .then(async (response) => response.ok ? response.json() : [])
      .then((body: Array<{ id: string; name: string; category?: string; price?: string; currency: string; is_active: boolean; source: string }>) => {
        setItems(body.map((item) => ({
          id: item.id,
          name: item.name,
          category: item.category || "Sem categoria",
          price: item.price == null ? "Sob consulta" : new Intl.NumberFormat("pt-BR", { style: "currency", currency: item.currency || "BRL" }).format(Number(item.price)),
          status: item.is_active ? "Disponível" : "Inativo",
          source: item.source,
        })));
      }).catch(() => null);
  }, [demoMode]);
  function summarize(item: { id: string; name: string; category?: string; price?: string; currency: string; is_active: boolean; source?: string }): CatalogItemSummary {
    return { id: item.id, name: item.name, category: item.category || "Sem categoria", price: item.price == null ? "Sob consulta" : new Intl.NumberFormat("pt-BR", { style: "currency", currency: item.currency || "BRL" }).format(Number(item.price)), status: item.is_active ? "Disponível" : "Inativo", source: item.source };
  }
  async function importCatalog() {
    if (!file) return;
    setBusy(true); setFeedback("");
    try {
      const data = new FormData(); data.append("file", file);
      if (mappingHeaders.length) {
        data.append("mapping_confirmed", "true");
        data.append("name_column", columnMapping.name);
        if (columnMapping.price) data.append("price_column", columnMapping.price);
        if (columnMapping.category) data.append("category_column", columnMapping.category);
        if (columnMapping.sku) data.append("sku_column", columnMapping.sku);
      }
      const response = await fetch(`${API_URL}/catalog/import`, { method: "POST", credentials: "include", headers: { "X-CSRF-Token": decodeURIComponent(readCookie("csrf_token")) }, body: data });
      const body = await response.json();
      if (!response.ok) {
        if (body.detail?.mapping_required && Array.isArray(body.detail.headers)) {
          setMappingHeaders(body.detail.headers);
          setColumnMapping({
            name: body.detail.suggested_mapping?.name || "",
            price: body.detail.suggested_mapping?.price || "",
            category: body.detail.suggested_mapping?.category || "",
            sku: body.detail.suggested_mapping?.sku || "",
          });
          setFeedback("A estrutura foi lida, mas precisamos confirmar o significado das colunas.");
          return;
        }
        const detail = typeof body.detail === "string" ? body.detail : body.detail?.message;
        const details = Array.isArray(body.detail?.errors) ? ` ${body.detail.errors.slice(0, 3).join(" ")}` : "";
        throw new Error(`${detail || "Não foi possível importar a planilha."}${details}`);
      }
      const importedItems = (body.items as Array<{ id: string; name: string; category?: string; price?: string; currency: string; is_active: boolean; source: string }>).map(summarize);
      setItems((current) => {
        const importedIds = new Set(importedItems.map((item) => item.id));
        return [...importedItems, ...current.filter((item) => !item.id || !importedIds.has(item.id))];
      });
      const warnings = Array.isArray(body.errors) && body.errors.length ? ` ${body.errors.slice(0, 3).join(" ")}` : "";
      setFeedback(`${body.imported} item(ns) importado(s)${body.updated ? ` e ${body.updated} atualizado(s)` : ""}.${body.skipped ? ` ${body.skipped} linha(s) foram ignoradas.` : ""}${warnings}`);
      setFile(null);
      setMappingHeaders([]);
      window.dispatchEvent(new Event("catalog-changed"));
    } catch (reason) { setFeedback(reason instanceof Error ? reason.message : "Não foi possível importar a planilha."); }
    finally { setBusy(false); }
  }
  async function createManualItem(event: FormEvent) {
    event.preventDefault();
    setBusy(true); setFeedback("");
    try {
      const payload = { name: newItem.name.trim(), category: newItem.category.trim() || null, price: newItem.price || null, sku: newItem.sku.trim() || null, currency: "BRL", is_active: true };
      if (demoMode) {
        setItems((current) => [summarize({ id: `demo-${Date.now()}`, ...payload, category: payload.category || undefined, price: payload.price || undefined, currency: "BRL", is_active: true }), ...current]);
      } else {
        const response = await fetch(`${API_URL}/catalog/items`, { method: "POST", credentials: "include", headers: { "Content-Type": "application/json", "X-CSRF-Token": decodeURIComponent(readCookie("csrf_token")) }, body: JSON.stringify(payload) });
        const body = await response.json().catch(() => null);
        if (!response.ok) throw new Error(body?.detail || "Não foi possível criar o item.");
        setItems((current) => [summarize(body), ...current]);
      }
      setNewItem({ name: "", category: "", price: "", sku: "" });
      setCreating(false);
      setFeedback("Item criado e publicado no catálogo.");
      window.dispatchEvent(new Event("catalog-changed"));
    } catch (reason) { setFeedback(reason instanceof Error ? reason.message : "Não foi possível criar o item."); }
    finally { setBusy(false); }
  }
  return <section className="personalization-view"><div className="automation-explainer"><span><Lightning weight="fill"/></span><div><strong>Catálogo padrão para qualquer tipo de negócio</strong><p>Envie uma planilha e a Nexus transforma produtos, serviços e valores em dados estruturados e isolados por empresa.</p></div><b>AUTOMÁTICO</b></div><div className="personalization-grid catalog-layout"><article className="module-card import-card"><div className="module-card-head"><span><UploadSimple/></span><div><h2>Importar catálogo</h2><p>CSV ou Excel com produtos, serviços e valores.</p></div></div><label className={`upload-zone ${file ? "has-file" : ""}`}><input type="file" accept=".csv,.xlsx" onChange={(event) => { setFile(event.target.files?.[0] ?? null); setFeedback(""); setMappingHeaders([]); }}/><FileCsv weight="duotone"/><strong>{file?.name || "Arraste a planilha ou selecione um arquivo"}</strong><small>{file ? "Arquivo selecionado e pronto para importar." : "Até 20 MB • CSV ou XLSX"}</small></label>{mappingHeaders.length > 0 && <div className="catalog-editor mapping-confirmation"><strong>Confirme as colunas</strong><label>Nome do produto ou serviço<select required value={columnMapping.name} onChange={(event) => setColumnMapping({ ...columnMapping, name: event.target.value })}><option value="">Selecione...</option>{mappingHeaders.map((header) => <option key={`name-${header}`} value={header}>{header}</option>)}</select></label><label>Preço<select value={columnMapping.price} onChange={(event) => setColumnMapping({ ...columnMapping, price: event.target.value })}><option value="">Sem preço / sob consulta</option>{mappingHeaders.map((header) => <option key={`price-${header}`} value={header}>{header}</option>)}</select></label><label>Categoria<select value={columnMapping.category} onChange={(event) => setColumnMapping({ ...columnMapping, category: event.target.value })}><option value="">Sem categoria</option>{mappingHeaders.map((header) => <option key={`category-${header}`} value={header}>{header}</option>)}</select></label><label>SKU ou código<select value={columnMapping.sku} onChange={(event) => setColumnMapping({ ...columnMapping, sku: event.target.value })}><option value="">Sem código</option>{mappingHeaders.map((header) => <option key={`sku-${header}`} value={header}>{header}</option>)}</select></label></div>}<button className="module-primary-button" disabled={!file || busy || (mappingHeaders.length > 0 && !columnMapping.name)} onClick={importCatalog}><Sparkle weight="fill"/> {busy ? "Importando..." : mappingHeaders.length ? "Confirmar colunas e importar" : "Extrair e publicar itens"}</button>{feedback && <div className="mapping-preview"><small>{feedback}</small></div>}<small>A Nexus detecta automaticamente a estrutura. Se houver dúvida, você confirma quais colunas contêm nome, preço, categoria e código.</small></article><article className="module-card catalog-card"><div className="module-card-head"><span><FileCsv/></span><div><h2>Catálogo publicado</h2><p>{demoMode ? "Exemplo genérico da estrutura padrão." : `${items.length} itens disponíveis para a IA.`}</p></div><button className="ghost-action" type="button" onClick={() => setCreating((value) => !value)}>{creating ? "Cancelar" : "+ Novo item"}</button></div>{creating && <form className="catalog-editor" onSubmit={createManualItem}><label>Nome<input required minLength={2} maxLength={200} value={newItem.name} onChange={(event) => setNewItem({ ...newItem, name: event.target.value })} placeholder="Produto ou serviço"/></label><label>Categoria<input maxLength={120} value={newItem.category} onChange={(event) => setNewItem({ ...newItem, category: event.target.value })} placeholder="Ex.: Serviços"/></label><label>Preço em reais<input inputMode="decimal" pattern="[0-9]+([,.][0-9]{1,2})?" value={newItem.price} onChange={(event) => setNewItem({ ...newItem, price: event.target.value.replace(",", ".") })} placeholder="0,00"/></label><label>SKU/código<input maxLength={120} value={newItem.sku} onChange={(event) => setNewItem({ ...newItem, sku: event.target.value })} placeholder="Opcional"/></label><button className="module-primary-button" disabled={busy}>{busy ? "Salvando..." : "Criar item"}</button></form>}<div className="catalog-table"><div className="catalog-table-head"><span>Item</span><span>Categoria</span><span>Valor</span><span>Status</span></div>{items.length ? items.map((item) => <div className="catalog-table-row" key={item.id || item.name}><strong>{item.name}</strong><span>{item.category}</span><b>{item.price}</b><em>{item.status}</em></div>) : <div className="catalog-empty">Seu catálogo ainda está vazio. Importe uma planilha ou crie o primeiro item.</div>}</div><div className="structured-note"><LockKey/><span><strong>Valores sempre exatos</strong>Preços são consultados diretamente no catálogo estruturado, e não na memória do modelo.</span></div></article></div></section>;
}

function KnowledgePanel() {
  const [sourceType, setSourceType] = useState("files");
  const sources = [{ name: "Políticas comerciais.pdf", type: "Documento", detail: "18 trechos indexados", status: "Pronto" }, { name: "Perguntas frequentes", type: "FAQ", detail: "12 respostas", status: "Pronto" }, { name: "Página de serviços", type: "Site", detail: "Atualizado hoje", status: "Sincronizado" }];
  return <section className="personalization-view"><div className="automation-explainer knowledge"><span><BookOpen weight="fill"/></span><div><strong>Uma biblioteca exclusiva para cada empresa</strong><p>Arquivos e textos são processados em segundo plano, separados pelo tenant e utilizados somente quando forem relevantes para a pergunta.</p></div><b>ISOLADO POR CLIENTE</b></div><div className="source-picker"><button className={sourceType === "files" ? "active" : ""} onClick={() => setSourceType("files")}><UploadSimple/><strong>Arquivos</strong><small>PDF, DOCX e planilhas</small></button><button className={sourceType === "faq" ? "active" : ""} onClick={() => setSourceType("faq")}><ListChecks/><strong>Perguntas frequentes</strong><small>Respostas validadas</small></button><button className={sourceType === "url" ? "active" : ""} onClick={() => setSourceType("url")}><LinkSimple/><strong>Páginas do site</strong><small>Conteúdo sincronizado</small></button></div><div className="personalization-grid knowledge-layout"><article className="module-card source-builder"><div className="module-card-head"><span>{sourceType === "files" ? <UploadSimple/> : sourceType === "faq" ? <ListChecks/> : <LinkSimple/>}</span><div><h2>{sourceType === "files" ? "Adicionar documentos" : sourceType === "faq" ? "Criar pergunta frequente" : "Importar página"}</h2><p>A Nexus valida antes de disponibilizar para a IA.</p></div></div>{sourceType === "files" && <label className="upload-zone"><input type="file" accept=".pdf,.doc,.docx,.csv,.xlsx"/><BookOpen weight="duotone"/><strong>Selecione os arquivos da empresa</strong><small>O processamento acontece automaticamente</small></label>}{sourceType === "faq" && <div className="source-form"><label>Pergunta<input placeholder="Ex.: Quais formas de pagamento vocês aceitam?"/></label><label>Resposta validada<textarea rows={5} placeholder="Escreva a resposta oficial da empresa."/></label></div>}{sourceType === "url" && <div className="source-form"><label>Endereço da página<input placeholder="https://empresa.com.br/servicos"/></label><div className="sync-choice"><Check/> Verificar atualizações automaticamente uma vez por dia</div></div>}<button className="module-primary-button"><PlusIcon/> Adicionar à base</button></article><article className="module-card source-list-card"><div className="module-card-head"><span><BookOpen/></span><div><h2>Fontes disponíveis</h2><p>Conteúdo que a IA pode consultar agora.</p></div></div><div className="source-list">{sources.map((source) => <div key={source.name}><i>{source.type === "Documento" ? <BookOpen/> : source.type === "FAQ" ? <ListChecks/> : <LinkSimple/>}</i><span><strong>{source.name}</strong><small>{source.type} • {source.detail}</small></span><b><Check/> {source.status}</b></div>)}</div></article></div></section>;
}

function PlusIcon() { return <span aria-hidden="true">+</span>; }

function GoalsPanel({ goals, onChange, onSave, saving, saved }: { goals: GoalsSettings; onChange: (goals: GoalsSettings) => void; onSave: () => void; saving: boolean; saved: boolean }) {
  const goalOptions = [{ id: "questions", title: "Responder dúvidas", text: "Consulta catálogo, documentos e FAQs", icon: BookOpen }, { id: "leads", title: "Qualificar oportunidades", text: "Coleta dados importantes antes do contato", icon: Target }, { id: "quotes", title: "Preparar orçamentos", text: "Usa valores exatos do catálogo", icon: FileCsv }, { id: "appointments", title: "Agendar atendimento", text: "Encaminha para agenda ou equipe", icon: CalendarDots }, { id: "orders", title: "Consultar solicitações", text: "Aciona integrações autorizadas", icon: Lightning }, { id: "handoff", title: "Chamar um humano", text: "Transfere conversas sensíveis ou complexas", icon: UserPlus }];
  const handoffOptions = [{ id: "customer_requested", label: "Cliente pediu uma pessoa" }, { id: "complaint_or_cancellation", label: "Reclamação ou cancelamento" }, { id: "unsafe_information", label: "IA sem informação segura" }];
  function toggleGoal(id: string) { onChange({ ...goals, enabled: goals.enabled.includes(id) ? goals.enabled.filter((goal) => goal !== id) : [...goals.enabled, id] }); }
  function toggleHandoff(id: string) { onChange({ ...goals, handoff_conditions: goals.handoff_conditions.includes(id) ? goals.handoff_conditions.filter((condition) => condition !== id) : [...goals.handoff_conditions, id] }); }
  return <section className="personalization-view"><div className="automation-explainer goals"><span><Target weight="fill"/></span><div><strong>O cliente escolhe resultados, não constrói workflows</strong><p>A Nexus transforma as escolhas abaixo em regras e ferramentas disponíveis para a IA. Integrações especiais continuam como serviço adicional.</p></div><b>SEM CÓDIGO</b></div><article className="module-card"><div className="module-card-head"><span><Target/></span><div><h2>O que a IA deve fazer?</h2><p>Ative apenas os objetivos que fazem sentido para esta operação.</p></div><strong className="selection-count">{goals.enabled.length} ativos</strong></div><div className="goal-grid">{goalOptions.map(({ id, title, text, icon: Icon }) => { const active = goals.enabled.includes(id); return <button type="button" key={id} className={active ? "active" : ""} aria-pressed={active} onClick={() => toggleGoal(id)}><i><Icon weight={active ? "fill" : "duotone"}/></i><span><strong>{title}</strong><small>{text}</small></span><em>{active ? <Check/> : "+"}</em></button>; })}</div></article><div className="personalization-grid rules-layout"><article className="module-card rules-card"><div className="module-card-head"><span><ListChecks/></span><div><h2>Regras obrigatórias</h2><p>Informações que devem orientar todas as conversas.</p></div></div><div className="source-form"><label>A IA sempre deve<textarea rows={5} maxLength={4000} value={goals.always_rules} onChange={(event) => onChange({ ...goals, always_rules: event.target.value })}/></label><label>A IA nunca deve<textarea rows={5} maxLength={4000} value={goals.never_rules} onChange={(event) => onChange({ ...goals, never_rules: event.target.value })}/></label></div></article><article className="module-card handoff-card"><div className="module-card-head"><span><UserPlus/></span><div><h2>Encaminhamento humano</h2><p>Situações que interrompem a automação.</p></div></div><div className="handoff-tags">{handoffOptions.map((option) => { const active = goals.handoff_conditions.includes(option.id); return <button type="button" key={option.id} className={active ? "active" : ""} aria-pressed={active} onClick={() => toggleHandoff(option.id)}>{active && <Check/>} {option.label}</button>; })}</div><div className="structured-note"><UserPlus/><span><strong>A equipe recebe o contexto</strong>A conversa e o motivo do encaminhamento acompanham a transferência.</span></div></article></div><button type="button" className="module-primary-button goals-save" onClick={onSave} disabled={saving}>{saving ? "Salvando..." : saved ? "Objetivos e regras salvos" : "Salvar objetivos e regras"}</button></section>;
}

type SupportTicketSummary = { id: string; category: string; priority: string; status: string; subject: string; message: string; preferred_channel: string; contact_value: string | null; replies: Array<{ id: string; author_role: string; message: string; created_at: string }>; created_at: string };

function SupportPanel({ demoMode }: { demoMode: boolean }) {
  const [category, setCategory] = useState("support");
  const [subject, setSubject] = useState("");
  const [message, setMessage] = useState("");
  const [tickets, setTickets] = useState<SupportTicketSummary[]>([]);
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; message: string } | null>(null);
  const [openedTicket, setOpenedTicket] = useState("");

  useEffect(() => {
    if (demoMode) return;
    fetch(`${API_URL}/support/tickets`, { credentials: "include" })
      .then(async (response) => response.ok ? response.json() : [])
      .then(setTickets).catch(() => null);
  }, [demoMode]);

  function chooseCustomPlan() {
    setCategory("custom_plan");
    setSubject("Quero falar sobre o plano personalizado");
    setFeedback(null);
  }

  async function submitTicket(event: FormEvent) {
    event.preventDefault();
    if (subject.trim().length < 4 || message.trim().length < 10) {
      setFeedback({ type: "error", message: "Informe um assunto e descreva a solicitação com pelo menos 10 caracteres." });
      return;
    }
    setBusy(true);
    setFeedback(null);
    const payload = { category, subject: subject.trim(), message: message.trim(), preferred_channel: "platform", contact_value: null };
    try {
      let ticket: SupportTicketSummary;
      if (demoMode) {
        ticket = { id: `demo-${Date.now()}`, category, priority: category === "custom_plan" ? "high" : "normal", status: "open", subject: payload.subject, message: payload.message, preferred_channel: payload.preferred_channel, contact_value: payload.contact_value, replies: [], created_at: new Date().toISOString() };
      } else {
        const response = await fetch(`${API_URL}/support/tickets`, { method: "POST", credentials: "include", headers: { "Content-Type": "application/json", "X-CSRF-Token": decodeURIComponent(readCookie("csrf_token")) }, body: JSON.stringify(payload) });
        const body = await response.json().catch(() => null);
        if (!response.ok) throw new Error(typeof body?.detail === "string" ? body.detail : "Não foi possível enviar a solicitação.");
        if (!body) throw new Error("O ticket foi recebido, mas não foi possível atualizar a tela. Recarregue a página para acompanhá-lo.");
        ticket = body;
      }
      setTickets((current) => [ticket, ...current]);
      setMessage("");
      setFeedback({ type: "success", message: category === "custom_plan" ? "Pedido prioritário enviado. Um especialista Nexus responderá pela plataforma." : "Solicitação enviada. Você pode acompanhar o andamento nesta página." });
    } catch (reason) {
      setFeedback({ type: "error", message: reason instanceof TypeError ? "Não foi possível conectar ao suporte. Tente novamente." : reason instanceof Error ? reason.message : "Não foi possível enviar a solicitação." });
    } finally {
      setBusy(false);
    }
  }

  const statusLabels: Record<string, string> = { open: "Aberto", in_progress: "Em atendimento", resolved: "Resolvido" };
  return <section className="personalization-view support-view"><div className="support-hero"><span><ChatCircleDots weight="duotone"/></span><div><small>CENTRAL DE SUPORTE</small><h2>A Nexus está ao seu lado</h2><p>Tire dúvidas sobre a plataforma ou solicite atendimento especializado sem sair do painel.</p></div><b>ATENDIMENTO DIRETO</b></div><div className="support-layout"><form className="module-card support-form" onSubmit={submitTicket}><div className="module-card-head"><span><PaperPlaneTilt/></span><div><h2>Nova solicitação</h2><p>Conte o que precisa e acompanhe o retorno pela plataforma.</p></div></div><div className="support-category"><button type="button" className={category === "support" ? "active" : ""} onClick={() => setCategory("support")}><ChatCircleDots/><span><strong>Suporte da plataforma</strong><small>Configuração, uso ou problemas</small></span></button><button type="button" className={category === "custom_plan" ? "active custom" : "custom"} onClick={chooseCustomPlan}><Sparkle weight="fill"/><span><strong>Plano personalizado</strong><small>Fale direto com um especialista</small></span></button></div><label>Assunto<input minLength={4} maxLength={200} value={subject} onChange={(event) => setSubject(event.target.value)} placeholder="Como podemos ajudar?" required/></label><label>Detalhes<textarea rows={6} minLength={10} maxLength={8000} value={message} onChange={(event) => setMessage(event.target.value)} placeholder="Descreva sua necessidade com o máximo de contexto." required/></label><div className="support-platform-note"><ChatCircleDots weight="duotone"/><span><strong>Retorno pela plataforma</strong><small>As respostas da equipe Nexus aparecerão no histórico das suas solicitações.</small></span></div><button className="module-primary-button" disabled={busy}>{busy ? "Enviando..." : category === "custom_plan" ? "Solicitar contato prioritário" : "Enviar ao suporte"}</button>{feedback && <div className={`support-feedback ${feedback.type}`}>{feedback.type === "success" ? <Check weight="bold"/> : <WarningCircle weight="bold"/>} {feedback.message}</div>}</form><aside className="support-side"><article className="module-card custom-contact-card"><span><Sparkle weight="fill"/></span><small>EXCLUSIVO DO PLANO PERSONALIZADO</small><h2>Converse com quem vai desenhar sua solução</h2><p>Integrações com ERP, regras exclusivas e fluxos sob medida recebem acompanhamento direto da equipe Nexus.</p><ul><li><Check/> Solicitação com prioridade alta</li><li><Check/> Retorno acompanhado pela plataforma</li><li><Check/> Contexto registrado no seu workspace</li></ul><button type="button" onClick={chooseCustomPlan}>Quero falar com um especialista <CaretRight/></button></article><article className="module-card ticket-history"><div className="module-card-head"><span><ListChecks/></span><div><h2>Suas solicitações</h2><p>Acompanhe os contatos deste workspace.</p></div></div>{tickets.length ? <div className="ticket-list">{tickets.slice(0, 5).map((ticket) => <div key={ticket.id} className={openedTicket === ticket.id ? "open" : ""}><button type="button" className="ticket-open" aria-expanded={openedTicket === ticket.id} onClick={() => setOpenedTicket((current) => current === ticket.id ? "" : ticket.id)}><i className={ticket.priority === "high" ? "high" : ""}/><span><strong>{ticket.subject}</strong><small>{ticket.category === "custom_plan" ? "Plano personalizado" : "Suporte"} • {new Date(ticket.created_at).toLocaleDateString("pt-BR")}</small></span><b>{statusLabels[ticket.status] || ticket.status}</b></button>{openedTicket === ticket.id && <div className="ticket-details"><p>{ticket.message}</p><small>Retorno: Pela plataforma</small></div>}</div>)}</div> : <div className="ticket-empty"><ChatCircleDots/><strong>Nenhuma solicitação ainda</strong><small>Quando precisar, sua conversa com a Nexus começa aqui.</small></div>}</article></aside></div></section>;
}

function AssistantPreview({ settings }: { settings: Settings }) { return <aside className="assistant-preview"><span>PRÉVIA DO ATENDIMENTO</span><div className="preview-bubble client">Olá! Vocês conseguem me ajudar?</div><div className="preview-bubble ai"><b><Sparkle weight="fill"/> NEXUS</b>Olá! Claro, será um prazer ajudar. Pode me contar o que você precisa?</div><small>Tom selecionado: {settings.assistant.tone}</small></aside>; }

type WhatsAppConnection = { waba_id: string; phone_number: string; phone_number_id?: string; display_name?: string; quality_rating?: string; status: string };
type EmbeddedSession = { app_id: string; configuration_id: string; solution_id: string; state: string };

function WhatsAppPanel({ demoMode, onConnectionChange }: { demoMode: boolean; onConnectionChange: (connected: boolean) => void }) {
  const [connection, setConnection] = useState<WhatsAppConnection | null>(null);
  const [phone, setPhone] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  useEffect(() => {
    if (demoMode) return;
    fetch(`${API_URL}/whatsapp/connection`, { credentials: "include" }).then(async (response) => response.ok ? response.json() : null).then((body) => { setConnection(body); onConnectionChange(body?.status === "connected"); }).catch(() => null);
  }, [demoMode, onConnectionChange]);

  async function finishOnboarding(session: EmbeddedSession, data: { waba_id: string; phone_number_id?: string }, phoneNumber: string) {
    const response = await fetch(`${API_URL}/whatsapp/onboarding/complete`, { method: "POST", credentials: "include", headers: { "Content-Type": "application/json", "X-CSRF-Token": decodeURIComponent(readCookie("csrf_token")) }, body: JSON.stringify({ state: session.state, waba_id: data.waba_id, phone_number_id: data.phone_number_id, phone_number: phoneNumber }) });
    const body = await response.json();
    if (!response.ok) throw new Error(typeof body.detail === "string" ? body.detail : "Não foi possível concluir a conexão.");
    setConnection(body); onConnectionChange(true); setMessage(""); setBusy(false);
  }

  async function connect() {
    setBusy(true); setMessage("");
    const digits = phone.replace(/\D/g, "");
    const brazilianNumber = digits.startsWith("55") && [12, 13].includes(digits.length) ? digits.slice(2) : digits;
    if (!/^\d{10,11}$/.test(brazilianNumber)) { setMessage("Informe o DDD e o número, por exemplo: 13 99999-0000."); setBusy(false); return; }
    const phoneNumber = `+55${brazilianNumber}`;
    if (demoMode) { setTimeout(() => { const demo = { waba_id: "demo", phone_number: phoneNumber, display_name: "Nexus Demonstração", quality_rating: "GREEN", status: "connected" }; setConnection(demo); onConnectionChange(true); setBusy(false); }, 700); return; }
    try {
      const response = await fetch(`${API_URL}/whatsapp/onboarding/session`, { method: "POST", credentials: "include", headers: { "X-CSRF-Token": decodeURIComponent(readCookie("csrf_token")) } });
      const session = await response.json() as EmbeddedSession & { detail?: string };
      if (!response.ok) throw new Error(session.detail || "Não foi possível iniciar a autorização.");
      const fbWindow = window as typeof window & { FB?: { init: (options: Record<string, unknown>) => void; login: (callback: (response: { status?: string }) => void, options: Record<string, unknown>) => void } };
      if (!fbWindow.FB) throw new Error("O serviço de autorização da Meta ainda está carregando. Tente novamente em alguns segundos.");
      fbWindow.FB.init({ appId: session.app_id, cookie: true, xfbml: true, version: "v23.0" });
      const receiveMessage = (event: MessageEvent) => {
        const eventHost = new URL(event.origin).hostname;
        if (eventHost !== "facebook.com" && !eventHost.endsWith(".facebook.com")) return;
        try {
          const data = typeof event.data === "string" ? JSON.parse(event.data) : event.data;
          if (data?.type !== "WA_EMBEDDED_SIGNUP") return;
          const finishedCoexistence = data.event === "FINISH_WHATSAPP_BUSINESS_APP_ONBOARDING" || (data.event === "FINISH" && data.data?.is_wa_login_user);
          if (finishedCoexistence) {
            window.removeEventListener("message", receiveMessage);
            if (!data.data?.waba_id) {
              setMessage("A Meta não retornou a conta do WhatsApp.");
              setBusy(false);
              return;
            }
            finishOnboarding(session, { waba_id: data.data.waba_id, phone_number_id: data.data.phone_number_id }, phoneNumber).catch((reason) => { setMessage(reason instanceof Error ? reason.message : "Erro inesperado."); setBusy(false); });
          } else if (data.event === "ERROR") {
            window.removeEventListener("message", receiveMessage);
            setMessage(data.data?.error_message || "A Meta não conseguiu concluir a autorização.");
            setBusy(false);
          } else if (data.event === "CANCEL") {
            window.removeEventListener("message", receiveMessage);
            setMessage("A autorização foi cancelada antes de terminar.");
            setBusy(false);
          }
        } catch { /* mensagens externas que não pertencem ao onboarding */ }
      };
      window.addEventListener("message", receiveMessage);
      fbWindow.FB.login((loginResponse) => {
        if (loginResponse.status && loginResponse.status !== "connected") {
          window.removeEventListener("message", receiveMessage);
          setMessage("A autorização da Meta não foi concluída.");
          setBusy(false);
        }
      }, {
        config_id: session.configuration_id,
        response_type: "code",
        override_default_response_type: true,
        extras: {
          setup: { solutionID: session.solution_id },
          sessionInfoVersion: 3,
          featureType: "whatsapp_business_app_onboarding",
        },
      });
      setMessage("Conclua a autorização na janela da Meta. Esta tela será atualizada automaticamente.");
    } catch (reason) { setMessage(reason instanceof Error ? reason.message : "Erro inesperado."); setBusy(false); }
  }

  useEffect(() => {
    if (document.getElementById("facebook-jssdk")) return;
    const script = document.createElement("script"); script.id = "facebook-jssdk"; script.async = true; script.defer = true; script.crossOrigin = "anonymous"; script.src = "https://connect.facebook.net/pt_BR/sdk.js"; document.body.appendChild(script);
  }, []);

  const connected = connection?.status === "connected";
  return <section className="whatsapp-view"><div className="whatsapp-hero"><div className="whatsapp-orbit"><i/><i/><i/></div><div className="whatsapp-hero-copy"><span><WhatsappLogo weight="fill"/> CANAL OFICIAL</span><h2>{connected ? "WhatsApp conectado e pronto." : "Conecte seu número. A Nexus cuida do restante."}</h2><p>{connected ? "Seu canal está vinculado ao tenant correto e pode receber o workflow inteligente da Nexus." : "A autorização acontece no ambiente seguro da Meta. Você não precisa compartilhar senha, token ou acesso ao n8n."}</p>{connected ? <div className="connected-number"><i><WhatsappLogo weight="fill"/></i><span><small>{connection.display_name || "Sua empresa"}</small><strong>{connection.phone_number}</strong></span><b><Check weight="bold"/> CONECTADO</b></div> : <div className="connect-form"><label>Número que será conectado<input inputMode="tel" value={phone} onChange={(event) => setPhone(event.target.value)} placeholder="13 99999-0000"/><small>O código do Brasil (+55) é adicionado automaticamente.</small></label><button className="button whatsapp-button" onClick={connect} disabled={busy}>{busy ? "Aguardando autorização..." : demoMode ? "Simular conexão" : "Conectar com a Meta"}<ArrowSquareOut/></button></div>}{message && <small className="whatsapp-message">{message}</small>}</div></div><aside className="whatsapp-guide"><span>COMO FUNCIONA</span><ol><li className={connected ? "done" : "current"}><i>{connected ? <Check/> : "1"}</i><div><strong>Autorize sua empresa</strong><small>Login e permissões diretamente na Meta</small></div></li><li className={connected ? "done" : ""}><i>{connected ? <Check/> : "2"}</i><div><strong>Vinculação automática</strong><small>YCloud e Nexus identificam seu número</small></div></li><li className={connected ? "done" : ""}><i>{connected ? <Check/> : "3"}</i><div><strong>Ativação do atendimento</strong><small>O workflow recebe as configurações do painel</small></div></li></ol><div className="whatsapp-safe"><LockKey weight="duotone"/><span><strong>Seus acessos ficam protegidos</strong>A Nexus não solicita sua senha do WhatsApp ou Facebook.</span></div></aside></section>;
}

type BillingState = {
  status: string;
  provider: string;
  plan_code: string | null;
  billing_interval: string | null;
  amount_paid_cents: number | null;
  last_payment_method: string | null;
  current_period_end: string | null;
  trial_ends_at: string | null;
  trial_days_remaining: number;
  access_allowed: boolean;
  cancel_at_period_end: boolean;
  management_available: boolean;
};

type PlanCode = "common" | "custom";
type BillingInterval = "monthly" | "annual";

const BILLING_OFFERS: Record<PlanCode, { name: string; monthly: number; annual: number; description: string }> = {
  common: { name: "Comum", monthly: 600, annual: 5400, description: "Auto personalização e recursos essenciais da Nexus." },
  custom: { name: "Personalizado", monthly: 1000, annual: 9000, description: "Configuração personalizada com acompanhamento especializado." },
};

function formatMoney(value: number) {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 }).format(value);
}

function BillingPanel({ demoMode }: { demoMode: boolean }) {
  const [billing, setBilling] = useState<BillingState | null>(null);
  const [loadState, setLoadState] = useState<"loading" | "ready" | "error" | "demo">(demoMode ? "demo" : "loading");
  const [loadError, setLoadError] = useState("");
  const [reloadToken, setReloadToken] = useState(0);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [plan, setPlan] = useState<PlanCode>("common");
  const [interval, setInterval] = useState<BillingInterval>("monthly");

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
    async function loadBilling() {
      const currentUrl = new URL(window.location.href);
      if (currentUrl.searchParams.get("checkout") === "success") {
        const orderNsu = currentUrl.searchParams.get("order_nsu");
        const transactionNsu = currentUrl.searchParams.get("transaction_nsu");
        const slug = currentUrl.searchParams.get("slug");
        let confirmationFinished = !(orderNsu && transactionNsu && slug);
        if (orderNsu && transactionNsu && slug) {
          try {
            const verification = await fetch(`${API_URL}/billing/infinitepay/verify`, {
              method: "POST",
              credentials: "include",
              headers: { "Content-Type": "application/json", "X-CSRF-Token": decodeURIComponent(readCookie("csrf_token")) },
              body: JSON.stringify({ order_nsu: orderNsu, transaction_nsu: transactionNsu, slug }),
            });
            const verificationBody = await verification.json().catch(() => null) as { detail?: string } | null;
            if (!verification.ok) throw new Error(verificationBody?.detail || "Pagamento recebido; a confirmação ainda está sendo processada.");
            confirmationFinished = true;
            if (!cancelled) setMessage("Pagamento confirmado. Seu acesso já foi atualizado.");
          } catch (reason) {
            if (!cancelled) setMessage(reason instanceof Error ? reason.message : "A confirmação do pagamento ainda está sendo processada.");
          }
        }
        if (confirmationFinished) window.history.replaceState({}, "", currentUrl.pathname);
      } else if (currentUrl.searchParams.get("checkout") === "canceled") {
        if (!cancelled) setMessage("Pagamento não concluído. Nenhuma cobrança foi confirmada.");
        window.history.replaceState({}, "", currentUrl.pathname);
      }

      const response = await fetch(`${API_URL}/billing/subscription`, { credentials: "include" });
      const body = await response.json().catch(() => null) as (BillingState & { detail?: string }) | null;
      if (!response.ok) throw new Error(body?.detail || "Não foi possível consultar sua assinatura.");
      return body;
    }

    loadBilling()
      .then((body) => {
        if (cancelled) return;
        setBilling(body?.status ? body : null);
        if (body?.plan_code === "common" || body?.plan_code === "custom") setPlan(body.plan_code);
        if (body?.billing_interval === "monthly" || body?.billing_interval === "annual") setInterval(body.billing_interval);
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
    if (demoMode) {
      setTimeout(() => {
        setBusy(false);
        setMessage(`Checkout de demonstração: plano ${BILLING_OFFERS[plan].name} ${interval === "annual" ? "anual" : "mensal"}.`);
      }, 450);
      return;
    }
    try {
      const checkout = endpoint === "checkout";
      const response = await fetch(`${API_URL}/billing/${endpoint}`, {
        method: "POST",
        credentials: "include",
        headers: {
          ...(checkout ? { "Content-Type": "application/json" } : {}),
          "X-CSRF-Token": decodeURIComponent(readCookie("csrf_token")),
        },
        ...(checkout ? { body: JSON.stringify({ plan, interval }) } : {}),
      });
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
  const hadPaidPlan = Boolean(billing?.plan_code);
  const expiredPaidPlan = loadState === "ready" && status === "incomplete" && hadPaidPlan;
  const expiredTrial = loadState === "ready" && !billing?.access_allowed && !hadPaidPlan && status === "incomplete" && Number.isFinite(trialEndTimestamp) && trialEndTimestamp <= Date.now();
  const paymentIssue = status === "past_due" || status === "unpaid";
  const cancelScheduled = loadState === "ready" && Boolean(billing?.cancel_at_period_end);
  const managementAvailable = loadState === "ready" && Boolean(billing?.management_available);
  const trialDays = billing?.trial_days_remaining ?? 0;
  const trialLabel = trialDays === 1 ? "1 dia grátis restante" : `${trialDays} dias grátis restantes`;
  const selectedOffer = BILLING_OFFERS[plan];
  const selectedPrice = interval === "annual" ? selectedOffer.annual : selectedOffer.monthly;
  const activePlan = billing?.plan_code === "custom" ? "Personalizado" : "Comum";
  const activeInterval = billing?.billing_interval === "annual" ? "anual" : "mensal";
  const activeUntil = billing?.current_period_end
    ? new Intl.DateTimeFormat("pt-BR", { dateStyle: "long" }).format(new Date(billing.current_period_end))
    : null;

  let badge = "Plano não contratado";
  let headline = "Escolha o plano ideal para continuar.";
  let description = "Pague com Pix ou cartão no checkout seguro da InfinitePay. No anual, o valor total pode ser parcelado em até 12 vezes.";
  let actionLabel = "Ir para o pagamento";
  let actionEndpoint: "checkout" | "portal" = "checkout";

  if (loadState === "loading") {
    badge = "Consultando plano";
    headline = "Consultando sua assinatura.";
    description = "Estamos verificando seu teste gratuito e os pagamentos confirmados.";
    actionLabel = "Consultando...";
  } else if (loadState === "error") {
    badge = "Status indisponível";
    headline = "Não foi possível consultar seu plano.";
    description = `${loadError} Nenhuma situação de cobrança foi presumida.`;
    actionLabel = "Tentar novamente";
  } else if (loadState === "demo") {
    badge = "Modo de demonstração";
    headline = "Escolha como contratar a Nexus.";
    description = "A conta ativa abre o checkout seguro da InfinitePay com o plano e o período selecionados.";
    actionLabel = "Simular checkout";
  } else if (paid) {
    badge = "Plano ativo";
    headline = `Nexus ${activePlan} ${activeInterval} ativo.`;
    description = activeUntil
      ? `Pagamento confirmado. Seu acesso está liberado até ${activeUntil}. A renovação é manual e pode ser feita antecipadamente.`
      : "Pagamento confirmado. Você pode renovar manualmente quando desejar.";
    actionLabel = managementAvailable ? "Gerenciar assinatura" : "Renovar acesso";
    actionEndpoint = managementAvailable ? "portal" : "checkout";
  } else if (trialing) {
    badge = trialLabel;
    headline = "Seu teste grátis está em andamento.";
    description = "Use todos os recursos por 3 dias. Ao contratar, o período pago começa imediatamente após a confirmação e funciona separadamente do teste.";
    actionLabel = "Contratar agora";
  } else if (expiredTrial) {
    badge = "Teste encerrado";
    headline = "Seu período gratuito terminou.";
    description = "Escolha um plano e conclua o pagamento para reativar a IA e as automações.";
  } else if (expiredPaidPlan) {
    badge = "Plano vencido";
    headline = "Renove para reativar seu acesso.";
    description = "A renovação é manual. Escolha novamente o plano e o período para gerar uma nova cobrança.";
    actionLabel = "Renovar acesso";
  } else if (paymentIssue) {
    badge = "Pagamento não confirmado";
    headline = "Gere uma nova cobrança segura.";
    description = "Escolha o plano desejado e tente novamente pelo checkout da InfinitePay.";
    actionLabel = "Tentar pagamento novamente";
  } else if (status === "canceled") {
    badge = "Plano encerrado";
    headline = "Contrate novamente quando quiser continuar.";
    description = "Escolha um plano para gerar uma nova cobrança. A renovação não acontece automaticamente.";
    actionLabel = "Contratar novamente";
  } else if (status === "incomplete") {
    badge = "Checkout não concluído";
    headline = "Conclua a contratação do seu plano.";
    description = "Revise o plano e o período antes de seguir para o checkout seguro.";
    actionLabel = "Continuar pagamento";
  }

  const trialStepDone = trialing || expiredTrial || paid || paymentIssue || status === "canceled" || expiredPaidPlan;
  const trialStepDetail = loadState === "loading"
    ? "Consultando período gratuito..."
    : loadState === "error"
      ? "Situação temporariamente indisponível"
      : loadState === "demo"
        ? "Teste independente da contratação"
        : trialing
          ? trialLabel
          : "Teste separado do plano pago";
  const subscriptionStepDetail = paid
    ? `${activePlan} ${activeInterval}${activeUntil ? ` até ${activeUntil}` : ""}`
    : expiredPaidPlan
      ? "Período pago encerrado; renovação manual"
      : "Mensal ou anual pelo checkout seguro";

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
          <span><Sparkle weight="fill"/> PLANOS NEXUS</span>
          <strong className={paid || trialing ? "active" : "pending"}>{badge}</strong>
        </div>
        <h2>{headline}</h2>
        <p>{description}</p>
        {trialing && billing?.trial_ends_at && <div className="trial-deadline"><Clock weight="duotone"/><span><strong>Teste válido até</strong>{new Intl.DateTimeFormat("pt-BR", { dateStyle: "long", timeStyle: "short" }).format(new Date(billing.trial_ends_at))}</span></div>}
        <div className="billing-trial-separate"><Clock weight="duotone"/><span><strong>Teste e contratação são separados</strong>Os 3 dias grátis servem somente para experimentar. O plano pago começa quando o pagamento é aprovado.</span></div>

        {actionEndpoint === "checkout" && loadState !== "loading" && loadState !== "error" && <div className="billing-selector">
          <div className="billing-cycle-toggle" aria-label="Período de cobrança">
            <button type="button" className={interval === "monthly" ? "active" : ""} onClick={() => setInterval("monthly")}>Mensal</button>
            <button type="button" className={interval === "annual" ? "active" : ""} onClick={() => setInterval("annual")}>Anual <small>Economize 25%</small></button>
          </div>
          <div className="billing-plan-options">
            {(Object.keys(BILLING_OFFERS) as PlanCode[]).map((code) => {
              const offer = BILLING_OFFERS[code];
              const price = interval === "annual" ? offer.annual : offer.monthly;
              return <button type="button" key={code} className={plan === code ? "active" : ""} onClick={() => setPlan(code)}>
                <span><strong>{offer.name}</strong><small>{offer.description}</small></span>
                <b>{formatMoney(price)}<small>/{interval === "annual" ? "ano" : "mês"}</small></b>
                {interval === "annual" && <em>equivale a {formatMoney(price / 12)}/mês</em>}
              </button>;
            })}
          </div>
          <div className="billing-order-summary">
            <span><small>Você selecionou</small><strong>Nexus {selectedOffer.name} · {interval === "annual" ? "Anual" : "Mensal"}</strong></span>
            <b>{formatMoney(selectedPrice)}<small>{interval === "annual" ? " à vista ou em até 12x" : " por 1 mês"}</small></b>
          </div>
        </div>}

        <div className="plan-features"><span><Check weight="bold"/> Pix ou cartão</span><span><Check weight="bold"/> Sem renovação automática</span><span><Check weight="bold"/> Taxas do cartão não repassadas</span><span><Check weight="bold"/> Ativação após confirmação segura</span></div>
        <button className="button" onClick={handlePrimaryAction} disabled={busy || loadState === "loading"}>{busy ? "Abrindo InfinitePay..." : actionLabel}<CaretRight/></button>
        {message && <small className="billing-message">{message}</small>}
      </div>
      <aside className="billing-side">
        <div className="billing-status-card">
          <span>SUA JORNADA</span>
          <ol>
            <li className="done"><i><Check/></i><div><strong>E-mail confirmado</strong><small>Conta e empresa verificadas</small></div></li>
            <li className={trialStepDone ? "done" : ""}><i>{trialStepDone ? <Check/> : "2"}</i><div><strong>3 dias grátis</strong><small>{trialStepDetail}</small></div></li>
            <li className={paid ? "done" : loadState === "ready" || loadState === "demo" ? "current" : ""}><i>{paid ? <Check/> : "3"}</i><div><strong>Plano pago</strong><small>{subscriptionStepDetail}</small></div></li>
            <li><i>4</i><div><strong>WhatsApp e ativação</strong><small>Conecte seu número oficial pela YCloud</small></div></li>
          </ol>
        </div>
        <div className="billing-security"><CreditCard weight="duotone"/><span><strong>Pagamento pela InfinitePay</strong>Pix ou cartão em ambiente seguro. No plano anual, o cartão pode ser parcelado em até 12 vezes.</span></div>
      </aside>
    </section>
  );
}
