# Prompt Estruturado — Assistente RAG NovaTech

## Papel

Você é um engenheiro de software sênior especializado em LLMs e sistemas RAG (Retrieval-Augmented Generation). Sua expertise inclui arquitetura de pipelines de ingestão documental, estratégias de chunking, context engineering e integração com ambientes Microsoft Azure.

---

## Contexto do Projeto

A **DB1** foi contratada pela **NovaTech** — empresa de logística com 1.200 funcionários — para construir um assistente de IA voltado à equipe de atendimento ao cliente (45 pessoas).

**Problema central:** os atendentes gastam em média **12 minutos por chamado** buscando informações em documentação dispersa para responder dúvidas sobre prazos, regras de frete, políticas de devolução e procedimentos de reclamação. Isso gera atrasos, respostas inconsistentes e frustração.

**Meta:** reduzir o tempo médio de busca de 12 minutos para **menos de 2 minutos** por chamado, com respostas em linguagem natural fundamentadas na documentação oficial e com indicação de fonte.

---

## Fontes de Conhecimento

| Fonte | Qtde | Formato | Atualização | Responsável |
|---|---|---|---|---|
| SharePoint corporativo | ~800 docs | PDF, DOCX | Mensal | Operações, Compliance |
| Confluence (wiki interna) | ~400 páginas | HTML/Wiki | Semanal | TI, Comercial |
| Pasta de rede | ~50 planilhas | XLSX | Mensal | Comercial |

---

## Restrições e Complexidades Técnicas

**Documentação:**
- PDFs do SharePoint contêm tabelas complexas (15+ colunas), fluxogramas embutidos como imagens e documentos escaneados (OCR necessário)
- Wiki do Confluence usa macros customizadas e links internos entre páginas
- Planilhas XLSX possuem fórmulas interdependentes

**Processo e governança:**
- 3 áreas atualizam a documentação de forma independente, sem revisão unificada
- Existem contradições entre versões de documentos — resolvidas hoje de forma informal
- Volume operacional: 320 chamados/dia, dos quais ~60% exigem consulta documental

**Infraestrutura disponível:**
- Licenças Microsoft 365 E3 já provisionadas
- Azure AI Services disponível para uso
- Integração requerida com Microsoft Teams e SharePoint
- Prazo: 3 meses (discovery + desenvolvimento + go-live)

---

## Conceito Técnico de Referência

> *"O contexto que o LLM recebe a cada pergunta é limitado pela janela de contexto do modelo. A qualidade da resposta depende de: quais chunks são selecionados (relevância), quantos chunks cabem no contexto (orçamento de atenção), onde ficam posicionados no prompt (efeito 'lost in the middle' — informação no meio de contextos longos tende a ser negligenciada pelo modelo), e o que mais está no contexto competindo por atenção (system prompt, histórico de conversa, instruções)."*

---

## Tarefa

Com base em todo o contexto acima, execute as seguintes etapas:

### 1. Análise Técnica do Pipeline RAG

#### 1.1 Desafios por Tipo de Fonte

Para cada tipo de fonte listado abaixo, detalhe:
- O **desafio específico** que representa para o pipeline de RAG
- Como esse desafio **afeta a qualidade das respostas**
- A **estratégia de tratamento** recomendada

Fontes a analisar:
- PDFs com tabelas complexas (15+ colunas)
- PDFs escaneados (requerem OCR)
- Wiki do Confluence com links internos e macros customizadas
- Planilhas XLSX com fórmulas interdependentes

#### 1.2 Estimativa do Tamanho da Base em Tokens

Calcule o volume total estimado da base de conhecimento em tokens, considerando:
- ~800 documentos PDF com média de 10 páginas cada
- ~400 páginas wiki com média de 1.500 palavras cada
- ~50 planilhas (estime um volume razoável de conteúdo textual)

> Regra prática: **1 token ≈ 0,75 palavras** (ou ~1,33 tokens por palavra)

#### 1.3 Análise de Orçamento de Contexto

Dado que:
- O modelo **GPT-4o** possui janela de contexto de **128K tokens**
- O system prompt + instruções consomem aproximadamente **2K tokens**
- Chunks terão tamanho aproximado de **500 tokens**

Responda:
- Quantos chunks cabem por query dentro do orçamento disponível?
- Como essa limitação afeta a estratégia de chunking e retrieval?
- Quais trade-offs surgem ao aumentar ou diminuir o tamanho dos chunks?

#### 1.4 Recomendação de Estratégia de Chunking

Proponha e justifique uma estratégia de chunking considerando:
- Os **tipos de perguntas** que os atendentes farão (ex: busca de regras pontuais, comparação de políticas, consulta a tabelas de valores)
- O efeito **"lost in the middle"** — tendência dos LLMs a negligenciar informações posicionadas no meio de contextos longos
- A heterogeneidade dos formatos de origem (PDF, wiki, planilha)

---

### 2. Revisão Crítica da Análise

Após concluir a análise acima, conduza uma **revisão crítica** do próprio documento:

- Identifique **pontos fracos** na argumentação ou nas recomendações
- Aponte **estimativas otimistas demais** que possam não se sustentar na prática
- Liste **riscos não considerados** que podem comprometer o pipeline ou os resultados esperados
- Incorpore os ajustes necessários diretamente na análise, sinalizando o que foi revisado
