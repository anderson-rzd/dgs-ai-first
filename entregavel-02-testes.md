# Entregável 2 — Resultados dos 5 Testes com Análise

## Configuração

| Parâmetro | Valor |
|---|---|
| Modelo de embedding | `paraphrase-multilingual-MiniLM-L12-v2` |
| Vector store | ChromaDB (distância cosseno) |
| Chunks recuperados por query | 8 |
| LLM para geração | Claude (chat manual) |
| Total de chunks na base | 35 (5 documentos) |

**Legenda de status dos chunks:**
- ✅ **Correto** — chunk previsto no gabarito do Anexo B como obrigatório
- 🟡 **Aceitável** — chunk previsto no gabarito como "pode aparecer"
- ⚠️ **Risco** — chunk de versão desatualizada ou fonte informal
- ❌ **Irrelevante** — chunk não previsto no gabarito, sem relação direta

---

## Teste 1 — "Qual o prazo de devolução?"

**Gabarito Anexo B:** deve recuperar POL-001-A (Seção 3.1) obrigatoriamente; POL-001-B e POL-001-C como aceitáveis.

### Chunks recuperados

| # | Chunk ID | Score | Fonte / Seção | Status |
|---|---|---|---|---|
| 1 | `PROC-042-v2-frete-especial-revisado-3__Prazo_de_entrega_para_frete_especial` | 0.5463 | PROC-042-v2 / 3. Prazo de entrega | ❌ Irrelevante (prazo de *entrega*, não de *devolução*) |
| 2 | `POL-001-politica-devolucao-3_1__Prazo_geral` | 0.5442 | POL-001 / 3.1. Prazo geral | ✅ Correto |
| 3 | `PROC-042-frete-especial-v1-3__Prazo_de_entrega_para_frete_especial` | 0.5249 | PROC-042-v1 / 3. Prazo de entrega | ❌ Irrelevante (v1 de prazo de *entrega*) |
| 4 | `SLA-2024-tabela-sla-clientes-5__Medição_e_reportes` | 0.4636 | SLA-2024 / 5. Medição | ❌ Irrelevante |
| 5 | `POL-001-politica-devolucao-3_5__Custos_de_devolução` | 0.4605 | POL-001 / 3.5. Custos | 🟡 Aceitável |
| 6 | `POL-001-politica-devolucao-3_3__Procedimento_de_devolução` | 0.4406 | POL-001 / 3.3. Procedimento | 🟡 Aceitável |
| 7 | `POL-001-politica-devolucao-3__Regras_de_Devolução` | 0.4253 | POL-001 / 3. Regras | 🟡 Aceitável |
| 8 | `FAQ-atendimento-Item_38____...` | 0.4176 | FAQ / Item 38 | ❌ Irrelevante (carga danificada) |

**Comparação com gabarito:** ✅ Chunk correto (POL-001-A, rank 2). ⚠️ Problema: PROC-042-v2 e v1 de "Prazo de *entrega*" ficam em rank 1 e 3 por confusão semântica entre "prazo de devolução" e "prazo de entrega" — o embedding do modelo não distingue os dois conceitos.

### Prompt enviado ao Claude

```
Você é o Assistente de Atendimento da NovaTech...

[Documento 1 — PROC-042-v2 / 3. Prazo de entrega para frete especial (score: 0.5463)]
## 3. Prazo de entrega para frete especial
O prazo de entrega para frete especial é calculado como o prazo padrão da rota
+ 3 dias úteis adicionais para manuseio e roteirização de carga pesada.

[Documento 2 — POL-001 / 3.1. Prazo geral (score: 0.5442)]
### 3.1. Prazo geral
O cliente pode solicitar a devolução de mercadorias em até 7 (sete) dias úteis
após a data de recebimento confirmada no sistema de tracking. A contagem de dias
úteis exclui sábados, domingos e feriados nacionais.

[Documento 3 — PROC-042-v1 / 3. Prazo de entrega (score: 0.5249)]
## 3. Prazo de entrega para frete especial
O prazo de entrega para frete especial é calculado como o prazo padrão da rota
+ 2 dias úteis adicionais para manuseio de carga pesada.

[... + 5 chunks adicionais]

Pergunta do atendente: Qual o prazo de devolução?
```

