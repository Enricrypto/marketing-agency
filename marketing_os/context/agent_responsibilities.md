# Responsabilidades de los Agentes — Marketing OS

> Referencia para operadores y Phase 5 (Scheduling / Cost Control).
> Fuente de verdad: `context/agents_config.json`

---

## Roles Operacionales

Los 23 agentes se agrupan en 7 roles. Cada rol puede usarse para programar tareas semanales.

| Rol | Agentes | Frecuencia sugerida |
|-----|---------|---------------------|
| **contenido** | copywriting, copy-editing, email-sequence, social-content | Diaria / semanal |
| **cro** | page-cro, signup-flow-cro, onboarding-cro, form-cro, popup-cro, paywall-upgrade-cro | Semanal / mensual |
| **seo** | seo-audit, programmatic-seo, competitor-alternatives, schema-markup | Semanal / mensual |
| **ads** | paid-ads | Semanal |
| **growth** | referral-program, free-tool-strategy, launch-strategy | Por proyecto |
| **estrategia** | marketing-ideas, marketing-psychology, pricing-strategy, ab-test-setup | Mensual |
| **analitica** | analytics-tracking | Semanal |

---

## Tabla Completa de Agentes

| Agente | Rol | Responsabilidad | Output | Destino |
|--------|-----|-----------------|--------|---------|
| `ab-test-setup` | estrategia | Diseñar hipótesis, variantes y plan de medición para experimentos A/B | Plan de experimento con hipótesis, variantes y métricas | Google Doc |
| `analytics-tracking` | analitica | Configurar eventos, objetivos y reportes de analítica digital | Tabla de eventos, propiedades y configuración de GA4/GTM | Google Sheet |
| `competitor-alternatives` | seo | Crear páginas de comparación y alternativas para SEO y ventas | Página tipo 'X vs Y' o 'Alternativas a X' con estructura SEO | Google Doc |
| `copy-editing` | contenido | Revisar, corregir y mejorar copy existente de páginas o emails | Copy editado con comentarios de mejora y versión final | Google Doc |
| `copywriting` | contenido | Escribir o reescribir copy para landing pages, homepage, pricing y features | Copy completo con headline, subheadline, cuerpo y CTA | Google Doc |
| `email-sequence` | contenido | Crear secuencias de email automatizadas: bienvenida, nurture, reactivación | Secuencia de N emails con asunto, cuerpo y CTA por email | Google Doc |
| `form-cro` | cro | Optimizar formularios de captura de leads, contacto y checkout | Análisis de fricciones + recomendaciones de campos y copy | Google Doc |
| `free-tool-strategy` | growth | Planificar herramientas gratuitas para generación de leads y SEO | Plan de herramienta con propósito, funcionalidad y distribución | Google Doc |
| `launch-strategy` | growth | Planificar lanzamientos de producto, features y campañas de pre-lanzamiento | Plan de lanzamiento por fases con canales, mensajes y calendario | Google Doc |
| `marketing-ideas` | estrategia | Generar ideas de marketing personalizadas para el negocio | Lista priorizada de ideas con canal, dificultad e impacto | Google Sheet |
| `marketing-psychology` | estrategia | Aplicar principios de psicología y sesgo cognitivo al copy y diseño | Análisis con principios aplicables y ejemplos concretos | Google Doc |
| `onboarding-cro` | cro | Mejorar la activación y primera experiencia de usuarios nuevos | Flujo de onboarding optimizado con pasos, mensajes y momentos AHA | Google Doc |
| `page-cro` | cro | Optimizar conversiones en cualquier página de marketing | Auditoría de página con problemas detectados y recomendaciones | Google Doc |
| `paid-ads` | ads | Crear y optimizar campañas de Google Ads, Meta Ads y LinkedIn Ads | Tabla de anuncios con títulos, descripciones y audiencias | Google Sheet |
| `paywall-upgrade-cro` | cro | Diseñar paywalls, pantallas de upgrade y gates de features in-app | Copy y estructura de la pantalla de upgrade | Google Doc |
| `popup-cro` | cro | Crear y optimizar popups, modales y overlays de conversión | Copy y flujo del popup con trigger, headline y CTA | Google Doc |
| `pricing-strategy` | estrategia | Diseñar estrategia de precios, tiers y empaquetamiento | Estructura de precios con tiers, features por plan y argumento de valor | Google Doc |
| `programmatic-seo` | seo | Planificar y generar páginas SEO a escala con templates y datos | Lista de URLs, títulos, meta descriptions y variables por template | Google Sheet |
| `referral-program` | growth | Diseñar programas de referidos y afiliados con incentivos virales | Diseño del programa con incentivos, copy e invitación | Google Doc |
| `schema-markup` | seo | Generar JSON-LD de schema markup para rich snippets | Código JSON-LD listo para insertar en el HTML | Google Doc |
| `seo-audit` | seo | Auditar problemas técnicos y on-page de SEO en un sitio web | Tabla de problemas SEO con prioridad y acción recomendada | Google Sheet |
| `signup-flow-cro` | cro | Optimizar flujos de registro y creación de cuenta | Análisis del flujo con copy mejorado y pasos a eliminar | Google Doc |
| `social-content` | contenido | Crear posts para LinkedIn, Instagram, Twitter/X y TikTok | Post completo con texto, hashtags y formato visual | Google Doc |

---

## Tareas Semanales Sugeridas por Rol

### Lunes — Contenido
```bash
python runner.py --agent social-content --task "3 posts para Instagram esta semana"
python runner.py --agent copywriting    --task "Reescribir la sección hero de la landing"
```

### Martes — SEO
```bash
python runner.py --agent seo-audit      --task "Auditar página principal" --output-type sheet
python runner.py --agent programmatic-seo --task "Plantilla para páginas de ciudad" --output-type sheet
```

### Miércoles — Ads
```bash
python runner.py --agent paid-ads --task "Crear 3 anuncios Google Ads para fitness Santiago" --output-type sheet
```

### Jueves — CRO
```bash
python runner.py --agent page-cro    --task "Optimizar landing de registro"
python runner.py --agent form-cro    --task "Revisar formulario de contacto"
```

### Viernes — Analítica + Estrategia
```bash
python runner.py --agent analytics-tracking --task "Plan de eventos para el flujo de checkout" --output-type sheet
python runner.py --agent marketing-ideas    --task "10 ideas para crecer en Santiago este mes" --output-type sheet
```

---

## Notas para Phase 5 (Scheduling)

- `output_type` por defecto ya está definido en `agents_config.json` — no es necesario pasarlo siempre.
- Los agentes de rol `estrategia` son costosos en tokens; ejecutar máximo 1 por semana.
- Los agentes de rol `contenido` son los más frecuentes y de menor costo.
- Ver logs de ejecución en: `/outputs/logs/runner.log`
