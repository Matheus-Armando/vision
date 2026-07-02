[25/06/26, 19:31:13] Matheus Chioquetta: É só as 8 e 40 a prova né
[01/07/26, 20:19:20] ~Gui Kruger: Desenvolva um MVP de alta fidelidade (apenas frontend, com dados mockados) de uma plataforma SaaS chamada provisoriamente VisionFlow.

O objetivo não é criar um produto funcional, mas sim um protótipo navegável para validar a ideia, gerar insights e apresentar o conceito.

Conceito

A plataforma transforma eventos capturados por câmeras em informações estruturadas e automações.

Em vez de depender de alguém para observar o ambiente e registrar informações manualmente, a IA identifica objetos, pessoas, documentos ou situações através da câmera e gera eventos que alimentam sistemas de gestão.

A ideia é que a câmera se torne uma nova fonte de dados para a empresa.

Fluxo principal:

Câmera → IA identifica → Evento → Regras → Automação → Dashboard

---

Problema que resolve

Empresas possuem inúmeros processos físicos que dependem da observação humana.

Funcionários precisam:

•⁠  ⁠contar produtos;
•⁠  ⁠conferir estoque;
•⁠  ⁠verificar uso de EPIs;
•⁠  ⁠registrar documentos;
•⁠  ⁠acompanhar movimentações;
•⁠  ⁠fiscalizar ambientes;
•⁠  ⁠preencher planilhas.

Esses processos são lentos, caros e sujeitos a erros.

A plataforma elimina parte desse trabalho transformando o que a câmera vê em dados acionáveis.

---

Público

O sistema deve ser genérico, atendendo diversos segmentos:

•⁠  ⁠logística
•⁠  ⁠indústria
•⁠  ⁠hospitais
•⁠  ⁠varejo
•⁠  ⁠construção
•⁠  ⁠agricultura
•⁠  ⁠escritórios
•⁠  ⁠condomínios
•⁠  ⁠oficinas
•⁠  ⁠almoxarifados

Evite deixar o design preso a um único nicho.

---

Objetivo do MVP

Criar uma interface que faça alguém entender o conceito em poucos minutos.

Tudo deve ser mockado.

Não é necessário backend.

Não é necessário login funcional.

Não é necessário IA real.

Quero apenas uma experiência convincente.

---

Estilo

Visual moderno.

Minimalista.

Tema escuro.

Inspirado em produtos como:

•⁠  ⁠Linear
•⁠  ⁠Notion
•⁠  ⁠Vercel
•⁠  ⁠Stripe Dashboard
•⁠  ⁠Cursor
•⁠  ⁠OpenAI

Utilizar bastante espaço em branco, cartões, animações suaves e aparência premium.

---

Estrutura

Dashboard

Mostrar indicadores como:

•⁠  ⁠Eventos detectados hoje
•⁠  ⁠Automações executadas
•⁠  ⁠Precisão da IA
•⁠  ⁠Câmeras conectadas
•⁠  ⁠Eventos pendentes
•⁠  ⁠Tempo médio de processamento

Adicionar gráficos fictícios.

---

Tela "Eventos"

Lista cronológica contendo registros como:

•⁠  ⁠Capacete detectado
•⁠  ⁠Documento identificado
•⁠  ⁠Prateleira vazia
•⁠  ⁠Produto abaixo do estoque mínimo
•⁠  ⁠Veículo entrou
•⁠  ⁠Pessoa entrou em área restrita
•⁠  ⁠Equipamento removido
•⁠  ⁠Caixa identificada
•⁠  ⁠Máquina parada

Cada evento deve possuir:

•⁠  ⁠horário
•⁠  ⁠câmera
•⁠  ⁠confiança (%)
•⁠  ⁠categoria
•⁠  ⁠status
•⁠  ⁠ação executada

---

Tela "Câmeras"

Exibir diversas câmeras fictícias.

Cada câmera mostra uma imagem ilustrativa e informações como:

