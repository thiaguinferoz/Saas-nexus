import type { Metadata } from "next";
import { LegalPage } from "../shared/legal-page";

export const metadata: Metadata = {
  title: "Política de Privacidade | Nexus",
  description: "Saiba como a Nexus trata e protege dados pessoais.",
};

const sections = [
  {
    title: "Quem somos e a quem esta política se aplica",
    content: <><p>A Nexus é responsável pela plataforma disponível em usenexusia.com e pelos dados pessoais tratados para administrar contas, contratos, suporte, segurança e relacionamento com clientes.</p><p>Quando uma empresa usa a Nexus para atender seus próprios contatos, essa empresa normalmente decide as finalidades do tratamento e atua como controladora. Nessa situação, a Nexus atua como operadora, tratando os dados conforme as instruções legítimas do cliente e o contrato.</p></>,
  },
  {
    title: "Dados que tratamos",
    content: <><p>Podemos tratar nome, e-mail, empresa, credenciais protegidas, preferências da conta, informações de suporte e dados relacionados ao plano e às transações de pagamento.</p><p>Para prestar o serviço, também podemos tratar números de telefone, identificadores do WhatsApp, mensagens e mídias, configurações da IA, horários, regras, catálogos, documentos e demais conteúdos inseridos pelo cliente. Dados técnicos podem incluir endereço IP, registros de acesso, dispositivo, navegador, data, horário e eventos de segurança.</p></>,
  },
  {
    title: "Como coletamos os dados",
    content: <><p>Os dados são fornecidos diretamente por você ao criar uma conta, configurar a plataforma, importar conteúdo, conectar o WhatsApp, contratar um plano ou solicitar suporte.</p><p>Também recebemos informações das integrações ativadas pelo cliente, como Meta/WhatsApp, YCloud, provedores de pagamento e serviços técnicos, além de registros gerados automaticamente durante o uso da plataforma.</p></>,
  },
  {
    title: "Finalidades e bases legais",
    content: <><p>Tratamos dados para criar e autenticar contas; executar o contrato; processar pagamentos; conectar canais; automatizar atendimentos; prestar suporte; prevenir fraude e incidentes; cumprir obrigações legais; exercer direitos; manter e aprimorar a plataforma.</p><p>Conforme o contexto, o tratamento pode se fundamentar na execução de contrato ou procedimentos preliminares, cumprimento de obrigação legal, exercício regular de direitos, legítimo interesse ou consentimento. Quando o consentimento for necessário, ele poderá ser revogado pelos canais indicados nesta política.</p></>,
  },
  {
    title: "Compartilhamento e operadores",
    content: <><p>Compartilhamos somente os dados necessários com fornecedores que apoiam a operação, como hospedagem e banco de dados, Redis e filas, n8n, Meta/WhatsApp, YCloud, envio de e-mails, cobrança e pagamento, monitoramento e suporte.</p><p>Também podemos compartilhar dados para cumprir lei, ordem judicial ou requisição válida de autoridade; investigar fraude ou incidentes; proteger direitos; ou viabilizar reorganização societária, com as salvaguardas aplicáveis. Não comercializamos dados pessoais.</p></>,
  },
  {
    title: "Transferências internacionais",
    content: <><p>Alguns fornecedores podem tratar dados em outros países. Nessas situações, buscamos utilizar mecanismos admitidos pela LGPD e medidas contratuais, técnicas e organizacionais adequadas, limitando a transferência ao necessário para as finalidades informadas.</p></>,
  },
  {
    title: "Retenção e exclusão",
    content: <><p>Mantemos os dados pelo tempo necessário para prestar o serviço, cumprir o contrato, atender obrigações legais, prevenir fraude e exercer direitos. Os prazos variam conforme a categoria do dado e a finalidade.</p><p>Após o encerramento, dados podem ser eliminados ou anonimizados, salvo quando a conservação for necessária ou permitida por lei. Cópias de segurança são descartadas conforme os ciclos técnicos de retenção.</p></>,
  },
  {
    title: "Segurança",
    content: <><p>Adotamos medidas técnicas e administrativas destinadas a proteger dados contra acesso não autorizado e situações acidentais ou ilícitas, incluindo controle de acesso, autenticação, segregação por cliente, proteção de credenciais, registros de operação, redes internas e rotinas de atualização.</p><p>Nenhum ambiente é totalmente imune a riscos. Em caso de incidente relevante, adotaremos medidas de contenção e as comunicações exigidas pela legislação.</p></>,
  },
  {
    title: "Cookies e tecnologias semelhantes",
    content: <><p>Utilizamos cookies estritamente necessários para autenticação, segurança, prevenção de fraude e funcionamento da sessão. Poderemos utilizar métricas de uso para compreender o desempenho da plataforma, respeitando as escolhas do usuário e a legislação aplicável.</p><p>Bloquear cookies essenciais pode impedir o funcionamento do login e de áreas protegidas.</p></>,
  },
  {
    title: "Seus direitos",
    content: <><p>Nos termos da LGPD, você pode solicitar confirmação de tratamento, acesso, correção, anonimização, bloqueio ou eliminação quando aplicável, portabilidade, informações sobre compartilhamento, revisão de decisões automatizadas e revogação do consentimento.</p><p>Podemos solicitar informações para confirmar a identidade e proteger os dados antes de atender ao pedido. Quando a Nexus atuar apenas como operadora, encaminharemos ou auxiliaremos o controlador responsável.</p></>,
  },
  {
    title: "Crianças e adolescentes",
    content: <><p>A Nexus é destinada a empresas e profissionais e não foi projetada para cadastro direto por crianças. O cliente deve evitar inserir dados de crianças e adolescentes sem necessidade, base legal e medidas de proteção compatíveis com o melhor interesse desses titulares.</p></>,
  },
  {
    title: "Contato e atualizações",
    content: <><p>Pedidos relacionados a dados pessoais e dúvidas sobre esta política podem ser enviados para contato@usenexusia.com. Informe dados suficientes para que possamos localizar a conta e responder com segurança.</p><p>Esta política poderá ser atualizada para refletir mudanças legais, técnicas ou operacionais. Alterações relevantes serão comunicadas pelos canais disponíveis, e a versão vigente permanecerá publicada nesta página.</p></>,
  },
];

export default function PrivacyPage() {
  return <LegalPage eyebrow="PRIVACIDADE FAZ PARTE DO PRODUTO" title="Política de Privacidade" summary="Aqui explicamos, de forma objetiva, quais dados a Nexus trata, por que os utiliza e como você pode exercer seus direitos." sections={sections} />;
}
