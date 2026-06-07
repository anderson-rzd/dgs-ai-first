# Análise Técnica — Pipeline RAG NovaTech

---

## 1. Análise Técnica do Pipeline RAG

### 1.1 Desafios por Tipo de Fonte

---

#### PDFs com tabelas complexas (15+ colunas)

**Desafio específico**

Extratores PDF padrão (PyMuPDF, pdfminer) serializam tabelas de forma linear, destruindo a relação entre cabeçalhos e células. Uma tabela de multiplicadores regionais com 15 colunas vira uma sequência de tokens sem estrutura: `Sul 1.2 Sudeste 1.0 Centro-Oeste 1.3...`. Quando o chunking corta no meio de uma tabela, o chunk resultante contém valores numéricos sem o contexto de qual coluna ou linha pertencem.

Na documentação da NovaTech, a SLA-2024 é um exemplo crítico: a tabela de SLAs tem 3 tiers × 7 métricas. Se serializada linearmente e cortada ao meio, um chunk pode ter os SLAs do Gold mas não do Silver — gerando respostas incompletas para perguntas de comparação entre tiers.

**Impacto na qualidade das respostas**

- Respostas com valores corretos mas sem contexto de qual coluna/linha se aplicam
- Incapacidade de responder perguntas de comparação ("qual a diferença entre Gold e Silver?") se os dados de ambos estão em chunks diferentes
- Retrieval impreciso: o embedding de um chunk com dados de tabela serializada não representa bem o conteúdo semântico

**Estratégia de tratamento**

1. Usar extratores com reconhecimento de estrutura tabular: **pdfplumber** para PDFs nativos, **Azure Document Intelligence** (Layout API) para PDFs complexos ou digitalizados
2. Converter tabelas para Markdown estruturado antes do chunking:
   ```
   | Tier   | Resposta (geral) | Resolução (geral) |
   |--------|-----------------|-------------------|
   | Gold   | 2h úteis        | 24h úteis         |
   | Silver | 4h úteis        | 48h úteis         |
   ```
3. Tratar cada tabela como **chunk indivisível** — independente do tamanho. Se uma tabela ultrapassar 1.000 tokens: dividir por grupos de linhas mas repetir os cabeçalhos em cada sub-chunk
4. Incluir metadado `tipo=tabela` e `domínio=sla|frete|devolução` para orientar o re-ranking

> ⚠️ **[Revisão Crítica — seção 2]** O Azure Document Intelligence resolve tabelas nativas mas tem desempenho inferior em tabelas com células mescladas e formatação irregular — situação comum em documentos legados. O custo por página do Layout API também precisa ser orçado: ~$0,015/página × 8.000 páginas = ~$120 só na primeira ingestão.

---

#### PDFs escaneados (requerem OCR)

**Desafio específico**

Documentos escaneados são imagens — extratores de texto retornam strings vazias ou lixo. O OCR tem taxa de erro que varia conforme qualidade da digitalização (resolução, inclinação, qualidade do original). Fluxogramas e diagramas embutidos como imagens são completamente opacos para qualquer extrator de texto convencional.

No contexto da NovaTech, onde estimamos que ~15% dos 800 PDFs são escaneados (~120 documentos), qualquer erro de OCR se propaga para os embeddings — o modelo não consegue fazer retrieval de termos grafados incorretamente.

**Impacto na qualidade das respostas**

- Documentos críticos parcialmente ilegíveis ou inacessíveis
- Erros de OCR geram tokens com ruído (`pol|tica de devoluç@o`) que não casam semanticamente com queries dos atendentes
- Fluxogramas com lógica de decisão (ex: "se carga perigosa → ramal 4500") ficam invisíveis para o pipeline

**Estratégia de tratamento**

