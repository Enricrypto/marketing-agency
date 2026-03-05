# Phase 5 — Cost Control & Operational Schedule

## Objetivo
Optimizar la ejecución de los 23 agentes de Marketing OS bajo un presupuesto de $20/mes de Claude Code (~400–500k tokens).
Maximizar impacto en contenido y métricas, minimizar uso innecesario de tokens.

---

## Agentes Críticos (Alto ROI)
| Agente | Frecuencia | Tamaño de batch | Tipo de salida | Notas |
|--------|-----------|----------------|---------------|-------|
| copywriting | Semanal | 1–2 posts | Doc | Contenido blog principal |
| social-content | Semanal | 3–5 posts | Doc | Posts para redes sociales |
| analytics-tracking | Semanal | Individual | Sheet | Métricas + gráficos |
| paid-ads | Semanal | 2–3 anuncios | Doc | Google Ads / Meta Ads |
| email-sequence | Semanal | 1 campaña | Doc | Emails automatizados |

---

## Agentes Importantes (SEO & Conversion)
| Agente | Frecuencia | Tamaño de batch | Tipo de salida | Notas |
|--------|-----------|----------------|---------------|-------|
| seo-audit | Bi-semanal | 1 auditoría | Sheet | Auditoría técnica y on-page |
| page-cro | Bi-semanal | 1 landing page | Doc | Optimización de páginas |
| form-cro | Bi-semanal | 1–2 formularios | Doc | Captura de leads |
| popup-cro | Bi-semanal | 1–2 popups | Doc | Conversión y engagement |
| schema-markup | Bi-semanal | 1–2 páginas | Doc | Estructura y rich snippets |
| ab-test-setup | Bi-semanal | 1–2 tests | Doc | Plan de experimentos |

---

## Agentes de Apoyo (Mensual / On-demand)
| Agente | Frecuencia | Tamaño de batch | Tipo de salida | Notas |
|--------|-----------|----------------|---------------|-------|
| marketing-ideas | Mensual | 5 ideas | Doc | Brainstorming de estrategias |
| launch-strategy | Mensual | 1–2 lanzamientos | Doc | Plan de lanzamientos |
| pricing-strategy | Mensual | 1 análisis | Doc | Ajustes de precios |
| competitor-alternatives | Mensual | 3–5 competidores | Sheet | Benchmarking |
| free-tool-strategy | On-demand | Según necesidad | Doc | Herramientas / lead magnets |
| onboarding-cro | On-demand | 1 flujo | Doc | Optimización de onboarding |
| paywall-upgrade-cro | On-demand | 1 flujo | Doc | Momentos de upsell |
| referral-program | On-demand | 1 lanzamiento | Doc | Programa de referidos |
| marketing-psychology | On-demand | 1–2 referencias | Doc | Modelos mentales y heurísticas |

---

## Recomendaciones de Ejecución

1. **Batching**: ejecutar tareas de alto volumen (social-content, copywriting, paid-ads) en un solo run semanal para ahorrar tokens.
2. **Individual**: mantener tareas de CRO, auditorías y métricas separadas para revisión humana.
3. **Human Review Loop**: revisar y aprobar todo contenido antes de publicación para evitar re-triggers innecesarios.
4. **Monitoreo de Tokens**: registrar tokens usados por agente en `/outputs/logs/` para no superar límite mensual.
5. **Priorización Flexible**: si se acerca el límite de tokens, ejecutar solo agentes críticos y posponer apoyo / on-demand.

---

## Ejemplo de Calendario Semanal

| Día | Agentes | Tarea |
|-----|---------|-------|
| Lunes | analytics-tracking, seo-audit | Métricas + revisión SEO |
| Martes | copywriting | 1–2 posts blog |
| Miércoles | social-content | 3–5 posts redes sociales |
| Jueves | paid-ads, page-cro | Ads + landing optimizada |
| Viernes | email-sequence, ab-test-setup | Campañas + plan tests |
| Sábado | on-demand | marketing-ideas, competitor-alternatives |
| Domingo | Human review | Aprobar contenidos Docs / Sheets |

---

**Nota**: Este plan maximiza impacto semanal y mantiene consumo de tokens bajo control.
Los outputs siempre se guardan como **borradores** en Google Docs/Sheets/Drive para revisión humana.