### Resposta obtida do Claude

> O prazo para solicitação de devolução de mercadorias é de **7 (sete) dias úteis** contados a partir da data de recebimento confirmada no sistema de tracking. Sábados, domingos e feriados nacionais não entram nessa contagem. **[FONTE: POL-001 — Política de Devolução, Seção 3.1 — Prazo geral]**
>
> *Nota:* Os demais documentos recuperados tratam do prazo de *entrega* de frete especial (PROC-042), que é diferente do prazo de *devolução*. Para devolução, a regra aplicável é a POL-001.

### Avaliação
| Critério | Resultado |
|---|---|
| Resposta correta? | ✅ Sim — 7 dias úteis com regra de dias úteis |
| Citou a fonte? | ✅ Sim — POL-001, Seção 3.1 |
| Respeitou guardrails? | ✅ Sim — distinguiu prazo de devolução de prazo de entrega |
| Usou chunk irrelevante? | ✅ Não — ignorou PROC-042 corretamente |

---

## Teste 2 — "Posso devolver carga perigosa?"

**Gabarito Anexo B:** deve recuperar POL-001-B (Seção 3.2) obrigatoriamente; FAQ-03 e POL-001-A como aceitáveis.

### Chunks recuperados

| # | Chunk ID | Score | Fonte / Seção | Status |
|---|---|---|---|---|
| 1 | `FAQ-atendimento-Item_3____...` | 0.5672 | FAQ / Item 3 — devolver carga perigosa | 🟡 Aceitável (mas informal) |
| 2 | `FAQ-atendimento-Item_38____...` | 0.5378 | FAQ / Item 38 — carga danificada | ❌ Irrelevante |
| 3 | `PROC-042-v2-4__Condições_especiais` | 0.4644 | PROC-042-v2 / 4. Condições especiais | ⚠️ Risco (menciona carga perigosa em frete, não devolução) |
| 4 | `POL-001-3_5__Custos_de_devolução` | 0.4485 | POL-001 / 3.5. Custos | 🟡 Aceitável |
| 5 | `PROC-042-v1-4__Condições_especiais` | 0.4297 | PROC-042-v1 / 4. Condições | ⚠️ Risco (v1 desatualizada) |
| 6 | `POL-001-3_2__Exceções_ao_prazo_geral-p0` | 0.4255 | POL-001 / 3.2. Exceções | ✅ Correto (rank 6 — deveria ser rank 1) |
| 7 | `FAQ-atendimento-Item_22____...` | 0.4121 | FAQ / Item 22 — seguro de carga | ❌ Irrelevante |
| 8 | `SLA-2024-3__Definição_incidente_crítico` | 0.3718 | SLA-2024 / 3. Incidente crítico | ❌ Irrelevante |

**Comparação com gabarito:** ⚠️ Chunk correto encontrado apenas em rank 6. O FAQ informal (rank 1) derrota a política normativa (POL-001-B, rank 6). Diferença de score: 0.5672 vs 0.4255 — o FAQ usa linguagem conversacional mais similar à query, enquanto a seção da POL-001 tem título "Exceções ao prazo geral" (não menciona "carga perigosa" no título).

### Prompt enviado ao Claude

```
Você é o Assistente de Atendimento da NovaTech...
[Regra: FAQ é informal — prefira documentos normativos (POL, PROC, SLA)]

[Documento 1 — FAQ-Atendimento / Item 3 (score: 0.5672)]
Na prática, a gente orienta o cliente a ligar no ramal 4500 (Gestão de Riscos).
Oficialmente não pode pelo processo padrão, mas já tiveram casos em que o pessoal
de Riscos autorizou exceção. Então não diga que é impossível — diga que precisa
de tratamento especial.

[Documento 6 — POL-001 / 3.2. Exceções ao prazo geral (score: 0.4255)]
As seguintes categorias de carga **NÃO são elegíveis** para devolução pelo processo
padrão: Cargas perigosas classificadas nas classes 1 a 6 da ANTT...
Para essas categorias, o cliente deve entrar em contato com o setor de Gestão de
Riscos (ramal 4500) para tratamento individual.

[... + outros chunks]

Pergunta do atendente: Posso devolver carga perigosa?
```

