"""
Marketing OS — WorkflowRunner Base Class (Phase 4)

Clase base para todos los workflows de WashDog.
Gestiona:
  - Creación y cierre de registros en la tabla `workflows`
  - Ejecución y logging de pasos individuales (tabla `steps`)
  - Guardado de contenido generado (tabla `content_outputs`)
  - Tracking de tokens y costo acumulado
"""

import time
import uuid
from datetime import datetime
from pathlib import Path
import sys

# Asegurar que el directorio raíz esté en el path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db import db, init_db, insert_row, update_row
from runner import call_claude, estimate_cost_usd


class WorkflowRunner:
    """
    Gestor de workflows de marketing para WashDog.

    Uso típico:
        wf = WorkflowRunner("blog_post", "cuidado del pelaje", "peluquería canina Santiago")
        try:
            result = wf.run_step("outline", prompt, agent_name="copywriting")
            wf.save_content("blog", title, content)
            wf.complete()
        except Exception as e:
            wf.fail(str(e))
            raise
    """

    def __init__(
        self,
        workflow_type: str,
        topic: str,
        target_keyword: str = "",
        city: str = "Santiago",
    ) -> None:
        """
        Args:
            workflow_type:    Tipo de workflow (blog_post | landing_page | seasonal_campaign)
            topic:            Tema o nombre de la ejecución
            target_keyword:   Keyword SEO objetivo
            city:             Ciudad objetivo (default: Santiago)
        """
        init_db()  # Crea las tablas si no existen (idempotente)

        self.workflow_id   = str(uuid.uuid4())
        self.workflow_type = workflow_type
        self.topic         = topic
        self.target_keyword = target_keyword
        self.city          = city
        self.steps_log: list[dict] = []  # historial de steps para resumen final

        self._create_workflow()

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def _create_workflow(self) -> None:
        insert_row("workflows", {
            "id":             self.workflow_id,
            "type":           self.workflow_type,
            "topic":          self.topic,
            "target_keyword": self.target_keyword,
            "city":           self.city,
            "status":         "running",
            "started_at":     datetime.now().isoformat(),
        })
        print(
            f"\n[workflow] ▶ {self.workflow_type.upper()} — {self.topic}\n"
            f"[workflow]   ID: {self.workflow_id[:8]}  City: {self.city}"
        )

    def complete(self) -> None:
        """Marca el workflow como completado y muestra resumen de costo."""
        update_row("workflows", self.workflow_id, {
            "status":      "completed",
            "finished_at": datetime.now().isoformat(),
        })
        total_cost   = sum(s["cost_usd"] for s in self.steps_log)
        total_tokens = sum(s["tokens_in"] + s["tokens_out"] for s in self.steps_log)
        print(
            f"[workflow] ✓ Completado — {len(self.steps_log)} steps  "
            f"| {total_tokens:,} tokens  | ${total_cost:.4f} USD"
        )

    def fail(self, error: str) -> None:
        """Marca el workflow como fallido."""
        update_row("workflows", self.workflow_id, {
            "status":      "failed",
            "finished_at": datetime.now().isoformat(),
        })
        print(f"[workflow] ✗ Fallido — {error}")

    # ── Ejecución de steps ────────────────────────────────────────────────────

    def run_step(
        self,
        step_name: str,
        prompt: str,
        agent_name: str = "claude",
        model: str = "claude-sonnet-4-6",
    ) -> str:
        """
        Ejecuta un step de AI, mide tiempo, registra tokens y costo.

        Args:
            step_name:  Nombre descriptivo del step (ej: "keyword_research")
            prompt:     Prompt completo para Claude
            agent_name: Agente de marketing responsable del step
            model:      Modelo Claude a usar

        Returns:
            Texto generado por Claude.

        Raises:
            Exception si Claude falla (el step se marca como 'failed').
        """
        step_id = str(uuid.uuid4())
        start   = time.monotonic()
        print(f"[workflow]   → {step_name} ({model.split('-')[1]})...")

        try:
            result    = call_claude(prompt, model=model)
            text      = result["text"]
            tokens_in  = result["input_tokens"]
            tokens_out = result["output_tokens"]
            cost       = estimate_cost_usd(model, tokens_in, tokens_out)
            duration   = int((time.monotonic() - start) * 1000)

            insert_row("steps", {
                "id":           step_id,
                "workflow_id":  self.workflow_id,
                "step_name":    step_name,
                "agent_name":   agent_name,
                "status":       "completed",
                "duration_ms":  duration,
                "token_input":  tokens_in,
                "token_output": tokens_out,
                "cost_usd":     cost,
                "created_at":   datetime.now().isoformat(),
            })

            self.steps_log.append({
                "step":       step_name,
                "cost_usd":   cost,
                "tokens_in":  tokens_in,
                "tokens_out": tokens_out,
                "duration_ms": duration,
            })

            print(f"[workflow]     ✓ {step_name}  {tokens_in}+{tokens_out} tok  ${cost:.4f}  {duration}ms")
            return text

        except Exception as e:
            duration = int((time.monotonic() - start) * 1000)
            insert_row("steps", {
                "id":          step_id,
                "workflow_id": self.workflow_id,
                "step_name":   step_name,
                "agent_name":  agent_name,
                "status":      "failed",
                "duration_ms": duration,
                "created_at":  datetime.now().isoformat(),
            })
            print(f"[workflow]     ✗ {step_name} — {e}")
            raise

    # ── Guardado de contenido ─────────────────────────────────────────────────

    def save_content(
        self,
        content_type: str,
        title: str,
        content: str,
        meta_description: str = "",
    ) -> str:
        """
        Persiste el contenido generado en la tabla content_outputs.

        Args:
            content_type:     "blog" | "landing" | "campaign" | "ad_copy"
            title:            Título del contenido
            content:          Texto completo generado
            meta_description: Meta description SEO (opcional)

        Returns:
            output_id (str) — ID del registro creado.
        """
        output_id  = str(uuid.uuid4())
        word_count = len(content.split())

        insert_row("content_outputs", {
            "id":               output_id,
            "workflow_id":      self.workflow_id,
            "content_type":     content_type,
            "title":            title,
            "meta_description": meta_description,
            "content":          content,
            "word_count":       word_count,
            "created_at":       datetime.now().isoformat(),
        })

        print(f"[workflow]   ✓ Contenido guardado: '{title[:60]}' ({word_count} palabras)")
        return output_id
