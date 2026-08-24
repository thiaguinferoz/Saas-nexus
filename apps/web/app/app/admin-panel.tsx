"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Buildings,
  ChatCircleText,
  CheckCircle,
  CaretDown,
  CaretUp,
  ClockCountdown,
  CreditCard,
  MagnifyingGlass,
  ShieldCheck,
  UsersThree,
  WhatsappLogo,
} from "@phosphor-icons/react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/v1";

type AdminSummary = {
  total_tenants: number;
  operational_tenants: number;
  active_subscriptions: number;
  trialing_subscriptions: number;
  connected_whatsapp: number;
  open_support_tickets: number;
};

type AdminTenant = {
  id: string;
  name: string;
  slug: string;
  status: string;
  owner_email: string | null;
  subscription_status: string | null;
  trial_ends_at: string | null;
  whatsapp_status: string | null;
  created_at: string;
};

type AdminTicket = {
  id: string;
  tenant_name: string;
  category: string;
  priority: string;
  status: string;
  subject: string;
  message: string;
  preferred_channel: string;
  contact_value: string | null;
  created_at: string;
};

type AdminOverview = {
  summary: AdminSummary;
  tenants: AdminTenant[];
  support_tickets: AdminTicket[];
};

const tenantStatusLabels: Record<string, string> = {
  pending_payment: "Pagamento pendente",
  provisioning: "Provisionando",
  awaiting_whatsapp: "Aguardando WhatsApp",
  active: "Ativo",
  grace_period: "Carência",
  suspended: "Suspenso",
  canceled: "Cancelado",
};

const subscriptionLabels: Record<string, string> = {
  pending: "Pendente",
  incomplete: "Checkout incompleto",
  trialing: "Teste grátis",
  active: "Assinante",
  past_due: "Pagamento atrasado",
  unpaid: "Não pago",
  canceled: "Cancelada",
};

const ticketStatusLabels: Record<string, string> = {
  open: "Aberto",
  in_progress: "Em atendimento",
  resolved: "Resolvido",
};

function readCookie(name: string) {
  return document.cookie
    .split("; ")
    .find((row) => row.startsWith(`${name}=`))
    ?.split("=")[1] ?? "";
}

function formatDate(value: string | null) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(value));
}

