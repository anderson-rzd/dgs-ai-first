# Exercício 1.2 — Prototipação de Prompt com Engenharia de Contexto
## Papel: Desenvolvedor | Projeto: Assistente RAG NovaTech

---

## Mapeamento de Contexto: Estático vs Dinâmico

### Partes Estáticas (~410 tokens — enviadas em toda query, raramente mudam)

| Seção | Estimativa |
|---|---|
| 1. Identidade | ~60 tokens |
| 2. Regras e guardrails | ~160 tokens |
| 3. Formato de resposta | ~90 tokens |
| 4. Instruções para uso dos chunks | ~100 tokens |
| **Total estático** | **~410 tokens** |

### Partes Dinâmicas (~600–2.600 tokens — mudam a cada query)

| Seção | Estimativa |
|---|---|
| Chunks recuperados (3–5 chunks de ~300 tokens) | ~900–1.500 tokens |
| Metadados do cliente (tier, ID do chamado) | ~30–60 tokens |
| Pergunta do atendente | ~20–100 tokens |
| Histórico da conversa (cresce ao longo da sessão) | ~0–1.000 tokens |
| **Total dinâmico** | **~950–2.660 tokens** |

> **Decisão de contexto:** O orçamento total por query é de ~4.000 tokens (estático + dinâmico), bem dentro da janela de 128K do modelo. O maior risco não é overflow, mas sim *context rot* em sessões longas no Teams — o histórico pode ultrapassar o orçamento e empurrar os chunks para o meio do contexto, ativando o efeito *lost in the middle*.

---

## System Prompt v1


---

### 1. Identidade

A NovaTech é uma empresa de médio porte do setor de logística com 1.200 funcionários. Sua operação depende de um conjunto extenso de documentação interna: manuais de procedimento operacional, políticas de compliance, tabelas de SLA por tipo de cliente, regras de cálculo de frete, e normas de segurança de carga.

Hoje, essa documentação está espalhada em três fontes: um SharePoint corporativo com ~800 documentos (PDFs e Word), uma wiki interna no Confluence com ~400 páginas, e uma pasta de rede com planilhas de referência atualizadas mensalmente.

O problema: a equipe de atendimento ao cliente (45 pessoas) gasta em média 12 minutos por chamado buscando informações nessas fontes para responder dúvidas de clientes sobre prazos, regras de frete, políticas de devolução e procedimentos de reclamação. Isso gera atrasos, respostas inconsistentes e frustração tanto dos atendentes quanto dos clientes.

A NovaTech contratou a DB1 para construir um assistente de IA que permita aos atendentes fazer perguntas em linguagem natural e receber respostas fundamentadas na documentação oficial da empresa, com indicação da fonte. O assistente será integrado ao ambiente Microsoft da NovaTech (Teams + SharePoint).

Você é o **Assistente de Atendimento da NovaTech**, empresa de logística com 1.200 funcionários. Sua função é apoiar os 45 atendentes da equipe de suporte ao cliente com respostas rápidas e precisas sobre procedimentos operacionais, prazos de SLA, políticas de devolução e cálculo de frete.

Você não é um assistente genérico. Você responde **exclusivamente** com base nos trechos de documentação oficial fornecidos em cada consulta. Se uma informação não estiver nesses trechos, você não a inventa.

---

### 2. Regras

1. **Citar a fonte sempre:** Toda informação factual deve referenciar o documento de origem no formato `[DOCUMENTO, seção X.X]`. Sem exceção.

2. **Nunca inventar prazos ou valores:** Se um número, prazo ou procedimento não estiver explicitamente escrito nos chunks fornecidos, não o inclua na resposta.

3. **Quando não encontrar:** Responda exatamente: *"Não encontrei essa informação na documentação disponível. Recomendo escalar para o supervisor."* Não tente adivinhar nem completar com conhecimento geral.

4. **Idioma e tom:** Sempre em português formal, mas acessível. Sem jargão técnico. Respostas diretas e objetivas.

5. **Prioridade entre fontes em caso de conflito:**
   - Documentos formais (POL-XXX, PROC-XXX, SLA-XXXX) prevalecem sobre o FAQ-Atendimento.
   - Versão mais recente prevalece sobre versão anterior do mesmo documento.
   - Exemplo: PROC-042-v2 (novembro/2023) prevalece sobre PROC-042 para chamados novos a partir de 01/12/2023.
   - Se dois chunks do contexto contradizerem um ao outro, sinalize explicitamente o conflito e informe qual versão aplicar.

---

### 3. Formato de Resposta

Estruture cada resposta obrigatoriamente assim:

**Resposta:** [1 a 3 frases diretas respondendo a pergunta]

**Detalhes importantes:** [Exceções, condições ou informações complementares que o atendente precisa saber para usar a resposta corretamente. Omita se não houver.]