•⁠  ⁠online/offline
•⁠  ⁠FPS
•⁠  ⁠última detecção
•⁠  ⁠quantidade de eventos
•⁠  ⁠localização

Ao clicar em uma câmera, abrir detalhes.

---

Tela "Visão da IA"

Simular a análise em tempo real.

Mostrar uma imagem mockada com caixas delimitadoras (bounding boxes) indicando:

Pessoa

Capacete

Notebook

Caixa

Pallet

Documento

Ferramenta

Produto

Veículo

Ao lado, exibir uma lista com as detecções e o nível de confiança.

---

Tela "Regras"

Essa é uma das partes mais importantes.

Criar um construtor visual semelhante ao n8n, Zapier ou Make.

Exemplo:

SE

Produto identificado

E

Quantidade menor que 10

ENTÃO

Criar solicitação de compra

Outro exemplo:

SE

Pessoa sem EPI

ENTÃO

Enviar alerta

Outro:

SE

Documento identificado

ENTÃO

Executar OCR

Salvar PDF

Enviar ao ERP

Todos esses fluxos serão apenas ilustrativos.

---

Tela "Automações"

Mostrar automações executadas.

Cada uma contendo:

•⁠  ⁠evento de origem
•⁠  ⁠data
•⁠  ⁠duração
•⁠  ⁠resultado
•⁠  ⁠integração utilizada

---

Tela "Integrações"

Mostrar integrações fictícias com:

•⁠  ⁠ERP
•⁠  ⁠Slack
•⁠  ⁠Microsoft Teams
•⁠  ⁠WhatsApp
•⁠  ⁠Email
•⁠  ⁠Google Drive
•⁠  ⁠API REST
•⁠  ⁠Webhooks

Todas apenas como mock.

---

Tela "Analytics"

Mostrar métricas como:

•⁠  ⁠objetos identificados
•⁠  ⁠categorias mais detectadas
•⁠  ⁠horários com mais eventos
•⁠  ⁠eventos por câmera
•⁠  ⁠economia estimada de horas
•⁠  ⁠redução de erros
•⁠  ⁠precisão por categoria

Tudo ilustrativo.

---

Landing Page

Criar também uma landing page elegante.

Hero principal com um slogan como:

"Transforme o que suas câmeras enxergam em decisões automatizadas."

Adicionar uma animação mostrando o fluxo:

Câmera → IA → Evento → Automação → Resultado

Criar seções:

•⁠  ⁠Problema
•⁠  ⁠Como funciona
•⁠  ⁠Casos de uso
•⁠  ⁠Benefícios
•⁠  ⁠Integrações
•⁠  ⁠Dashboard
•⁠  ⁠CTA final

---

Casos de uso ilustrativos

Mostrar cards como:

Controle de estoque

Controle patrimonial

Segurança do trabalho

Inspeção de qualidade

Controle de documentos

Controle de acesso

Monitoramento industrial

Gestão de ativos

Fiscalização

Logística

---

Componentes importantes

•⁠  ⁠Sidebar moderna
•⁠  ⁠Navbar
•⁠  ⁠Cards
•⁠  ⁠Timeline de eventos
•⁠  ⁠Kanban opcional
•⁠  ⁠Gráficos
•⁠  ⁠Indicadores
•⁠  ⁠Tabelas elegantes
•⁠  ⁠Modais
•⁠  ⁠Toasts simulando novas detecções
•⁠  ⁠Badges coloridas
•⁠  ⁠Breadcrumbs
•⁠  ⁠Busca
•⁠  ⁠Filtros

---

Diferencial

A interface deve comunicar que a plataforma não é apenas um sistema de visão computacional, mas uma plataforma que transforma o mundo físico em dados estruturados e automações configuráveis.

O usuário deve compreender que a IA apenas detecta eventos. O verdadeiro valor está em permitir configurar regras, integrações e ações que automatizam processos de negócio.

Crie uma experiência visual rica, moderna e convincente, utilizando exclusivamente dados mockados, para servir como base de validação da ideia e geração de insights sobre funcionalidades futuras.