1. **Triagem antes do OCR:** detectar PDFs escaneados automaticamente (verificar se o PDF tem camada de texto; se não, marcar para OCR)
2. **Azure AI Document Intelligence Read API** para OCR de qualidade — já disponível na infraestrutura da NovaTech
3. **Para fluxogramas:** usar GPT-4o Vision (ou Azure OpenAI com visão) para gerar descrição textual estruturada do fluxograma, incluída como chunk extra com metadado `tipo=fluxograma_descrito`
4. **Validação de qualidade pós-OCR:** calcular densidade de caracteres especiais e palavras fora do vocabulário esperado; documentos com baixa confiança entram em fila de revisão humana
5. **Não indexar lixo:** criar threshold de confiança (ex: < 80% de caracteres válidos → descartar o trecho, não indexar)

> ⚠️ **[Revisão Crítica — seção 2]** A estratégia de GPT-4o Vision para fluxogramas é cara e lenta para 120 documentos com múltiplos diagramas. Recomendo priorizar: identificar quais fluxogramas contêm informação crítica para atendimento (não todos os diagramas precisam ser descritos).

---

#### Wiki do Confluence com links internos e macros customizadas

**Desafio específico**

A API REST do Confluence retorna conteúdo em formato HTML com tags de macro (`<ac:structured-macro>`) que não são texto utilizável. Links internos entre páginas (`<a href="/wiki/spaces/...">ver PROC-042</a>`) criam dependências que um chunk isolado não resolve — o atendente pergunta algo que a wiki responde com "conforme descrito em outra página", e o pipeline não sabe que precisa buscar aquela outra página também.

Macros dinâmicas (como listas de documentos recentes, calendários) geram conteúdo que fica obsoleto imediatamente após a ingestão.

**Impacto na qualidade das respostas**

- Chunks com referências não resolvidas geram respostas incompletas ("Para mais detalhes, consulte a página X" — mas X não está no contexto)
- Macros não parseadas injetam HTML bruto nos chunks, contaminando os embeddings
- Conteúdo dinâmico indexado em T+0 fica desatualizado em T+1, gerando respostas com informações antigas

**Estratégia de tratamento**

1. **Extrair via API com expansão:** usar o endpoint `GET /rest/api/content/{id}?expand=body.storage` e processar o formato XML de armazenamento (mais limpo que o HTML renderizado)
2. **Parser de macros:** implementar parser que: remove macros de conteúdo dinâmico (recent pages, user mentions), substitui macros de código por seu conteúdo textual, converte macros de tabela para Markdown
3. **Resolução de links internos:** ao extrair uma página, seguir os links internos e incluir um resumo (primeiros 2 parágrafos) da página linkada como contexto no chunk — ou indexar todas as páginas linkadas e usar graph-based retrieval
4. **Metadados de versão:** usar o campo `version.number` e `history.lastUpdated` da API para rastrear mudanças e reindexar apenas páginas alteradas

> ⚠️ **[Revisão Crítica — seção 2]** A resolução de links internos pode gerar explosão de conteúdo: uma página pode linkar para 10 outras, cada uma linkando para mais 10. É necessário definir um limite de profundidade (ex: apenas 1 nível de links) e implementar deduplicação para evitar que o mesmo conteúdo apareça em múltiplos chunks.

---

#### Planilhas XLSX com fórmulas interdependentes

**Desafio específico**

Extratores de planilha (openpyxl, pandas) que leem apenas valores calculados perdem a relação entre fórmulas e seus insumos — é impossível saber se um valor de R$ 1.234 é fixo ou derivado de outra célula. Planilhas com referências externas (`\\novatech-fs\comercial\tabelas\frete-base-AAAAMM.xlsx`) criam dependências que o pipeline não consegue resolver automaticamente. Abas sem cabeçalhos explícitos produzem chunks com dados sem contexto.

**Impacto na qualidade das respostas**

- Um chunk com `1.8` não tem significado sem saber que é o multiplicador regional Norte da PROC-042-v2
- Se a planilha referenciada externamente mudar e não for reingerida, o pipeline responde com valores desatualizados sem saber disso
- Tabelas com cabeçalhos em linhas (em vez de colunas) confundem a serialização