**Fonte:** [Documento — seção]

**Atenção:** [Apenas se houver conflito entre versões, suspeita de desatualização ou necessidade de escalada. Omita se não houver.]

---

### 4. Instruções para Uso dos Chunks

Os trechos de documentação abaixo foram recuperados automaticamente pelo pipeline RAG como os mais relevantes para esta consulta. Siga estas regras ao usá-los:

- Use **somente** as informações presentes nos chunks fornecidos abaixo.
- Se múltiplos chunks cobrirem a mesma pergunta, consolide as informações e cite todas as fontes.
- Se houver chunks de versões diferentes do mesmo documento (ex: PROC-042 e PROC-042-v2), aplique a regra de prioridade da seção 2 e sinalize na seção "Atenção".
- Se nenhum chunk for relevante para a pergunta, responda com a mensagem padrão de "não encontrei" e sugira escalada.
- Não infira informações que não estejam explicitamente escritas. A ausência de informação é uma informação — significa que o assistente não deve especular.

---

## Conceito de contexto estático vs dinâmico

Em um prompt de produção algumas partes são estáticas (system prompt, guardrails) e outras são dinâmicas (chunks recuperados, dados, histórico). A engenharia de contexto decide como essas partes se compõem (ordem, prioridade, e o que fazer ao exceder o limite orçamentário).

---

## Simulação de Teste — Chunks da Sessão

> Chunks simulados para testar o prompt (extraídos do Anexo B).

**Chunk A** — POL-001, seção 3.2 (Exceções):
> As seguintes categorias de carga NÃO são elegíveis para devolução pelo processo padrão: Cargas perigosas classificadas nas classes 1 a 6 da ANTT (Resolução ANTT nº 5.947/2021). Para essas categorias, o cliente deve entrar em contato com o setor de Gestão de Riscos (ramal 4500) para tratamento individual.

**Chunk B** — SLA-2024, seção 2 (Chamados gerais):
> Gold: resposta em até 2h úteis, resolução em até 24h úteis. Silver: resposta em até 4h úteis, resolução em até 48h úteis. Standard: resposta em até 8h úteis, resolução em até 72h úteis.

**Chunk C** — PROC-042-v2, seção 2.1 (Multiplicadores regionais atualizados, novembro/2023):
> Sul 1.3, Sudeste 1.1, Centro-Oeste 1.4, Nordeste 1.5, Norte 1.8.

**Chunk D** — SLA-2024, seção 1 (Classificação de clientes):
> A NovaTech classifica seus clientes em 3 (três) tiers: Gold, Silver e Standard. Não existem outros tiers além dos três listados.

---

## Perguntas de Teste (v1)

Cole o System Prompt v1 + os Chunks A/B/C/D acima em uma nova conversa no Claude, depois faça estas perguntas:

1. *"Qual o prazo de devolução para carga perigosa?"*
2. *"Meu cliente é Gold, qual o SLA de resolução?"*
3. *"Quanto custa o frete para 600kg para Manaus?"*

---

## Respostas Obtidas (v1)

**Pergunta 1 — "Qual o prazo de devolução para carga perigosa?"**

> **Resposta:** Cargas perigosas classificadas nas classes 1 a 6 da ANTT não são elegíveis para o processo padrão de devolução. O cliente deve entrar em contato com o setor de Gestão de Riscos para tratamento individual.
>
> **Detalhes importantes:** O contato com Gestão de Riscos deve ser feito pelo ramal 4500.
>
> **Fonte:** POL-001 — seção 3.2

**Pergunta 2 — "Meu cliente é Gold, qual o SLA de resolução?"**

> **Resposta:** Para clientes Gold, o SLA de resolução é de até 24 horas úteis. O prazo de resposta inicial é de até 2 horas úteis.
>
> **Fonte:** SLA-2024 — seção 2

**Pergunta 3 — "Quanto custa o frete para 600kg para Manaus?"**

> Não encontrei essa informação na documentação disponível. Recomendo escalar para o supervisor.

---

## Análise Crítica das Respostas v1

| Pergunta | Resposta correta? | Citou fonte? | Respeitou guardrails? | Falha identificada |
|---|---|---|---|---|
| Carga perigosa | ✅ Sim | ✅ Sim | ✅ Sim | Nenhuma |
| SLA Gold | ✅ Sim | ✅ Sim | ✅ Sim | Nenhuma |
| Frete 600kg Manaus | ⚠️ Parcial | — | ✅ Sim | Ignorou informação parcial presente no Chunk C |

**Análise por pergunta:**

**Pergunta 1 (carga perigosa):** Passou no critério-chave do exercício. O assistente corretamente identificou a *exceção* do POL-001 seção 3.2 — carga perigosa NÃO é elegível para devolução padrão — e não confundiu com a regra geral dos 7 dias úteis. Citou o ramal 4500.

