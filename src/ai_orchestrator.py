import json
import math
import scipy.stats
import requests

class AIEngineOrchestrator:
    def __init__(self, model_name="llama3"):
        self.model_name = model_name
        # API endpoint local por defecto de Ollama
        self.api_url = "http://localhost:11434/api/generate"

    def calcular_probabilidad_pert(self, duracion_critica, varianza_critica, tiempo_sj):
        """
        Calcula la probabilidad de cumplir con el tiempo programado utilizando
        la distribución normal estándar (z).
        
        :param duracion_critica: E{e_j} - Duración total esperada de la ruta crítica.
        :param varianza_critica: var{e_j} - Sumatoria de las varianzas de las actividades de la ruta crítica.
        :param tiempo_sj: S_j - Tiempo programado ingresado por el usuario.
        :return: Tupla (z, porcentaje_probabilidad)
        """
        if varianza_critica <= 0:
            # Si no hay varianza, no hay incertidumbre
            if tiempo_sj >= duracion_critica:
                return float('inf'), 100.0
            else:
                return float('-inf'), 0.0
            
        # Fórmula z = (S_j - E{e_j}) / sqrt(var{e_j})
        z = (tiempo_sj - duracion_critica) / math.sqrt(varianza_critica)
        
        # Obtener la probabilidad exacta acumulada usando scipy
        probabilidad = scipy.stats.norm.cdf(z)
        porcentaje_probabilidad = probabilidad * 100.0
        
        return z, porcentaje_probabilidad

    def generar_auditoria_estructural(self, datos_grafo_json, tiempo_sj):
        """
        Orquesta el flujo completo: procesa el JSON (extrae el SDD), calcula la 
        probabilidad de éxito y genera un reporte narrativo estructurado a través de Ollama.
        
        :param datos_grafo_json: Dict o String JSON que contiene el bloque SDD generado en backend.
        :param tiempo_sj: Tiempo límite / programado deseado por el usuario.
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

        # Intentar extraer métricas clave del SDD para el cálculo probabilístico de forma tolerante.
        # Ajustar estas claves según la estructura exacta que tenga tu backend en el Hito 2.
        duracion_critica = sdd.get("duracion_ruta_critica", sdd.get("E_ej", 0))
        varianza_critica = sdd.get("varianza_ruta_critica", sdd.get("var_ej", 0))
        
        # Búsqueda profunda en caso de estar en un sub-diccionario (e.g., 'metricas')
        if not duracion_critica and "metricas" in sdd:
            duracion_critica = sdd["metricas"].get("duracion_ruta_critica", 0)
            varianza_critica = sdd["metricas"].get("varianza_ruta_critica", 0)
            
        # 2. Calcular la probabilidad de cumplimiento
        try:
            duracion_critica = float(duracion_critica)
            varianza_critica = float(varianza_critica)
            tiempo_sj = float(tiempo_sj)
        except (ValueError, TypeError):
            duracion_critica = 0.0
            varianza_critica = 0.0
            tiempo_sj = 0.0

        z, probabilidad_pct = self.calcular_probabilidad_pert(duracion_critica, varianza_critica, tiempo_sj)

        # 3. Definir System Prompt
        system_prompt = (
            "Eres un auditor experto en optimización de proyectos e Investigación de Operaciones. "
            "Tu tarea es analizar redes PERT/CPM y generar auditorías estructurales y narrativas de negocio. "
            "REGLA ESTRICTA: Debes basar tu análisis ÚNICA Y EXCLUSIVAMENTE en el bloque 'Structural Diagnostic Data' (SDD) provisto. "
            "Tienes PROHIBIDO alucinar, inventar o suponer datos, nodos, métricas o rutas que no estén explícitamente en el JSON."
        )

        # 4. Definir User Prompt con interpolación limpia
        user_prompt = f"""
A continuación se presenta el bloque pre-procesado SDD (Structural Diagnostic Data) extraído del backend de nuestra red PERT/CPM:

```json
{json.dumps(sdd, indent=2, ensure_ascii=False)}
```

### Datos Probabilísticos Matemáticamente Calculados (No recalcular):
- Tiempo de finalización programado (S_j): {tiempo_sj}
- Duración total de la ruta crítica (E{{e_j}}): {duracion_critica}
- Varianza sumada de la ruta crítica (var{{e_j}}): {varianza_critica}
- Valor de Desviación Normal (Z): {z:.4f}
- Probabilidad exacta de cumplimiento: {probabilidad_pct:.2f}%

### Instrucciones para la Auditoría:
Con base en la información anterior, genera un informe ejecutivo en formato Markdown que contenga **exclusivamente** las siguientes secciones:

1. **Síntesis de Riesgos (Narrativa de Negocio):**
   Traduce las fallas técnicas y los errores topológicos reportados en el SDD (como ciclos, nodos huérfanos, holguras críticas o fallas de flujo) en una narrativa de negocio. Describe cuál es el impacto operativo y señala los cuellos de botella estructurales.

2. **Evaluación de Probabilidad y Riesgo Temporal:**
   Interpreta la probabilidad de éxito ({probabilidad_pct:.2f}%) en relación con el tiempo programado ({tiempo_sj}). Explica claramente qué significa este porcentaje para la viabilidad y salud general del proyecto.

3. **Recomendaciones de Asignación de Recursos:**
   Analiza la brecha entre los tiempos optimistas (a) y pesimistas (b) expuestos en el SDD para las distintas actividades. Basándote en esto, propón estrategias de reasignación de recursos, enfocándote en estabilizar las actividades de la ruta crítica y aquellas con mayor varianza (incertidumbre).
"""

        # 5. Construir payload para la API de Ollama
        payload = {
            "model": self.model_name,
            "system": system_prompt,
            "prompt": user_prompt,
            "stream": False
        }

        # 6. Llamada local a Ollama y Manejo de Excepciones
        try:
            response = requests.post(self.api_url, json=payload, timeout=120)
            response.raise_for_status()
            resultado = response.json()
            
            reporte_markdown = resultado.get("response", "")
            if not reporte_markdown:
                return "Error: El modelo de Ollama procesó la solicitud, pero devolvió una respuesta vacía."
                
            return reporte_markdown
            
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