**Estratégia de tratamento**

1. **Extrair valores calculados** (não fórmulas) com openpyxl, ativando `data_only=True`
2. **Obrigatoriedade de cabeçalhos:** para cada aba, incluir sempre os cabeçalhos de linha e coluna em cada chunk gerado — nunca extrair apenas os valores
3. **Converter para Markdown tabular** antes do chunking:
   ```
   ## Aba: Multiplicadores Regionais (frete-base-202401.xlsx)
   | Região       | Multiplicador |
   |--------------|---------------|
   | Norte        | 1.8           |
   | Nordeste     | 1.5           |
   ```
4. **Documentar dependências externas como metadados:** se a planilha referencia outro arquivo, registrar isso e incluir no pipeline de ingestão
5. **Rejeitar planilhas com referências externas não resolvidas:** alertar o operador ao invés de indexar com dados possivelmente incorretos

> ⚠️ **[Revisão Crítica — seção 2]** As 50 planilhas atualizadas mensalmente exigem reingestão automática. A atualização manual é risco operacional alto — se um comercial atualizar a tabela de fretes e o pipeline não for acionado, o assistente responderá com valores desatualizados com total confiança.

---

### 1.2 Estimativa do Tamanho da Base em Tokens

| Fonte | Qtde | Vol. Estimado | Palavras | Tokens (~1,33/palavra) |
|-------|------|---------------|----------|------------------------|
| PDFs SharePoint | 800 docs × 10 pág. | 8.000 páginas | 2.400.000¹ | **3.192.000** |
| Wiki Confluence | 400 páginas | — | 600.000 | **798.000** |
| Planilhas XLSX | 50 planilhas | — | 200.000² | **266.000** |
| **Total** | | | **3.200.000** | **~4.256.000** |

¹ Usando 300 palavras/página (PDFs de logística são menos densos que prosa contínua — contêm tabelas, listas, cabeçalhos)  
² Usando 50 planilhas × 5 abas × 20 linhas × 10 colunas × 4 palavras por célula (valores numéricos e descritivos curtos)

**Total estimado: ~4,3 milhões de tokens**

> ⚠️ **[Revisão Crítica — seção 2]** Esta estimativa é conservadora em dois sentidos opostos: (1) assume que todos os 800 PDFs têm conteúdo textual — mas PDFs escaneados podem resultar em 0 tokens se o OCR falhar; (2) não considera o overhead de metadados adicionados pelo pipeline (fonte, data, versão, tipo) que acrescentam tokens a cada chunk. Na prática, o volume pode variar entre 3M e 6M tokens dependendo da qualidade do OCR e da verbosidade dos metadados.

---

### 1.3 Análise de Orçamento de Contexto

**Parâmetros:**
- Janela de contexto GPT-4o: 128.000 tokens
- System prompt + instruções: ~2.000 tokens
- **Disponível para contexto dinâmico: 126.000 tokens**
- Tamanho de cada chunk: 500 tokens
- **Máximo teórico de chunks por query: 252**

**O que significa na prática?**

252 chunks por query é enganosamente confortável. O problema não é o espaço físico — é o efeito de atenção distribuída: quanto mais chunks no contexto, mais o modelo dilui sua atenção e mais propício é ao "lost in the middle". A literatura empírica e os benchmarks de RAG mostram degradação relevante de qualidade acima de 10-15 chunks.

**Orçamento recomendado por query:**

| Componente | Tokens | % da janela |
|------------|--------|-------------|
| System prompt (estático) | ~2.000 | 1,6% |
| Metadados do atendente (tier, ID) | ~100 | 0,1% |
| Chunks recuperados (padrão: 5) | ~2.500 | 1,9% |
| Histórico de conversa (Teams) | ~1.000 | 0,8% |
| Pergunta do atendente | ~100 | 0,1% |
| **Total utilizado (típico)** | **~5.700** | **4,5%** |
| **Buffer de segurança** | ~122.300 | 95,5% |