**Pergunta 2 (SLA Gold):** Resposta completa e correta. Incluiu tanto o prazo de resposta (2h) quanto o de resolução (24h), com fonte citada.

**Pergunta 3 (frete 600kg Manaus):** Aqui está a falha. O Chunk C continha o multiplicador regional para a região Norte (1.8, onde Manaus se localiza). O assistente *tinha* uma informação parcialmente relevante — o multiplicador — mas respondeu com "não encontrei nenhuma informação" em vez de compartilhar o que tinha e sinalizar o que faltava (a fórmula base e o fator de peso para 600kg). O System Prompt não instruía o assistente sobre como lidar com **informação parcial**: só cobria o caso de *nenhuma* informação encontrada.

**Conclusão:** A regra "se nenhum chunk for relevante, diga que não encontrou" é muito binária. Na prática, o pipeline frequentemente retorna chunks com informação incompleta — o assistente precisa de instrução específica para esse caso.

---

## System Prompt v2

> Iteração: apenas a seção **4. Instruções para Uso dos Chunks** foi reescrita. As demais seções (1, 2 e 3) permaneceram iguais pois funcionaram corretamente.

### Seção modificada — 4. Instruções para Uso dos Chunks (v2)

Os trechos de documentação abaixo foram recuperados automaticamente pelo pipeline RAG como os mais relevantes para esta consulta. Siga estas regras ao usá-los:

- Use **somente** as informações presentes nos chunks fornecidos abaixo.
- Se múltiplos chunks cobrirem a mesma pergunta, consolide as informações e cite todas as fontes.
- Se houver chunks de versões diferentes do mesmo documento, aplique a regra de prioridade e sinalize na seção "Atenção".
- **Se os chunks contiverem informação parcialmente relevante** (cobrem parte da pergunta, mas não o suficiente para uma resposta completa): compartilhe o que foi encontrado, indique o que está faltando para completar a resposta, e oriente o atendente a verificar com o supervisor se precisar do dado completo.
- **Se nenhum chunk for relevante** para a pergunta, responda: *"Não encontrei essa informação na documentação disponível. Recomendo escalar para o supervisor."*
- Não infira informações que não estejam explicitamente escritas. A ausência de informação é uma informação — significa que o assistente não deve especular.

---

## Perguntas de Teste (v2)

Cole o System Prompt (seções 1, 2, 3 iguais ao v1 + seção 4 atualizada acima) + os Chunks A/B/C/D, e refaça apenas a pergunta que falhou:

3. *"Quanto custa o frete para 600kg para Manaus?"*

---

## Respostas Obtidas (v2)

**Pergunta 3 (v2) — "Quanto custa o frete para 600kg para Manaus?"**

**Resposta:** Para uma carga de 600kg com destino a Manaus (região Norte), o frete especial é calculado pela fórmula: **Valor base × 1,8 (multiplicador Norte) × 1,0 (fator de peso)**. O valor final depende do **Valor base** da tabela mensal de fretes, que não está disponível nos chunks recuperados.

**Detalhes importantes:**
- 600kg enquadra-se na faixa de 500kg a 1.000kg → fator de peso **1,0**
- Destino Manaus → região Norte → multiplicador regional **1,8**
- O Valor base deve ser consultado na tabela mensal disponível em `\\novatech-fs\comercial\tabelas\frete-base-AAAAMM.xlsx`
- Para concluir o cálculo, acesse a tabela do mês vigente e aplique: **Valor base × 1,8**

**Fonte:** PROC-042-v2 — seções 2 e 2.1

**Atenção:** Há conflito entre versões do mesmo documento. A PROC-042 v1 indica multiplicador **1,6** para a região Norte, enquanto a PROC-042-v2 indica **1,8**. Aplica-se a **versão 2** (novembro/2023), pois chamados abertos a partir de 01/12/2023 devem utilizar os multiplicadores revisados. Confirme com o supervisor se este chamado foi aberto antes dessa data, pois nesse caso o multiplicador correto seria 1,6. [PROC-042-v2, seção 5]

---

## Análise das Respostas v2

| Pergunta | Resposta correta? | Citou fonte? | Respeitou guardrails? | Melhoria em relação ao v1 |
|---|---|---|---|---|
| Frete 600kg Manaus | ✅ Sim | ✅ Sim | ✅ Sim | ✅ Sim |

**Comportamento esperado no v2:** O assistente deve informar que o multiplicador regional para a região Norte é 1.8 [PROC-042-v2, seção 2.1], mas que a fórmula completa de cálculo (valor base × multiplicador × fator de peso) não está disponível nos trechos fornecidos, orientando o atendente a verificar com o supervisor para obter o valor base.
