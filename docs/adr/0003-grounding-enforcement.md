# ADR-0003: Citation enforcement come guardrail architetturale obbligatorio

**Status**: Accepted
**Date**: 2026-05-29

## Context

CCI/AVCS è classificato come sistema AI ad alto rischio (EU AI Act art. 6, allegato III).
Ogni affermazione dell'LLM verso l'utente deve essere tracciabile a evidenza documentale
specifica. Il KPI di allucinazione libera è < 1% (misurato come % di frasi senza
citazione valida). Disabilitare il guardrail in produzione azzera la credibilità
del sistema agli occhi di auditor e stakeholder (Hera, AOU Modena, Ducati Corse).

## Decision

Implementare `cci_llm.citation_parser` come **post-processor obbligatorio** su ogni
completamento LLM destinato all'utente. Il parser:

1. Estrae pattern `[source: chunk_id]` o `[doc_name #chunk_N]` da ogni frase
2. Verifica che il `chunk_id` esista nella sessione di retrieval corrente
3. Se una frase non ha citazione valida → rigetta l'output e re-prompt con istruzione rafforzata (max 2 retry)
4. Se dopo 2 retry persiste la violazione → ritorna errore strutturato (mai output non groundato all'utente)

Il flag `strict=False` è consentito SOLO nei test (fixture con dati sintetici senza chunker reale).
In produzione e staging: sempre `strict=True`.

## Consequences

**Positive**:
- Zero hallucination libera come proprietà architetturale, non come speranza
- Ogni output è verificabile da auditor esterno
- AI Act art. 13 (transparency) soddisfatto by design

**Negative**:
- Latenza aggiuntiva (1-2 retry in casi edge): accettabile rispetto al rischio reputazionale
- Costo token leggermente superiore per i re-prompt

## Alternatives considered

- **Guardrail solo a livello di prompt**: insufficiente, LLM può ignorare istruzioni nel prompt system
- **Post-hoc filtering**: rimuove le frasi senza citazione → output troncato, peggiore UX del rifiuto esplicito