Na prática, o orçamento é generoso para queries simples. O risco real é em perguntas multi-domínio (SLA + frete + devolução), onde o pipeline pode recuperar chunks de 3 tópicos diferentes — nesse caso, é preferível fazer queries separadas por domínio do que injetar 15 chunks de uma vez.

**Como a limitação afeta a estratégia de chunking e retrieval:**

1. **Não usar todo o espaço disponível:** o limite de contexto não é o teto de qualidade — é o limite físico. O teto de qualidade fica bem abaixo
2. **N fixo de chunks é ingênuo:** queries simples ("qual o SLA Gold?") precisam de 1-2 chunks. Queries complexas podem precisar de 7-10. Implementar N dinâmico baseado na complexidade da query
3. **Chunks menores × mais chunks ≠ melhor:** 10 chunks de 200 tokens pode ser pior do que 5 chunks de 500 tokens se os 5 forem mais relevantes

**Trade-offs ao variar o tamanho dos chunks:**

| Tamanho | Vantagens | Desvantagens |
|---------|-----------|--------------|
| Pequeno (150-250 tokens) | Retrieval mais preciso; chunk foca num único conceito | Perde contexto local; regras multi-etapa ficam fragmentadas |
| Médio (400-600 tokens) | Equilíbrio entre precisão e contexto; cobre seções completas | Pode misturar dois sub-tópicos diferentes |
| Grande (800-1200 tokens) | Preserva contexto de procedimentos longos; tabelas inteiras | Embedding representa múltiplos conceitos, dificultando retrieval semântico |

> ⚠️ **[Revisão Crítica — seção 2]** A estimativa de "2K tokens para system prompt" pode ser otimista. Um system prompt robusto com guardrails detalhados, exemplos de resposta correta/incorreta e instruções de tratamento de contradições facilmente chega a 3-5K tokens. Isso reduz o espaço efetivo disponível.

---

### 1.4 Recomendação de Estratégia de Chunking

**Estratégia: Chunking Híbrido com Tipagem por Conteúdo**

Não existe uma estratégia única que funcione para todos os tipos de documento da NovaTech. A recomendação é implementar três tipos de chunk com tratamento diferenciado:

---

**Tipo 1 — Chunks Semânticos por Seção** (padrão para prosa estruturada)

- **Tamanho alvo:** 400-500 tokens
- **Overlap:** 10% (~50 tokens) entre chunks adjacentes da mesma seção
- **Quando usar:** documentos com estrutura clara de seções (POL-001, PROC-042, SLA-2024)
- **Quebra por:** cabeçalhos h2/h3, nunca no meio de uma regra ou exceção

*Justificativa:* Os atendentes farão principalmente perguntas de busca pontual ("qual o prazo de devolução?", "qual o SLA Gold?") que mapeiam para seções específicas. Chunks por seção preservam a unidade semântica de cada regra. O overlap evita que a última frase de uma seção (que pode ser uma exceção crítica) fique inacessível.

---

**Tipo 2 — Chunks de Tabela** (indivisíveis)

- **Tamanho:** variável (50-2.000 tokens) — a tabela completa sempre fica junta
- **Quando usar:** qualquer tabela extraída de PDF, wiki ou planilha
- **Quebra por:** grupos de linhas se > 1.000 tokens, mas sempre com cabeçalhos repetidos
- **Metadado obrigatório:** `tipo=tabela`, `domínio`, `colunas_presentes`

*Justificativa:* Perguntas de consulta de valores ("qual o multiplicador para o Nordeste?", "qual o fator de peso para 2.000kg?") exigem a tabela completa. Um chunk que contém apenas parte da tabela garante resposta errada ou incompleta. O "lost in the middle" é menos relevante para tabelas, pois o modelo precisa do conteúdo completo, não de uma posição específica.

---

