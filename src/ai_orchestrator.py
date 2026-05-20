import json
import math
import requests

class AIEngineOrchestrator:
    def __init__(self, model_name="qwen2.5:3b"):
        self.model_name = model_name
        # API endpoint local por defecto de Ollama
        self.api_url = "http://localhost:11434/api/generate"

    def generar_auditoria_estructural(self, datos_grafo_json):
        """
        Orquesta el flujo completo: procesa el JSON (extrae el SDD) y genera 
        un reporte narrativo estructurado a través de Ollama enfocado puramente 
        en análisis topológico estructural.
        
        :param datos_grafo_json: Dict o String JSON que contiene el bloque SDD generado en backend.
        :return: String con el reporte en formato Markdown.
        """
        # 1. Parsear el JSON y extraer el bloque SDD
        if isinstance(datos_grafo_json, str):
            try:
                datos = json.loads(datos_grafo_json)
            except json.JSONDecodeError:
                return "Error: El formato JSON proporcionado no es un JSON válido."
        else:
            datos = datos_grafo_json
            
        sdd = datos.get("SDD", {})
        if not sdd:
            return "Error: No se encontró el bloque 'SDD' en el JSON proporcionado."

        # 2. Definir System Prompt
        system_prompt = (
            "Eres un auditor experto en optimización de proyectos e Investigación de Operaciones. "
            "Tu tarea es analizar la ESTRUCTURA TOPOLÓGICA de redes de proyectos y generar auditorías estructurales. "
            "REGLA ESTRICTA DE ENTRADA: Debes basar tu análisis ÚNICA Y EXCLUSIVAMENTE en el bloque 'Structural Diagnostic Data' (SDD) provisto. "
            "Este proyecto NO incluye análisis de tiempo, duraciones ni probabilidades. Solo estructura de red (DAG, flujos, nodos huérfanos). "
            "Tienes PROHIBIDO alucinar o inventar datos temporales que no existan. "
            "REGLA ESTRICTA DE FORMATO: Devuelve la auditoría directamente como texto formateado en Markdown. "
            "NO envuelvas todo el reporte dentro de bloques de código (no uses triples comillas invertidas como ```markdown al principio o final del informe)."
        )

        # 3. Definir User Prompt con interpolación limpia
        user_prompt = f"""
A continuación se presenta el bloque pre-procesado SDD (Structural Diagnostic Data) extraído de nuestra red topológica:

```json
{json.dumps(sdd, indent=2, ensure_ascii=False)}
```

### Instrucciones para la Auditoría Estructural:
Con base en la información topológica anterior, genera un informe ejecutivo en formato Markdown que contenga **exclusivamente** las siguientes secciones (escribe los títulos y el contenido directamente en texto plano Markdown sin envolverlo todo en un bloque de código):

1. **Diagnóstico de Conectividad (Narrativa Estructural):**
   Interpreta el estado del grafo evaluando si cumple con la propiedad DAG, la unicidad de fuente y sumidero, y la conservación de flujo (si aplica). Explica qué significa que la red esté en este estado para la planificación secuencial del proyecto.

2. **Síntesis de Vulnerabilidades Topológicas:**
   Identifica los errores topológicos y problemas de diseño estructural explícitamente reportados en el JSON (por ejemplo: ciclos, relaciones circulares o nodos huérfanos sin precedencias claras). Si no hay errores, destaca la robustez de la topología.

3. **Recomendaciones Arquitectónicas:**
   Propón acciones correctivas inmediatas a nivel estructural (sin menciones a tiempos, dinero o duraciones probabilísticas). ¿Qué conexiones deberían revisarse? ¿Hay cuellos de botella lógicos?
"""

        # 4. Construir payload para la API de Ollama
        payload = {
            "model": self.model_name,
            "system": system_prompt,
            "prompt": user_prompt,
            "stream": False
        }

        # 5. Llamada local a Ollama y Manejo de Excepciones
        try:
            response = requests.post(self.api_url, json=payload, timeout=120)
            response.raise_for_status()
            resultado = response.json()
            
            reporte_markdown = resultado.get("response", "")
            if not reporte_markdown:
                return "Error: El modelo de Ollama procesó la solicitud, pero devolvió una respuesta vacía."
            
            # Limpiar posibles bloques de código envolventes
            reporte_markdown = reporte_markdown.strip()
            if reporte_markdown.startswith("```markdown"):
                reporte_markdown = reporte_markdown[11:].strip()
            elif reporte_markdown.startswith("```"):
                reporte_markdown = reporte_markdown[3:].strip()
            
            if reporte_markdown.endswith("```"):
                reporte_markdown = reporte_markdown[:-3].strip()
                
            return reporte_markdown
            
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                try:
                    error_json = e.response.json()
                    detail = error_json.get("error", "")
                except Exception:
                    detail = ""
                return (
                    f"**Error: Modelo no encontrado.** El modelo `{self.model_name}` no está instalado en tu servicio local de Ollama.\n\n"
                    f"Por favor, descarga el modelo ejecutando el siguiente comando en tu terminal:\n"
                    f"```bash\nollama pull {self.model_name}\n```\n"
                    f"*(Detalle de error de Ollama: `{detail if detail else e.response.text}`)*"
                )
            return f"**Error de Protocolo HTTP:** La IA respondió con un código de error {e.response.status_code if e.response is not None else 'desconocido'}:\n`{str(e)}`"
        except requests.exceptions.ConnectionError:
            return (
                "**Error Crítico:** No se pudo conectar al servicio local de Ollama. "
                "Asegúrate de que Ollama esté ejecutándose (por ejemplo, en `http://localhost:11434`) "
                f"y que tengas el modelo `{self.model_name}` instalado (`ollama run {self.model_name}`)."
            )
        except requests.exceptions.Timeout:
            return "**Error de Tiempo de Espera:** La solicitud al modelo local tardó demasiado en responder y fue abortada."
        except requests.exceptions.RequestException as e:
            return f"**Error de Comunicación:** Ha ocurrido un error inesperado al intentar comunicarse con la IA:\n`{str(e)}`"
