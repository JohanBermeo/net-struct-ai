# 🌐 Motor de Validación Estructural de Redes (PERT/CPM) con Agente de IA

## 📝 Descripción del Proyecto
Este software de investigación aplicada modela, valida y audita la estructura lógica de proyectos utilizando la **Teoría de Grafos Dirigidos Acíclicos (DAG)**. El núcleo matemático en Python procesa la topología de la red mientras interactúa dinámicamente con un **Agente de Inteligencia Artificial (Ollama / Qwen 2.5 (3B))** encargado de interpretar los resultados, identificar redundancias estructurales y apoyar la toma de decisiones.

El desarrollo de este sistema da estricto cumplimiento a los componentes obligatorios de la asignatura: el agente de IA interactúa directamente con datos reales y modelados del backend sin reemplazar el rigor matemático del modelo de Investigación de Operaciones.

---

## 🛠️ Stack Tecnológico
* **Frontend & UI:** Streamlit (Tablas dinámicas mediante `st.data_editor` y reactividad en tiempo real).
* **Motor de Grafos:** NetworkX (Validación de aciclicidad, ordenamiento topológico y cálculo de componentes).
* **Agente de IA:** Ollama + Qwen 2.5 (3B) (Despliegue de API local para auditoría y generación de escenarios).

---

## 📐 Abstracción y Modelo Matemático
El backend procesa el proyecto como un Grafo Dirigido Acíclico $G = (V, A)$:
* $V$: Conjunto de **Nodos (Eventos)** que representan hitos de inicio o finalización.
* $A$: Conjunto de **Arcos (Actividades)** dirigidos, definidos por relaciones de precedencia estricta.

### Reglas Topológicas Automatizadas
1. **Unificación de Raíz (Nodo Inicial Único):** Si se introducen múltiples actividades sin predecesores, el sistema crea un **Nodo Origen Virtual (Nodo 1)** para forzar una única raíz.
2. **Detección de Ciclos (Loops):** Validación mediante el algoritmo de ordenamiento topológico de Kahn. Si se detecta un bucle, el procesamiento se detiene para aislar el error lógico.
3. **Identidad de Arcos:** Resolución automática de actividades paralelas entre los mismos eventos mediante la inserción de **nodos intermedios y actividades ficticias** con duración cero.

---

## 🚀 Levantamiento del Agente y Ejecución

### 1. Clonar el Repositorio

```bash
git clone https://github.com/JohanBermeo/net-struct-ai
cd net-struct-ai
```

### 2. Entorno Virtual e Instalación de Dependencias

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**Windows (Símbolo del sistema - CMD):**
```cmd
python -m venv venv
.\venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**Linux / macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Levantamiento del Agente de IA Local (Ollama)

Asegúrese de tener [Ollama](https://ollama.com/) instalado. Puede verificar la instalación y preparar el modelo ejecutable con los siguientes comandos:

```bash
# 1. Verificar que Ollama está instalado correctamente
ollama --version

# 2. Descargar / Actualizar el modelo qwen2.5:3b en local
ollama pull qwen2.5:3b

# 3. Listar los modelos locales descargados para confirmar que qwen2.5:3b está listo
ollama list

# 4. Iniciar y ejecutar el servicio con el modelo qwen2.5:3b
ollama run qwen2.5:3b
```

*Nota: Mantenga este servicio ejecutándose en segundo plano o en una terminal separada mientras utiliza la aplicación.*

### 4. Ejecución del Programa (Interfaz Streamlit)

Existen dos formas de ejecutar el programa en Windows:

#### Opción A: Ejecución automática con un solo comando (Recomendado)
El proyecto incluye un script `run.bat` que automatiza la comprobación de Ollama y el arranque de Streamlit. Ejecute desde su consola o haga doble clic en el archivo:
```powershell
.\run.bat
```

#### Opción B: Ejecución manual
Con el entorno virtual activado y Ollama ejecutándose de fondo, inicie el servidor de desarrollo de Streamlit:
```bash
streamlit run src/app.py
```

La aplicación se abrirá automáticamente en su navegador predeterminado en `http://localhost:8501`.

### 5. Ejecución de la Suite de Pruebas (Tests)