**Tipo 3 — Chunks de FAQ** (curtos, com metadado de confiabilidade)

- **Tamanho alvo:** 100-200 tokens por Q&A
- **Quando usar:** FAQ-Atendimento e qualquer documento informal
- **Metadado obrigatório:** `fonte=informal`, `validado_compliance=false`

*Justificativa:* Os Q&As do FAQ são semanticamente coesos — cada item responde uma dúvida específica. Manter cada Q&A como chunk próprio melhora o retrieval. O metadado de confiabilidade permite instruir o modelo a priorizar documentos formais quando houver conflito (ex: FAQ diz que carga perigosa pode ser enviada com frete expresso, mas não há PROC formal — o modelo deve sinalizar isso).

---

**Tratamento do efeito "Lost in the Middle"**

No momento da montagem do prompt, aplicar re-ranking com reposicionamento:

1. Recuperar 2× o número de chunks que serão usados (ex: buscar top-10, usar 5)
2. Re-rankar por relevância combinada (similaridade semântica + metadados de data/vigência)
3. Ao montar o bloco de contexto: posicionar os chunks de **maior relevância no início e no final**, chunks de relevância intermediária no meio
4. Isso mitiga o efeito "lost in the middle" sem exigir modelo diferente

```
[Chunk 1 — Alta relevância]      ← modelo presta mais atenção
[Chunk 2 — Média relevância]
[Chunk 3 — Média relevância]
[Chunk 4 — Média relevância]
[Chunk 5 — Alta relevância]      ← modelo presta mais atenção
```

**Tratamento de documentos contraditórios (PROC-042 vs PROC-042-v2):**

- Adicionar metadados `versao`, `data_vigencia_inicio`, `data_vigencia_fim` em cada chunk
- Ao recuperar chunks de documentos com mesma numeração mas versões diferentes: incluir **ambos** no contexto, com instrução explícita no system prompt para usar a versão mais recente e sinalizar a existência da versão antiga
- Não resolver a contradição no pipeline — sinalizar para o atendente que existe divergência e indicar ambas as fontes

---

## 2. Revisão Crítica da Análise

### Pontos Fracos Identificados

**Otimismo com o prazo de OCR**

