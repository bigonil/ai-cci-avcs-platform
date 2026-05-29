# ISO 42001 — Roadmap CCI/AVCS

**Versione**: 0.1 — Draft
**Data**: 2026-05-29

## Stato AIMS (AI Management System)

| Clausola ISO 42001 | Titolo | Status | Note |
|-------------------|--------|--------|------|
| 4.1 | Contesto dell'organizzazione | Planned | Da formalizzare con Hera DSI |
| 5.1 | Leadership | Planned | Owner: CTO / CDO |
| 6.1 | Gestione rischi AI | In Progress | Vedere ai-act-mapping.yaml art_9 |
| 7.5 | Informazioni documentate | In Progress | ADR + README per ogni servizio |
| 8.4 | Valutazione impatto AI | Planned | Integrato in hitl.py (art. 14) |
| 9.1 | Monitoraggio e misurazione | In Progress | KPI Prometheus su /metrics |
| 10.1 | Non conformità e azioni correttive | Planned | Workflow audit trail |

## KPI AIMS

- Frequenza di revisione modello: trimestrale
- Incident AI tracking: via audit log (governance-service)
- Bias monitoring: da implementare in Fase 2

## Prossimi passi

1. Formalizzare policy AI con Hera DSI (Q3 2026)
2. Prima audit interna ISO 42001 (Q4 2026)
3. Certificazione esterna (2027)