Para ejecutar las pruebas unitarias y verificar el correcto funcionamiento del validador de red (ciclos, unicidad de fuente/destino y conservación de flujo):

```bash
# Ejecutar todas las pruebas unitarias
pytest

# O alternativamente a través del módulo python
python -m pytest

# Ejecutar las pruebas mostrando detalles individuales (modo detallado/verbose)
pytest -v
```

---

# 💻 Interfaz de Usuario y Modo de Uso

## Ingreso de Datos

Introduzca las actividades, sus predecesores inmediatos y duraciones en la matriz de precedencias interactiva de Streamlit (`st.data_editor`).

## Procesamiento Técnico

El motor de `NetworkX` valida la viabilidad del grafo, resuelve actividades ficticias y genera la lista de adyacencia estructurada.

## Auditoría del Agente de IA

El sistema envía la estructura real en formato JSON hacia la API de Qwen 2.5 (3B). El agente devuelve un reporte automatizado en lenguaje natural explicando la lógica del proyecto, detectando cuellos de botella y proponiendo mejoras estructurales.

---

# 📂 Estructura del Repositorio

Cumpliendo con los criterios de calidad y documentación exigidos:

```plaintext
net-struct-ai/
├── README.md                    # Documentación principal del repositorio
├── requirements.txt             # Dependencias Python (Streamlit, NetworkX, Ollama, etc.)
├── .gitignore                   # Exclusiones de control de versiones (venv, cachés, secretos)
├── venv/                        # Entorno virtual local (no versionado; generado al instalar)
│
├── PROYECTO FINAL_IO_IA_15.pdf  # Rúbrica oficial y condiciones obligatorias (opcional)
├── PROYECTO FINAL_IO_IA_16.pdf  # Guía técnica y parámetros complementarios (opcional)
│
├── assets/                      # Recursos gráficos y multimedia
│   └── mapa_mental.pdf          # Mapa mental del tema (agregar al entregar)
│
├── docs/                        # Documentación académica del proyecto
│   └── documento_final.pdf      # Problema, modelo matemático y análisis crítico (agregar al entregar)
│
└── src/                         # Código fuente del sistema ejecutable
    ├── app.py                   # Interfaz de usuario (Streamlit UI)
    ├── ai_orchestrator.py       # Conexión y prompts del Agente de IA (Ollama)
    ├── core_math.py             # Motor de validación de grafos (NetworkX)
    ├── network_model.py         # Modelo de datos PERT/CPM
    └── structural_validator.py  # Validador de consistencia y generación de SDD
```

| Ruta | Descripción |
|------|-------------|
| `src/app.py` | Punto de entrada de Streamlit; orquesta la UI y el flujo de datos. |
| `src/ai_orchestrator.py` | Cliente Ollama y plantillas de prompt para auditoría en lenguaje natural (Qwen 2.5). |
| `src/core_math.py` | Lógica de grafos con NetworkX y utilidades. |
| `src/network_model.py` | Carga e inicialización de actividades. |
| `src/structural_validator.py` | Validación DAG, ciclo, y generación de SDD. |
| `assets/` | Material visual de apoyo (mapa mental, diagramas exportados). |
| `docs/` | Entregables académicos en PDF. |
| `requirements.txt` | Versiones mínimas de Streamlit, NetworkX, pandas, requests y ollama. |

---

# ⚖️ Rúbrica de Evaluación Aplicada

El proyecto se evalúa estrictamente bajo los siguientes criterios de calidad [cite: 2, 3]:

- **Modelamiento (30%)**:  
  Rigor en la formulación matemática de la red y control de precedencias [cite: 2, 3].

- **Implementación (25%)**:  
  Código funcional, ejecutable y libre de fallos en Streamlit [cite: 2, 3].

- **Agente IA (20%)**:  
  Aporte de valor real, interpretación analítica de datos y soporte a la decisión [cite: 2, 3].

- **Análisis (15%)**:  
  Profundidad crítica en la evaluación de la estructura del modelo [cite: 2, 3].

- **Documentación (10%)**:  
  Claridad, organización y profesionalismo en el repositorio y código [cite: 2, 3].
