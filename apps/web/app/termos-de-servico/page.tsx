import type { Metadata } from "next";
import { LegalPage } from "../shared/legal-page";

export const metadata: Metadata = {
  title: "Termos de Serviço | Nexus",
  description: "Condições de uso da plataforma Nexus.",
};

const sections = [
  {
    title: "Aceitação e escopo",
    content: <><p>Estes Termos regulam o acesso e o uso da plataforma Nexus, incluindo o painel, as automações, os recursos de inteligência artificial e as integrações disponibilizadas ao cliente.</p><p>Ao criar uma conta, contratar um plano ou utilizar a plataforma, você declara que leu e concorda com estes Termos e com a Política de Privacidade. Se estiver representando uma empresa, declara possuir poderes para vinculá-la a estas condições.</p></>,
  },
  {
    title: "Conta e responsabilidades do cliente",
    content: <><p>Você deve fornecer informações verdadeiras, manter os dados cadastrais atualizados e proteger suas credenciais. A conta não deve ser compartilhada com pessoas não autorizadas.</p><p>O cliente é responsável pelos usuários que autorizar, pelas configurações inseridas no painel e por comunicar imediatamente qualquer suspeita de acesso indevido.</p></>,
  },
  {
    title: "Funcionamento da Nexus",
    content: <><p>A Nexus auxilia empresas a configurar e automatizar atendimentos pelo WhatsApp. A plataforma pode processar mensagens, regras, horários, catálogos, documentos e outras informações fornecidas pelo cliente para executar as funcionalidades contratadas.</p><p>Respostas geradas por inteligência artificial podem conter imprecisões. O cliente deve revisar configurações e informações relevantes, especialmente preços, prazos, orientações profissionais e decisões que produzam efeitos jurídicos, financeiros ou sobre a saúde e segurança de pessoas.</p></>,
  },
  {
    title: "WhatsApp e serviços de terceiros",
    content: <><p>Algumas funcionalidades dependem de serviços de terceiros, incluindo Meta/WhatsApp, YCloud, provedores de hospedagem, automação, e-mail e pagamento. O uso dessas integrações também está sujeito aos termos e políticas dos respectivos fornecedores.</p><p>Alterações, indisponibilidades, bloqueios ou limitações impostas por terceiros podem afetar a plataforma. A Nexus não controla decisões da Meta, do WhatsApp ou de outros fornecedores, mas adotará esforços razoáveis para manter a integração operacional.</p></>,
  },
  {
    title: "Uso aceitável",
    content: <><p>É proibido utilizar a Nexus para fraude, spam, assédio, discriminação, conteúdo ilícito, violação de direitos, coleta indevida de dados, disseminação de malware ou tentativa de acessar contas, dados ou infraestrutura de terceiros.</p><p>O cliente deve possuir base legal e autorizações adequadas para tratar dados e enviar comunicações, respeitando a LGPD, as regras do WhatsApp e a legislação aplicável. Também é responsável pelo conteúdo enviado, importado ou configurado na plataforma.</p></>,
  },
  {
    title: "Teste, planos e pagamentos",
    content: <><p>Quando oferecido, o período gratuito possui a duração informada no momento do cadastro. Após o teste, a continuidade dos recursos pagos depende da contratação de um plano vigente.</p><p>Preços, periodicidade, condições de renovação e meios de pagamento são apresentados antes da contratação. Tributos aplicáveis poderão ser incluídos conforme a legislação. Em caso de atraso, a Nexus poderá limitar recursos após os avisos e prazos de tolerância informados ao cliente.</p></>,
  },
  {
    title: "Cancelamento e encerramento",
    content: <><p>O cliente pode solicitar o cancelamento pelos canais disponibilizados. Valores já pagos seguem as condições apresentadas na contratação e os direitos previstos na legislação do consumidor.</p><p>A Nexus poderá suspender ou encerrar o acesso em caso de violação destes Termos, risco de segurança, fraude, uso ilegal ou inadimplência, assegurando aviso e oportunidade de regularização quando cabível.</p></>,
  },
  {
    title: "Propriedade intelectual",
    content: <><p>A plataforma, o software, a marca, a interface e os materiais da Nexus pertencem à Nexus ou a seus licenciadores. A contratação concede apenas uma licença limitada, revogável, não exclusiva e intransferível para uso da plataforma durante a vigência do serviço.</p><p>O cliente mantém a titularidade sobre os conteúdos que inserir. Ele autoriza o tratamento desses conteúdos apenas na medida necessária para prestar, proteger e melhorar o serviço, conforme a Política de Privacidade.</p></>,
  },
  {
    title: "Disponibilidade e limitações",
    content: <><p>A Nexus empregará esforços razoáveis para manter a plataforma segura e disponível, mas manutenções, falhas de rede, eventos de terceiros e situações fora de controle podem causar interrupções.</p><p>Nada nestes Termos exclui responsabilidades que não possam ser afastadas por lei. Quando permitido, eventuais responsabilidades serão avaliadas conforme os danos diretos comprovados e as circunstâncias do caso.</p></>,
  },
  {
    title: "Privacidade e segurança",
    content: <><p>O tratamento de dados pessoais está descrito na Política de Privacidade. O cliente também pode atuar como controlador dos dados de seus contatos, enquanto a Nexus poderá atuar como operadora conforme as instruções legítimas do cliente.</p><p>As partes devem adotar medidas adequadas de segurança e cooperar no atendimento de obrigações legais e direitos dos titulares.</p></>,
  },
  {
    title: "Alterações e legislação aplicável",
    content: <><p>Estes Termos podem ser atualizados para refletir mudanças legais, técnicas ou comerciais. Alterações relevantes serão comunicadas pelos canais disponíveis e indicarão uma nova data de vigência.</p><p>Aplicam-se as leis da República Federativa do Brasil. Eventuais conflitos serão tratados preferencialmente de forma amigável e, quando houver relação de consumo, será respeitado o foro do domicílio do consumidor.</p></>,
  },
];

export default function TermsPage() {
  return <LegalPage eyebrow="REGRAS CLARAS PARA UMA RELAÇÃO TRANSPARENTE" title="Termos de Serviço" summary="Este documento explica as condições para criar uma conta, contratar e utilizar a plataforma Nexus." sections={sections} />;
}