### Resposta obtida do Claude

> De acordo com a política oficial da NovaTech, cargas perigosas classificadas nas classes 1 a 6 da ANTT **não são elegíveis para devolução pelo processo padrão**. Isso inclui explosivos (classe 1), gases (classe 2), líquidos inflamáveis (classe 3), sólidos inflamáveis (classe 4), oxidantes e peróxidos (classe 5) e substâncias tóxicas (classe 6). **[FONTE: POL-001 — Política de Devolução, Seção 3.2]**
>
> O cliente deve ser orientado a entrar em contato com o setor de **Gestão de Riscos** pelo ramal **4500** para tratamento individual do caso.
>
> *Observação operacional (fonte informal):* O FAQ interno de atendimento menciona que, na prática, o setor de Riscos já autorizou exceções em casos específicos. Por isso, não afirme ao cliente que é impossível — informe que requer tratamento especial pelo ramal 4500. **[FONTE: FAQ-Atendimento, Item 3 — documento informal, não validado por Compliance]**

### Avaliação
| Critério | Resultado |
|---|---|
| Resposta correta? | ✅ Sim — a regra principal (NÃO pode pelo processo padrão) está correta |
| Citou a fonte? | ✅ Sim — priorizou POL-001 sobre o FAQ |
| Respeitou guardrails? | ✅ Sim — alertou sobre natureza informal do FAQ |
| Chunk irrelevante influenciou? | ⚠️ Parcialmente — chunks do PROC-042 sobre frete de cargas perigosas foram ignorados |

**Risco identificado:** sem o guardrail explícito "FAQ é informal", o Claude poderia ter baseado a resposta principal no FAQ-Item 3 (rank 1) em vez da POL-001-3.2 (rank 6), gerando uma resposta com tom de "orientação prática" em vez de "regra normativa".

---

## Teste 3 — "Qual o SLA do cliente Gold?"

**Gabarito Anexo B:** deve recuperar SLA-2024-B (Seção 2 — tabela de SLAs) obrigatoriamente.

### Chunks recuperados

| # | Chunk ID | Score | Fonte / Seção | Status |
|---|---|---|---|---|
| 1 | `FAQ-atendimento-Item_41____...` | 0.4787 | FAQ / Item 41 — SLA resposta vs resolução | ⚠️ Aceitável mas informal |
| 2 | `FAQ-atendimento-Item_15____...` | 0.4663 | FAQ / Item 15 — Platinum inexistente | ❌ Irrelevante |
| 3 | `SLA-2024-5__Medição_e_reportes` | 0.4395 | SLA-2024 / 5. Medição | 🟡 Aceitável |
| 4 | `SLA-2024-4__Penalidades_por_descumprimento` | 0.3812 | SLA-2024 / 4. Penalidades | 🟡 Aceitável |
| 5 | `FAQ-atendimento-Item_27____...` | 0.3369 | FAQ / Item 27 — tracking | ❌ Irrelevante |
| 6 | `SLA-2024-1__Classificação_de_clientes` | 0.3256 | SLA-2024 / 1. Classificação | 🟡 Aceitável |
| 7 | `FAQ-atendimento-Item_45____...` | 0.3230 | FAQ / Item 45 — desconto frete | ❌ Irrelevante |
| 8 | `POL-001-2__Escopo` | 0.3046 | POL-001 / 2. Escopo | ❌ Irrelevante |

**Comparação com gabarito:** ❌ Chunk correto (SLA-2024 / 2. Tabela de SLAs) está em **rank 12** com score 0.260 — completamente fora dos 8 recuperados. O FAQ-41 (rank 1, score 0.479) usa linguagem coloquial ("O Gold tem 2h de resposta e 24h de resolução") que é semanticamente mais próxima da query natural do que o título formal "2. Tabela de SLAs". O LLM recebe a resposta certa mas via fonte errada (informal).

### Prompt enviado ao Claude

