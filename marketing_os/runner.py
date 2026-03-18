#!/usr/bin/env python3
"""
Marketing OS — Runner CLI
Ejecuta agentes de marketing usando Claude y guarda outputs en /outputs.
"""

import os
import json
import argparse
from datetime import datetime
from pathlib import Path

# Carga variables de entorno desde .env (debe existir con ANTHROPIC_API_KEY)
from dotenv import load_dotenv
load_dotenv(override=True)

import anthropic

# Nota: los clientes de Google Workspace se importan de workspace/ (no google/)
# para evitar conflicto con el namespace package google-auth / google-api-python-client.

# ──────────────────────────────────────────────
# CONFIGURACIÓN
# ──────────────────────────────────────────────

BASE_DIR = Path(__file__).parent
AGENTS_DIR = BASE_DIR / "agents"
CONTEXT_DIR = BASE_DIR / "context"
OUTPUTS_DIR = BASE_DIR / "outputs"

DOCS_DIR   = OUTPUTS_DIR / "docs"
SHEETS_DIR = OUTPUTS_DIR / "sheets"
DRIVE_DIR  = OUTPUTS_DIR / "drive"
LOGS_DIR   = OUTPUTS_DIR / "logs"


# ──────────────────────────────────────────────
# CONFIGURACIÓN DE AGENTES (Phase 4)
# ──────────────────────────────────────────────