A análise assume que o Azure Document Intelligence resolve o OCR de forma satisfatória. Na prática, documentos escaneados com baixa qualidade (resolução < 150 DPI, distorção, marcas d'água) podem ter taxa de erro > 20%, tornando os chunks inutilizáveis. O projeto precisa de uma fase de **auditoria da qualidade dos PDFs escaneados** antes de dimensionar o esforço de OCR — sem isso, o cronograma de 3 meses pode não ser suficiente.

**Estimativa de tokens subestimada para planilhas**

A estimativa de 50 planilhas × 5 abas × 20 linhas é conservadora. Planilhas comerciais de frete frequentemente têm centenas de linhas e dezenas de abas. Uma única planilha de tabela de fretes base (com combinações de origem × destino × tipo de carga) pode ter 5.000+ linhas. Isso pode elevar a estimativa de planilhas de ~266K para 1M+ tokens — aumentando o total da base para 5-6M tokens.

**Falta de estratégia para documentos obsoletos**

A análise não endereça o que fazer com os documentos contraditórios que já existem (PROC-042 v1 e v2 coexistindo sem marcação de obsolescência). O pipeline de ingestão precisa de uma política explícita: ou a NovaTech resolve a governança antes do go-live, ou o pipeline indexa ambos com lógica de priorização — mas sem governança, o assistente vai perpetuar a inconsistência existente.

**Ausência de tratamento para gaps documentais**

Os Anexos A e B revelam gaps críticos: nenhum documento formal sobre carga danificada em trânsito, sobre frete padrão (< 500kg), sobre seguro de carga. O assistente vai responder "não encontrei informação" para perguntas que os atendentes fazem diariamente (~20% dos chamados, baseado nos dados do FAQ). Isso pode minar a adoção se não for comunicado e endereçado como requisito de curadoria.

---

### Estimativas Otimistas Demais

| Estimativa | Por que pode não se sustentar |
|------------|-------------------------------|
| 300 palavras/página PDF | PDFs com tabelas densas e fluxogramas têm menos palavras por página; PDFs de relatório narrativo têm mais. A variância é alta. |
| 5 abas × 20 linhas por planilha | Planilhas de frete costumam ser muito maiores. Sem acesso às planilhas reais, a estimativa é puro chute. |
| 3 meses para discovery + dev + go-live | A resolução da contradição PROC-042 v1/v2 e dos gaps documentais requer governança prévia da NovaTech — atividade fora do controle do time de desenvolvimento e frequentemente subestimada em projetos de RAG. |
| OCR via Azure resolve os PDFs escaneados | Sem auditoria de qualidade prévia, pode-se descobrir no meio do projeto que 30% dos PDFs escaneados têm qualidade insuficiente para OCR automatizado. |

---

### Riscos Não Considerados na Análise Original

**Risco 1: Contradições que o pipeline não detecta automaticamente**

A PROC-042 v1 e v2 têm o mesmo número de documento mas multiplicadores diferentes. O pipeline de ingestão ingênuo indexa os dois como documentos distintos e igualmente válidos. Sem lógica explícita de detecção de contradições (comparar documentos com mesma numeração, verificar datas de vigência), o retrieval pode retornar chunks de ambas as versões na mesma query — gerando respostas matematicamente inconsistentes que o atendente não vai detectar.

**Risco 2: Degradação silenciosa com atualizações incrementais**

A documentação é atualizada mensalmente por 3 áreas independentes. Se o pipeline de reingestão for incremental (só reingere documentos novos ou modificados), documentos que *deveriam* ter sido arquivados mas não foram continuarão sendo recuperados. Sem um processo de governança de arquivamento, a base cresce sempre e nunca encolhe — aumentando o risco de contradições ao longo do tempo.

**Risco 3: Alucinação de alta confiança em gaps documentais**

O assistente bem calibrado deve dizer "não encontrei informação" quando não há chunk relevante. Mas LLMs tendem a alucidar com confiança alta em domínios onde têm conhecimento geral — e logística é um domínio bem representado no treinamento do GPT-4o. Para perguntas sobre frete padrão (< 500kg), seguro de carga ou carga danificada — tópicos sem cobertura documental — o modelo pode gerar respostas plausíveis mas incorretas para a NovaTech especificamente. O guardrail de "nunca inventar" precisa ser testado especificamente nesses cenários.

**Risco 4: Context rot em sessões longas no Teams**

O assistente será integrado ao Teams, onde uma sessão pode ter 10-20 perguntas sequenciais de um atendente. Se o histórico de conversa for incluído no contexto (que é esperado para que o assistente mantenha coerência), o histórico cresce continuamente. Com 20 perguntas de ~100 tokens cada e respostas de ~300 tokens, o histórico acumula ~8.000 tokens — mais do que todos os chunks recuperados. Isso comprime o espaço para chunks e degrada a qualidade das respostas tardias na sessão.

**Mitigação recomendada:** implementar janela deslizante de histórico (manter apenas as últimas 3-5 trocas) ou sumarização automática do histórico quando exceder orçamento definido.

---

### Ajustes Incorporados

Os seguintes ajustes foram incorporados diretamente nas seções anteriores com marcação `⚠️ [Revisão Crítica]`:

- Custo e limitações do Azure Document Intelligence para tabelas (1.1 — PDFs com tabelas)
- Priorização da estratégia de Vision para fluxogramas (1.1 — PDFs escaneados)
- Limite de profundidade para resolução de links no Confluence (1.1 — Wiki)
- Risco de planilhas com volume maior que o estimado (1.1 — XLSX)
- Variância da estimativa de tokens (1.2)
- Potencial subestimativa do system prompt (1.3)