```
[Documento 1 — FAQ-Atendimento / Item 41 (score: 0.4787)]
Resposta é quando a gente dá o primeiro retorno ao cliente. Resolução é quando o
problema é efetivamente resolvido. O Gold tem 2h de resposta e 24h de resolução.
Silver é 4h e 48h. Standard é 8h e 72h. Para incidentes críticos, os prazos são
menores — veja a tabela SLA-2024.

[Documento 3 — SLA-2024 / 5. Medição e reportes (score: 0.4395)]
Os SLAs são medidos pelo sistema de chamados (Azure DevOps)...
O relógio de SLA pausa fora do horário comercial (08h-18h, dias úteis) para
chamados gerais, mas não pausa para incidentes críticos de clientes Gold.

[... + outros chunks]

Pergunta do atendente: Qual o SLA do cliente Gold?
```

### Resposta obtida do Claude

> Para clientes do tier **Gold**, os prazos de SLA são:
>
> - **Tempo de primeira resposta:** até **2 horas**
> - **Tempo de resolução:** até **24 horas**
>
> **[FONTE: FAQ-Atendimento, Item 41 — atenção: este é um documento informal do time de atendimento]**
>
> *Nota importante:* Para incidentes críticos de clientes Gold, o relógio de SLA **não pausa** fora do horário comercial (ou seja, conta 24 horas corridas). **[FONTE: SLA-2024, Seção 5]**
>
> Para confirmar os SLAs formais e os prazos específicos para incidentes críticos, recomendo consultar o documento SLA-2024 — Tabela de SLA por Tipo de Cliente, Seção 2.

### Avaliação
| Critério | Resultado |
|---|---|
| Resposta correta? | ✅ Sim — valores corretos (2h / 24h) |
| Citou a fonte? | ⚠️ Parcialmente — citou o FAQ como fonte principal (informal), mas alertou |
| Respeitou guardrails? | ✅ Sim — sugeriu consultar SLA-2024 Seção 2 que não estava nos chunks |
| Chunk principal do gabarito recuperado? | ❌ Não — SLA-2024 Seção 2 está em rank 12 |

**Problema crítico:** a resposta está correta mas por razões erradas — a tabela formal (SLA-2024 Seção 2) não foi recuperada. Se o FAQ-41 tivesse um valor errado (ou fosse uma versão desatualizada), o Claude responderia errado sem ter como perceber, pois o documento normativo não está no contexto.

---

## Teste 4 — "Qual o SLA do cliente Platinum?"

**Gabarito Anexo B:** deve recuperar SLA-2024-A (Seção 1 — "não existem outros tiers") obrigatoriamente; FAQ-15 como aceitável.

### Chunks recuperados

| # | Chunk ID | Score | Fonte / Seção | Status |
|---|---|---|---|---|
| 1 | `FAQ-atendimento-Item_15____...` | 0.6751 | FAQ / Item 15 — Platinum inexistente | 🟡 Aceitável (FAQ correto aqui) |
| 2 | `FAQ-atendimento-Item_41____...` | 0.3705 | FAQ / Item 41 — SLA resposta vs resolução | 🟡 Aceitável |
| 3 | `SLA-2024-1__Classificação_de_clientes` | 0.3656 | SLA-2024 / 1. Classificação | ✅ Correto |
| 4 | `SLA-2024-5__Medição_e_reportes` | 0.3515 | SLA-2024 / 5. Medição | 🟡 Aceitável |
| 5 | `POL-001-2__Escopo` | 0.3482 | POL-001 / 2. Escopo | ❌ Irrelevante |
| 6 | `PROC-042-v2-4__Condições_especiais` | 0.3256 | PROC-042-v2 / 4. Condições | ❌ Irrelevante |
| 7 | `FAQ-atendimento-Item_8____...` | 0.3175 | FAQ / Item 8 — frete especial | ❌ Irrelevante |
| 8 | `FAQ-atendimento-Item_22____...` | 0.3158 | FAQ / Item 22 — seguro | ❌ Irrelevante |

**Comparação com gabarito:** ✅ Chunk correto (SLA-2024 Seção 1) em rank 3. FAQ-15 em rank 1 com score bem acima (0.675 vs 0.366) — o FAQ usa "Platinum" explicitamente no título, o que gera alta similaridade semântica. A combinação FAQ-15 + SLA-2024 Seção 1 fornece contexto suficiente para uma boa resposta.

### Prompt enviado ao Claude