export function AdminPanel() {
  const [data, setData] = useState<AdminOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [updatingTicket, setUpdatingTicket] = useState("");
  const [openedTicket, setOpenedTicket] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await fetch(`${API_URL}/admin/overview`, {
        credentials: "include",
        cache: "no-store",
      });
      const body = await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(body?.detail ?? "Não foi possível carregar a administração.");
      }
      setData(body);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Erro inesperado.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const tenants = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return data?.tenants ?? [];
    return (data?.tenants ?? []).filter(
      (tenant) =>
        tenant.name.toLowerCase().includes(term) ||
        tenant.owner_email?.toLowerCase().includes(term) ||
        tenant.slug.toLowerCase().includes(term),
    );
  }, [data?.tenants, search]);

  async function updateTicket(ticket: AdminTicket, status: string) {
    setUpdatingTicket(ticket.id);
    setError("");
    try {
      const response = await fetch(`${API_URL}/admin/support/tickets/${ticket.id}`, {
        method: "PATCH",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": decodeURIComponent(readCookie("csrf_token")),
        },
        body: JSON.stringify({ status }),
      });
      const body = await response.json().catch(() => null);
      if (!response.ok) throw new Error(body?.detail ?? "Não foi possível atualizar o chamado.");
      setData((current) =>
        current
          ? {
              ...current,
              support_tickets: current.support_tickets.map((item) =>
                item.id === ticket.id ? body : item,
              ),
            }
          : current,
      );
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Erro inesperado.");
    } finally {
      setUpdatingTicket("");
    }
  }

  if (loading) {
    return <div className="admin-loading">Preparando a central administrativa...</div>;
  }

  if (error && !data) {
    return (
      <section className="admin-empty">
        <ShieldCheck weight="duotone" />
        <h2>Não foi possível abrir a administração</h2>
        <p>{error}</p>
        <button type="button" onClick={() => void load()}>Tentar novamente</button>
      </section>
    );
  }

  if (!data) return null;

  const metrics = [
    { icon: Buildings, label: "Empresas cadastradas", value: data.summary.total_tenants, detail: `${data.summary.operational_tenants} em operação` },
    { icon: CreditCard, label: "Assinaturas ativas", value: data.summary.active_subscriptions, detail: `${data.summary.trialing_subscriptions} em teste grátis` },
    { icon: WhatsappLogo, label: "WhatsApps conectados", value: data.summary.connected_whatsapp, detail: "Números oficiais ativos" },
    { icon: ChatCircleText, label: "Chamados pendentes", value: data.summary.open_support_tickets, detail: "Abertos ou em atendimento" },
  ];

  return (
    <section className="admin-view">
      <div className="admin-banner">
        <span><ShieldCheck weight="duotone" /></span>
        <div><small>AMBIENTE PROTEGIDO</small><h2>Operação Nexus em uma única visão</h2><p>Dados consolidados de clientes, ativação, cobrança e suporte. Somente administradores autorizados visualizam esta área.</p></div>
        <b><i /> Tempo real</b>
      </div>

      {error && <div className="panel-error">{error}</div>}

      <div className="admin-metrics">
        {metrics.map(({ icon: Icon, label, value, detail }) => (
          <article key={label}>
            <span><Icon weight="duotone" /></span>
            <div><small>{label}</small><strong>{value}</strong><p>{detail}</p></div>
          </article>
        ))}
      </div>

      <div className="admin-layout">
        <article className="module-card admin-clients">
          <div className="admin-section-head">
            <div><span><UsersThree weight="duotone" /></span><div><h2>Clientes e workspaces</h2><p>Acompanhe os estágios de ativação de cada empresa.</p></div></div>
            <label><MagnifyingGlass /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Buscar empresa ou e-mail" /></label>
          </div>
          <div className="admin-table-wrap">
            <div className="admin-table admin-table-head"><span>Empresa</span><span>Plano</span><span>WhatsApp</span><span>Criada em</span></div>
            {tenants.map((tenant) => (
              <div className="admin-table admin-table-row" key={tenant.id}>
                <span><strong>{tenant.name}</strong><small>{tenant.owner_email ?? tenant.slug}</small><em className={`state-${tenant.status}`}>{tenantStatusLabels[tenant.status] ?? tenant.status}</em></span>
                <span><strong>{subscriptionLabels[tenant.subscription_status ?? ""] ?? "Sem plano"}</strong><small>{tenant.subscription_status === "trialing" ? `Termina em ${formatDate(tenant.trial_ends_at)}` : "Status da cobrança"}</small></span>
                <span className={tenant.whatsapp_status === "connected" ? "connected" : "pending"}><i />{tenant.whatsapp_status === "connected" ? "Conectado" : "Pendente"}</span>
                <time>{formatDate(tenant.created_at)}</time>
              </div>
            ))}
            {!tenants.length && <div className="admin-no-results">Nenhum cliente encontrado.</div>}
          </div>
        </article>

        <aside className="module-card admin-tickets">
          <div className="admin-section-head compact"><div><span><ClockCountdown weight="duotone" /></span><div><h2>Suporte recente</h2><p>Priorize solicitações da plataforma.</p></div></div></div>
          <div className="admin-ticket-list">
            {data.support_tickets.slice(0, 8).map((ticket) => (
              <article key={ticket.id} className={openedTicket === ticket.id ? "open" : ""}>
                <button
                  type="button"
                  className="admin-ticket-open"
                  aria-expanded={openedTicket === ticket.id}
                  onClick={() => setOpenedTicket((current) => current === ticket.id ? "" : ticket.id)}
                >
                  <span>
                    <header><span>{ticket.tenant_name}</span><b className={ticket.priority === "high" ? "high" : ""}>{ticket.priority === "high" ? "ALTA" : "NORMAL"}</b></header>
                    <h3>{ticket.subject}</h3>
                  </span>
                  {openedTicket === ticket.id ? <CaretUp /> : <CaretDown />}
                </button>
                <p>{formatDate(ticket.created_at)} · {ticket.preferred_channel}</p>
                {openedTicket === ticket.id && (
                  <div className="admin-ticket-details">
                    <strong>Mensagem</strong>
                    <p>{ticket.message}</p>
                    <dl>
                      <div><dt>Canal de retorno</dt><dd>{ticket.preferred_channel}</dd></div>
                      <div><dt>Contato</dt><dd>{ticket.contact_value || "Pela plataforma"}</dd></div>
                    </dl>
                  </div>
                )}
                <label>
                  <CheckCircle />
                  <select value={ticket.status} disabled={updatingTicket === ticket.id} onChange={(event) => void updateTicket(ticket, event.target.value)}>
                    <option value="open">{ticketStatusLabels.open}</option>
                    <option value="in_progress">{ticketStatusLabels.in_progress}</option>
                    <option value="resolved">{ticketStatusLabels.resolved}</option>
                  </select>
                </label>
              </article>
            ))}
            {!data.support_tickets.length && <div className="admin-no-results">Nenhum chamado aberto.</div>}
          </div>
        </aside>
      </div>
    </section>
  );
}