def load_agents_config() -> dict:
    """
    Carga context/agents_config.json con las responsabilidades y output_type
    por defecto de los 23 agentes. Se usa para validación y auto-configuración.
    """
    config_path = CONTEXT_DIR / "agents_config.json"
    if not config_path.exists():
        return {}
    with open(config_path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("agents", {})


# Cargado una vez al iniciar el módulo
AGENTS_CONFIG: dict = load_agents_config()


def get_agent_defaults(agent_name: str) -> dict:
    """
    Retorna la configuración por defecto de un agente desde agents_config.json.
    Si el agente no está en el config, retorna valores neutros.
    """
    return AGENTS_CONFIG.get(agent_name, {
        "role": "general",
        "responsibility": "Agente de marketing",
        "output_type": "doc",
        "output_description": "Output generado por el agente",
    })


def validate_agent(agent_name: str) -> None:
    """
    Verifica que el agente existe como carpeta en /agents/ y está en agents_config.json.
    Lanza ValueError con lista de agentes válidos si no se encuentra.
    """
    skill_path = AGENTS_DIR / agent_name / "SKILL.md"
    if not skill_path.exists():
        valid = sorted(p.name for p in AGENTS_DIR.iterdir() if p.is_dir())
        raise ValueError(
            f"[runner] Agente no encontrado: '{agent_name}'\n"
            f"Agentes disponibles: {', '.join(valid)}"
        )


# ──────────────────────────────────────────────
# FUNCIONES DE CARGA
# ──────────────────────────────────────────────

def load_skill(agent_name: str) -> str:
    """Carga el SKILL.md del agente especificado."""
    skill_path = AGENTS_DIR / agent_name / "SKILL.md"
    if not skill_path.exists():
        raise FileNotFoundError(f"Agente no encontrado: {agent_name}\nRuta: {skill_path}")
    return skill_path.read_text(encoding="utf-8")


def load_business_context() -> str:
    """Carga el contexto del negocio desde context/business_context.md."""
    context_path = CONTEXT_DIR / "business_context.md"
    if not context_path.exists():
        raise FileNotFoundError(f"Contexto no encontrado en: {context_path}")
    return context_path.read_text(encoding="utf-8")


def load_task(task_input: dict | str) -> dict:
    """
    Acepta task input como dict o como ruta a un archivo JSON.
    Formato esperado:
    {
        "agent": "copywriting",
        "task_description": "...",
        "output_type": "doc" | "sheet" | "drive"   (opcional, default: "doc")
    }
    """
    if isinstance(task_input, str):
        task_path = Path(task_input)
        if not task_path.exists():
            raise FileNotFoundError(f"Task file no encontrado: {task_path}")
        with open(task_path, encoding="utf-8") as f:
            return json.load(f)
    return task_input


# ──────────────────────────────────────────────
# CONSTRUCCIÓN DEL PROMPT
# ──────────────────────────────────────────────

def build_prompt(skill_md: str, business_context: str, task: dict) -> str:
    """
    Construye el prompt completo para enviar a Claude.
    Combina: contexto del negocio + instrucciones del skill + task input.
    """
    task_json = json.dumps(task, ensure_ascii=False, indent=2)

    prompt = f"""
# CONTEXTO DEL NEGOCIO
{business_context}

---

# INSTRUCCIONES DEL AGENTE (SKILL.md)
{skill_md}

---

# TASK INPUT
{task_json}

---

Genera el output estructurado siguiendo las instrucciones del agente.
- Idioma: Español (Chile)
- Formato: listo para guardar en Google Docs o Google Sheets
- Si es Doc: incluye `title:` y `content:`
- Si es Sheet: incluye `sheet_name:` y `rows:` como array de arrays
- El output es un BORRADOR para revisión humana. No asumas publicación.
""".strip()

    return prompt


# ──────────────────────────────────────────────
# ESTIMACIÓN DE COSTO (Phase 5)
# ──────────────────────────────────────────────

# Precios USD por millón de tokens (input / output)
_MODEL_PRICING: dict[str, tuple[float, float]] = {
    "claude-opus-4-6":    (15.00, 75.00),
    "claude-sonnet-4-6":  ( 3.00, 15.00),
    "claude-haiku-4-5":   ( 0.25,  1.25),
}


def estimate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    """
    Estima el costo en USD de una llamada a Claude según el modelo y tokens usados.
    Usa precios por millón de tokens definidos en _MODEL_PRICING.
    """
    price_in, price_out = _MODEL_PRICING.get(model, (15.00, 75.00))
    return (input_tokens * price_in + output_tokens * price_out) / 1_000_000


# ──────────────────────────────────────────────
# LLAMADA A CLAUDE
# ──────────────────────────────────────────────

def call_claude(prompt: str, model: str = "claude-opus-4-6") -> dict:
    """
    Envía el prompt a la API de Claude y retorna texto + uso de tokens.

    Requiere: ANTHROPIC_API_KEY en .env o variable de entorno.

    Returns:
        {
            "text": str,
            "input_tokens": int,
            "output_tokens": int,
            "model": str,
        }
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "[error] ANTHROPIC_API_KEY no encontrada.\n"
            "Agrega tu clave en el archivo .env:\n"
            "  ANTHROPIC_API_KEY=sk-ant-..."
        )

    try:
        client = anthropic.Anthropic(api_key=api_key)
        mensaje = client.messages.create(
            model=model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        return {
            "text": mensaje.content[0].text,
            "input_tokens": mensaje.usage.input_tokens,
            "output_tokens": mensaje.usage.output_tokens,
            "model": model,
        }

    except anthropic.AuthenticationError:
        raise EnvironmentError("[error] ANTHROPIC_API_KEY inválida. Verifica tu clave.")
    except anthropic.RateLimitError:
        raise RuntimeError("[error] Límite de tasa de Claude alcanzado. Espera un momento y reintenta.")
    except anthropic.APITimeoutError:
        raise RuntimeError("[error] Timeout al conectar con la API de Claude.")
    except anthropic.APIError as e:
        raise RuntimeError(f"[error] Error de API de Claude: {e}")


# ──────────────────────────────────────────────
# GUARDADO DE OUTPUT
# ──────────────────────────────────────────────

# ──────────────────────────────────────────────
# LOGGING (Phase 4)
# ──────────────────────────────────────────────

def log_task(agent_name: str, task_input: dict, result: dict) -> None:
    """
    Registra un resumen de la tarea ejecutada en /outputs/logs/runner.log.
    Cada línea es un objeto JSON independiente (JSONL) para facilitar parseo.
    """
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOGS_DIR / "runner.log"

    config = get_agent_defaults(agent_name)
    entry = {
        "timestamp": datetime.now().isoformat(),
        "agent": agent_name,
        "role": config.get("role", "general"),
        "output_type": result.get("output_type", "doc"),
        "task_description": task_input.get("task_description", "")[:120],
        "saved_path": result.get("saved_path", ""),
        "google_url": (result.get("google") or {}).get("url", ""),
        "content_length": len(result.get("content", "")),
        "tokens_input": (result.get("tokens") or {}).get("input", 0),
        "tokens_output": (result.get("tokens") or {}).get("output", 0),
        "cost_usd": (result.get("tokens") or {}).get("cost_usd", 0.0),
        "status": "ok",
    }

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def save_output(agent_name: str, output_type: str, content: str) -> Path:
    """
    Guarda el output en la carpeta correspondiente según output_type.
    - doc   → /outputs/docs/
    - sheet → /outputs/sheets/
    - drive → /outputs/drive/
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{agent_name}_{timestamp}.txt"

    output_map = {
        "doc": DOCS_DIR,
        "sheet": SHEETS_DIR,
        "drive": DRIVE_DIR,
    }
    target_dir = output_map.get(output_type, DOCS_DIR)
    target_dir.mkdir(parents=True, exist_ok=True)

    output_path = target_dir / filename
    output_path.write_text(content, encoding="utf-8")
    return output_path


# ──────────────────────────────────────────────
# INTEGRACIÓN GOOGLE WORKSPACE
# ──────────────────────────────────────────────

def upload_to_google(agent_name: str, output_type: str, content: str,
                     title: str | None = None) -> dict | None:
    """
    Sube el output a Google Workspace según output_type:
    - doc   → crea un Google Doc  en Drive/MarketingOS/docs/
    - sheet → crea o actualiza un Google Sheet en Drive/MarketingOS/sheets/
    - drive → sube archivo .txt a Drive/MarketingOS/drive/

    Retorna dict con URL e IDs, o None si las credenciales no están disponibles.
    """
    try:
        from workspace.api import create_doc, append_to_sheet, upload_file_to_drive, get_or_create_folder
    except Exception as e:
        print(f"[workspace] No disponible: {e}")
        return None

    try:
        # Carpeta raíz del proyecto en Drive (se crea automáticamente si no existe)
        root_folder = get_or_create_folder("MarketingOS")

        if output_type == "doc":
            doc_folder = get_or_create_folder("docs", parent_id=root_folder)
            doc_title  = title or f"{agent_name} — {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            doc_id     = create_doc(doc_title, content, folder_id=doc_folder)
            return {"doc_id": doc_id, "url": f"https://docs.google.com/document/d/{doc_id}/edit"}

        elif output_type == "sheet":
            sheet_folder = get_or_create_folder("sheets", parent_id=root_folder)
            # Claude debe retornar JSON con {sheet_name, rows} para output tipo sheet
            try:
                parsed     = json.loads(content)
                sheet_name = parsed.get("sheet_name", title or agent_name)
                rows       = parsed.get("rows", [])
            except json.JSONDecodeError:
                # Si no es JSON válido, guardar líneas en una sola columna
                sheet_name = title or agent_name
                rows       = [[line] for line in content.splitlines() if line.strip()]
            sheet_id = append_to_sheet(sheet_name, rows, folder_id=sheet_folder)
            return {"sheet_id": sheet_id, "url": f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit"}

        elif output_type == "drive":
            drive_folder = get_or_create_folder("drive", parent_id=root_folder)
            # Guardar archivo localmente primero, luego subir a Drive
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            tmp_path  = DRIVE_DIR / f"{agent_name}_{timestamp}.txt"
            tmp_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path.write_text(content, encoding="utf-8")
            file_id = upload_file_to_drive(str(tmp_path), folder_id=drive_folder)
            return {"file_id": file_id, "url": f"https://drive.google.com/file/d/{file_id}/view"}

    except Exception as e:
        print(f"[workspace] Error al subir output: {e}")
        return None


# ──────────────────────────────────────────────
# FUNCIÓN PRINCIPAL
# ──────────────────────────────────────────────

def run_agent(agent_name: str, task_input: dict, model: str = "claude-opus-4-6") -> dict:
    """
    Pipeline completo para ejecutar un agente de marketing:
    1. Validar nombre de agente contra agents_config.json y /agents/
    2. Resolver output_type (del task, del config, o default "doc")
    3. Cargar SKILL.md + contexto del negocio
    4. Construir prompt y llamar a Claude
    5. Guardar output localmente en /outputs
    6. Subir a Google Workspace si las credenciales están disponibles
    7. Registrar la ejecución en /outputs/logs/runner.log
    8. Retornar dict con rutas, URLs y contenido del output
    """
    # 1. Validar agente
    validate_agent(agent_name)

    # 2. Resolver output_type: task_input > agents_config.json > "doc"
    agent_config = get_agent_defaults(agent_name)
    output_type = task_input.get("output_type") or agent_config.get("output_type", "doc")
    doc_title = task_input.get("title")

    print(f"[runner] Agente    : {agent_name}  [{agent_config.get('role', 'general')}]")
    print(f"[runner] Tarea     : {str(task_input.get('task_description', ''))[:80]}")
    print(f"[runner] Modelo    : {model}")
    print(f"[runner] Output    : {output_type}  — {agent_config.get('output_description', '')}")

    # 3. Cargar SKILL.md y contexto del negocio
    skill_md = load_skill(agent_name)
    business_context = load_business_context()

    # 4. Construir prompt y llamar a Claude
    prompt = build_prompt(skill_md, business_context, task_input)
    print(f"[runner] Prompt    : {len(prompt)} caracteres — enviando a Claude...")

    claude_response = call_claude(prompt, model=model)
    output = claude_response["text"]
    tokens_in  = claude_response["input_tokens"]
    tokens_out = claude_response["output_tokens"]
    cost_usd   = estimate_cost_usd(model, tokens_in, tokens_out)

    print(f"[runner] Tokens    : {tokens_in} in / {tokens_out} out  (~${cost_usd:.4f} USD)")

    # 5. Guardar localmente
    saved_path = save_output(agent_name, output_type, output)
    print(f"[runner] Local     : {saved_path}")

    # 6. Subir a Google Workspace
    google_result = upload_to_google(agent_name, output_type, output, title=doc_title)
    if google_result:
        print(f"[runner] Google    : {google_result.get('url', 'OK')}")

    result = {
        "agent": agent_name,
        "role": agent_config.get("role", "general"),
        "output_type": output_type,
        "saved_path": str(saved_path),
        "google": google_result,
        "content": output,
        "tokens": {"input": tokens_in, "output": tokens_out, "cost_usd": cost_usd},
    }

    # 7. Registrar en log (incluye tokens y costo)
    log_task(agent_name, task_input, result)

    return result


def run(task_input: dict | str, model: str = "claude-opus-4-6") -> dict:
    """Wrapper de run_agent que acepta task_input como dict o ruta JSON."""
    task = load_task(task_input)
    agent_name = task.get("agent")
    if not agent_name:
        raise ValueError("El task input debe incluir el campo 'agent'.")
    return run_agent(agent_name, task, model=model)


# ──────────────────────────────────────────────
# CLI ENTRY POINT
# ──────────────────────────────────────────────

def list_agents() -> None:
    """Imprime la tabla de agentes disponibles con su rol y output_type por defecto."""
    print("\n── Agentes disponibles (" + str(len(AGENTS_CONFIG)) + ") ─────────────────────────────")
    print(f"{'Agente':<28} {'Rol':<12} {'Output':<8} Responsabilidad")
    print("─" * 90)
    for name, cfg in sorted(AGENTS_CONFIG.items()):
        print(
            f"{name:<28} {cfg.get('role',''):<12} {cfg.get('output_type',''):<8} "
            f"{cfg.get('responsibility','')[:50]}"
        )
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Marketing OS Runner — Ejecuta agentes de marketing con Claude"
    )
    parser.add_argument(
        "--agent",
        help="Nombre del agente (ej: copywriting, social-content)"
    )
    parser.add_argument(
        "--task",
        help="Descripción del task (texto) o ruta a archivo JSON"
    )
    parser.add_argument(
        "--output-type", choices=["doc", "sheet", "drive"],
        help="Tipo de output (default: según agents_config.json)"
    )
    parser.add_argument(
        "--model", default="claude-opus-4-6",
        help="Modelo de Claude a usar (default: claude-opus-4-6)"
    )
    parser.add_argument(
        "--extra", default=None,
        help="JSON adicional de parámetros (ej: '{\"keywords\": [\"fitness\"]}')"
    )
    parser.add_argument(
        "--list", action="store_true",
        help="Listar todos los agentes disponibles con su rol y output type"
    )

    args = parser.parse_args()

    # Modo listado
    if args.list:
        list_agents()
        return

    # Validar argumentos obligatorios
    if not args.agent or not args.task:
        parser.error("Se requiere --agent y --task para ejecutar un agente.")

    task_input: dict = {
        "agent": args.agent,
        "task_description": args.task,
    }

    # output_type solo se agrega si fue pasado explícitamente; si no, agents_config.json lo define
    if args.output_type:
        task_input["output_type"] = args.output_type

    if args.extra:
        try:
            extra = json.loads(args.extra)
            task_input.update(extra)
        except json.JSONDecodeError as e:
            print(f"[error] --extra no es JSON válido: {e}")
            return

    try:
        result = run(task_input, model=args.model)
        print("\n─── OUTPUT ───────────────────────────────")
        print(result["content"])
        print(f"\n[runner] Archivo  : {result['saved_path']}")
        if result.get("google"):
            print(f"[runner] Google   : {result['google'].get('url', '')}")
        print("──────────────────────────────────────────")
    except (EnvironmentError, RuntimeError, FileNotFoundError, ValueError) as e:
        print(f"\n{e}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