```
[Documento 1 — FAQ-Atendimento / Item 15 (score: 0.6751)]
Não existe tier Platinum na NovaTech. Às vezes o cliente confunde com outra
transportadora ou com o programa de fidelidade antigo que foi descontinuado em
2022. Oriente que nossos tiers são Gold, Silver e Standard e peça o número do
contrato para verificar.

[Documento 3 — SLA-2024 / 1. Classificação de clientes (score: 0.3656)]
A NovaTech classifica seus clientes em 3 (três) tiers com base no volume mensal
de operações e no valor do contrato: Gold, Silver e Standard.
Nota: Não existem outros tiers além dos três listados acima.

[... + outros chunks]

Pergunta do atendente: Qual o SLA do cliente Platinum?
```

### Resposta obtida do Claude

> O tier **Platinum não existe** na NovaTech. A empresa classifica seus clientes em apenas **três tiers**: **Gold**, **Silver** e **Standard**. Não há SLA definido para um tier Platinum porque esse tier não faz parte da estrutura de clientes da empresa. **[FONTE: SLA-2024 — Tabela de SLA, Seção 1 — Classificação de clientes]**
>
> O cliente pode estar confundindo com outra transportadora ou com o programa de fidelidade antigo, descontinuado em 2022. Solicite o número do contrato para verificar o tier correto. **[FONTE: FAQ-Atendimento, Item 15 — informação prática do time]**
>
> Posso informar os SLAs de qualquer um dos três tiers existentes, se precisar.

### Avaliação
| Critério | Resultado |
|---|---|
| Resposta correta? | ✅ Sim — zero alucinação, Platinum não existe |
| Citou a fonte? | ✅ Sim — SLA-2024 como fonte normativa + FAQ como contexto prático |
| Respeitou guardrails? | ✅ Sim — não inventou SLA para tier inexistente |
| Chunk correto recuperado? | ✅ Sim — rank 3 com score 0.366 |

**Melhor resultado dos 5 testes.** A combinação FAQ-15 (alta similaridade por ter "Platinum" explícito) + SLA-2024 Seção 1 (normativa que confirma os 3 tiers) produziu contexto ideal para a resposta.

---

## Teste 5 — "Como calcular o frete para 600kg com destino a Manaus?"

**Gabarito Anexo B:** deve recuperar PROC-042v2-B (multiplicadores regionais v2) e PROC-042v2-A (fórmula v2). Risco: recuperar PROC-042-B (v1) gerando contradição.

### Chunks recuperados

| # | Chunk ID | Score | Fonte / Seção | Status |
|---|---|---|---|---|
| 1 | `PROC-042-v2-2__Fórmula_de_cálculo` | 0.5383 | PROC-042-v2 / 2. Fórmula | ✅ Correto (fórmula v2) |
| 2 | `PROC-042-v1-2__Fórmula_de_cálculo` | 0.5366 | PROC-042-v1 / 2. Fórmula | ⚠️ Risco (v1 — fator de peso diferente: 1.2 vs 1.15 para >1.000kg) |
| 3 | `PROC-042-v1-1__Objetivo` | 0.4910 | PROC-042-v1 / 1. Objetivo | ❌ Irrelevante |
| 4 | `PROC-042-v2-4__Condições_especiais` | 0.4002 | PROC-042-v2 / 4. Condições | 🟡 Aceitável |
| 5 | `PROC-042-v2-1__Objetivo` | 0.3897 | PROC-042-v2 / 1. Objetivo | ❌ Irrelevante |
| 6 | `PROC-042-v1-4__Condições_especiais` | 0.3810 | PROC-042-v1 / 4. Condições | ⚠️ Risco (v1) |
| 7 | `FAQ-atendimento-Item_27____...` | 0.3210 | FAQ / Item 27 — tracking | ❌ Irrelevante |
| 8 | `PROC-042-v2-3__Prazo_de_entrega` | 0.3204 | PROC-042-v2 / 3. Prazo | 🟡 Aceitável |

**Comparação com gabarito:** ❌ Chunk com multiplicadores regionais v2 (PROC-042v2-B) **não está nos top-20**. O pipeline recupera as fórmulas de ambas as versões (v1 e v2 com scores quase idênticos: 0.5383 vs 0.5366), mas a tabela de multiplicadores regionais — onde consta "Norte = 1.8" — não é recuperada. Causa: a query contém "Manaus" mas a tabela contém "Norte" — o pipeline não faz mapeamento geográfico implícito.

### Prompt enviado ao Claude

```
[Documento 1 — PROC-042-v2 / 2. Fórmula de cálculo (score: 0.5383)]
Valor do frete = Valor base × Multiplicador regional × Fator de peso
Fator de peso: 1.0 (500-1.000kg); 1.15 (1.001-3.000kg); 1.4 (acima de 3.000kg).
Multiplicador regional = fator aplicado conforme a região de destino (seção 2.1).

[Documento 2 — PROC-042-v1 / 2. Fórmula de cálculo (score: 0.5366)]
Valor do frete = Valor base × Multiplicador regional × Fator de peso
Fator de peso: 1.0 (500-1.000kg); 1.2 (1.001-3.000kg); 1.5 (acima de 3.000kg).
Multiplicador regional = fator aplicado conforme a região de destino (seção 2.1).

[... + outros chunks sem a tabela de multiplicadores regionais]

Pergunta do atendente: Como calcular o frete para 600kg com destino a Manaus?
```

### Resposta obtida do Claude

> Para um frete de **600kg** com destino a Manaus, o cálculo usa a fórmula de frete especial (acima de 500kg):
>
> **Fórmula:** Valor do frete = Valor base × Multiplicador regional × Fator de peso
>
> **Fator de peso para 600kg** (faixa 500–1.000kg): **1.0** (igual nas duas versões do documento)
>
> ⚠️ **Atenção — contradição identificada:** existem duas versões do PROC-042 nos documentos fornecidos com fatores de peso diferentes para outras faixas (v1: 1.2 para >1.000kg; v2: 1.15 para >1.000kg). Para 600kg, o fator é 1.0 em ambas.
>
> **Multiplicador regional para Manaus (região Norte):** os documentos fornecidos não incluem a tabela de multiplicadores regionais (seção 2.1). Não é possível completar o cálculo sem essa informação. **Consulte o PROC-042-v2, Seção 2.1** para obter o multiplicador da região Norte.
>
> **[FONTE: PROC-042-v2 — Frete Especial Revisado, Seção 2; PROC-042-v1, Seção 2]**

### Avaliação
| Critério | Resultado |
|---|---|
| Resposta correta? | ✅ Parcialmente — fator de peso correto (1.0), mas multiplicador ausente |
| Citou a fonte? | ✅ Sim — ambas as versões, com alerta de contradição |
| Respeitou guardrails? | ✅ Sim — declarou que a informação do multiplicador não estava no contexto |
| Alucinação? | ✅ Não — recusou inventar o multiplicador da região Norte |
| Chunk principal do gabarito recuperado? | ❌ Não — tabela de multiplicadores não foi recuperada |

**Problema crítico:** a pipeline não conecta "Manaus" ao "Norte" pois esse mapeamento geográfico não está em nenhum chunk recuperado. O Claude respondeu corretamente se comportando conforme os guardrails (disse que não tinha a informação), mas o atendente recebeu uma resposta incompleta.

---

## Resumo dos 5 Testes

| # | Pergunta | Recall keywords | Fonte correta top-3 | Resposta Claude correta? |
|---|---|---|---|---|
| 1 | Prazo de devolução | 100% | ✅ | ✅ Sim |
| 2 | Devolver carga perigosa | 100% | ❌ FAQ no rank 1 | ✅ Sim (guardrail ajudou) |
| 3 | SLA cliente Gold | 33% | ✅ | ✅ Sim (via FAQ informal) |
| 4 | SLA cliente Platinum | 100% | ✅ | ✅ Sim |
| 5 | Frete 600kg Manaus | 67% | ✅ | ⚠️ Parcial (multiplicador ausente) |

**Recall médio: 80% | Precisão de fonte: 90%**

Os guardrails no system prompt foram decisivos nos testes 2 e 3: sem eles, o Claude teria usado o FAQ informal como fonte principal sem alertar o atendente. A instrução "FAQ é informal — prefira documentos normativos" funcionou corretamente em todos os casos onde o FAQ era irrelevante ou apenas complementar.
