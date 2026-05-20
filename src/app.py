import streamlit as st
import pandas as pd
import networkx as nx
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import math

from network_model import PERTNetwork
from structural_validator import validate_network_structure
from ai_orchestrator import AIEngineOrchestrator

# Configuración principal de la página para un aspecto profesional
st.set_page_config(
    page_title="Validador Estructural PERT/CPM",
    page_icon="🕸️",
    layout="wide"
)


def generar_plantilla_csv():
    """Genera un archivo CSV de plantilla para que el usuario lo descargue."""
    df_plantilla = pd.DataFrame({
        "Actividad": ["A", "B", "C", "D"],
        "Dependencias": ["", "", "A", "A, B"]
    })
    return df_plantilla.to_csv(index=False).encode('utf-8')


def validar_datos_frontend(df: pd.DataFrame) -> list:
    """
    Valida las reglas de negocio en el frontend antes de enviar al motor matemático.
    Retorna una lista de strings con los errores encontrados.
    """
    errores = []

    # Verificar columnas requeridas
    columnas_requeridas = ["Actividad", "Dependencias"]
    columnas_faltantes = [col for col in columnas_requeridas if col not in df.columns]
    if columnas_faltantes:
        errores.append(f"Faltan las siguientes columnas requeridas: {', '.join(columnas_faltantes)}")
        return errores

    # Crear copia local y rellenar nulos
    df_temp = df.copy()
    df_temp["Actividad"] = df_temp["Actividad"].fillna("").astype(str).str.strip()
    df_temp["Dependencias"] = df_temp["Dependencias"].fillna("").astype(str).str.strip()

    # Verificar si hay actividades vacías
    actividades_vacias = df_temp[df_temp["Actividad"] == ""]
    if not actividades_vacias.empty:
        errores.append("La columna 'Actividad' no puede contener nombres vacíos.")

    # Verificar duplicados en actividades
    actividades = [a for a in df_temp["Actividad"].tolist() if a != ""]
    duplicados = set([x for x in actividades if actividades.count(x) > 1])
    if duplicados:
        errores.append(f"Existen nombres de actividad duplicados: {', '.join(duplicados)}")

    # Validar dependencias de cada fila
    set_actividades = set(actividades)
    for idx, fila in df_temp.iterrows():
        act_id = fila["Actividad"]
        if act_id == "":
            continue
        
        deps_str = fila["Dependencias"]
        if deps_str and deps_str.lower() != 'nan':
            # Separar por comas y limpiar espacios
            deps = [d.strip() for d in deps_str.split(",") if d.strip()]
            for dep in deps:
                if dep == act_id:
                    errores.append(f"Actividad '{act_id}': no puede depender de sí misma.")
                elif dep not in set_actividades:
                    errores.append(f"Actividad '{act_id}': depende de '{dep}', pero '{dep}' no existe en la tabla de actividades.")
                    
    return errores





def main():
    st.title("⚙️ Motor de Validación Estructural y Auditoría IA (PERT/CPM)")

    # ---------------------------------------------------------
    # Layout de Entrada de Datos
    # ---------------------------------------------------------
    st.markdown("""
    Construya la topología de la red definiendo las actividades y sus relaciones a través de nodos origen y destino.
    Puede usar la edición manual en pantalla o cargar un archivo con los datos.
    """)

    if 'datos_pert' not in st.session_state:
        st.session_state.datos_pert = pd.DataFrame({
            "Actividad": ["A", "B", "C", "D"],
            "Dependencias": ["", "", "A", "A, B"]
        })

    tab_manual, tab_archivo = st.tabs(["📝 Edición Manual Dinámica", "📁 Carga de Archivos"])

    with tab_manual:
        st.subheader("Tabla de Actividades")
        st.info("Agregue, edite o elimine filas dinámicamente.")
        df_editado = st.data_editor(
            st.session_state.datos_pert,
            num_rows="dynamic",
            width="stretch",
            hide_index=True,
            column_config={
                "Actividad": st.column_config.TextColumn("Actividad", required=True, help="ID único de la actividad"),
                "Dependencias": st.column_config.TextColumn("Dependencias (predecesores separados por comas)", required=False, help="Lista de actividades precedentes separadas por comas (ej: A, B). Dejar vacío si no tiene."),
            },
            key="tabla_editor"
        )

    with tab_archivo:
        st.subheader("Carga e Importación de Datos de Red")
        col1, col2 = st.columns([1, 2])
        with col1:
            st.markdown("**Exportar Datos**")
            st.download_button(
                label="📥 Descargar Tabla (.csv)",
                data=df_editado.to_csv(index=False).encode('utf-8') if 'df_editado' in locals() else st.session_state.datos_pert.to_csv(index=False).encode('utf-8'),
                file_name="tabla_actividades_pert.csv",
                mime="text/csv",
                width="stretch"
            )
        with col2:
            st.markdown("**Carga de Archivo**")
            archivo_subido = st.file_uploader("Sube tu archivo (Excel o CSV)", type=["csv", "xlsx", "xls"])
            if archivo_subido is not None:
                try:
                    if archivo_subido.name.endswith('.csv'):
                        df_cargado = pd.read_csv(archivo_subido)
                    else:
                        df_cargado = pd.read_excel(archivo_subido)

                    if st.button("⬇️ Aplicar datos del archivo a la tabla", type="secondary"):
                        st.session_state.datos_pert = df_cargado
                        if "tabla_editor" in st.session_state:
                            del st.session_state.tabla_editor
                        st.success("¡Datos aplicados! Vaya a la pestaña 'Edición Manual Dinámica' para verlos.")
                        st.rerun()
                except Exception as e:
                    st.error(f"Error al procesar el archivo: {str(e)}")

    st.divider()

    # ---------------------------------------------------------
    # Botón de Acción Centralizado
    # ---------------------------------------------------------
    if st.button("🚀 Ejecutar Auditoría Estructural y de IA", type="primary", width="stretch"):
        df_final = df_editado.copy() if 'df_editado' in locals() else st.session_state.datos_pert.copy()

        # Filtrar filas completamente vacías o nulas que el usuario pudo agregar
        # accidentalmente en st.data_editor con num_rows="dynamic"
        df_final = df_final.dropna(how="all")
        df_final = df_final[~(df_final.astype(str).apply(lambda col: col.str.strip()).eq("").all(axis=1))]
        df_final = df_final.reset_index(drop=True)

        if df_final.empty:
            st.error("🚨 La tabla de actividades está vacía. Agregue al menos una actividad.")
            return

        errores_frontend = validar_datos_frontend(df_final)
        if errores_frontend:
            st.error("🚨 Se encontraron errores en la entrada de datos:")
            for e in errores_frontend:
                st.warning(f"• {e}")
            return

        # 1. Cargar datos en el Modelo de Red (Hito 1)
        try:
            datos_formateados = []
            for _, fila in df_final.iterrows():
                act_id = str(fila['Actividad']).strip()
                deps_str = str(fila.get('Dependencias', '')).strip()
                deps_list = [d.strip() for d in deps_str.split(',') if d.strip()] if deps_str and deps_str.lower() != 'nan' else []
                datos_formateados.append({
                    'id': act_id,
                    'predecessors': deps_list
                })
            red_pert = PERTNetwork()
            red_pert.cargar_desde_lista(datos_formateados)
        except (ValueError, TypeError) as e:
            st.error(f"❌ Error de validación del modelo PERT (Backend): {str(e)}")
            return
        except Exception as e:
            st.error(f"❌ Error inesperado al inicializar el modelo PERT: {str(e)}")
            return

        # 2. Validación Estructural y Generación del SDD (Hito 2)
        try:
            resultado_validacion = validate_network_structure(red_pert)
            sdd = resultado_validacion.get("SDD", {}) if isinstance(resultado_validacion, dict) else {}
        except Exception as e:
            st.error(f"❌ Error crítico en la validación estructural (Hito 2): {str(e)}")
            return

        # Extracción de indicadores topológicos desde el SDD
        estado_red = sdd.get("estado_red", sdd)
        es_dag = estado_red.get("es_dag", True)
        unicidad = estado_red.get("unicidad", True)
        conservacion = estado_red.get("conservacion_flujo", True)
        errores_topologicos = sdd.get("errores_topologicos", [])

        # ---------------------------------------------------------------
        # Control de flujo estricto: Bloqueo ante fallas estructurales.
        # Si el grafo contiene ciclos o viola la unicidad de fuente/destino,
        # la progresión cronológica queda invalidada y NO se debe llamar
        # a AIEngineOrchestrator ni a Ollama.
        # ---------------------------------------------------------------
        hay_falla_critica = (not es_dag) or (not unicidad)

        if hay_falla_critica or errores_topologicos:
            st.error("🚨 ERROR ESTRUCTURAL GRAVE DETECTADO")
            st.markdown(
                "Un grafo con **bucles (ciclos)** o sin **unicidad de origen/destino** invalida "
                "la progresión cronológica requerida por la Investigación de Operaciones (PERT/CPM)."
            )
            st.warning(
                "⛔ No se puede proceder con la Auditoría de IA "
                "hasta que se resuelvan las fallas topológicas."
            )

            # Mostrar lista explícita de cada error detectado
            if errores_topologicos:
                st.subheader("Detalles de las fallas lógicas:")
                for error in errores_topologicos:
                    st.error(f"❌ {error}")

            if not es_dag:
                st.error("❌ Se detectó al menos un ciclo en el grafo. Elimine las dependencias circulares.")
            if not unicidad:
                st.error("❌ La red no posee una única fuente y/o un único destino. Revise los nodos huérfanos.")

            # Bloqueo total: no se renderiza ninguna pestaña de análisis.
            return

        st.success("✅ La estructura de la red es válida. Desplegando resultados...")

        # 3. Pestañas de Resultados (Tabs)
        tab_topologia, tab_ia = st.tabs([
            "📊 Diagnóstico Topológico y Red",
            "🤖 Informe de Auditoría IA (Ollama)"
        ])

        # ==========================================
        # Pestaña 1: Diagnóstico Topológico y Red
        # ==========================================
        with tab_topologia:
            st.subheader("Evaluación de Reglas de Oro Topológicas")
            col_dag, col_uni, col_flujo = st.columns(3)

            with col_dag:
                st.success("✅ Grafo Dirigido Acíclico (DAG)")

            with col_uni:
                st.success("✅ Unicidad (1 Fuente / 1 Destino)")

            with col_flujo:
                if conservacion:
                    st.success("✅ Conservación de Flujo")
                else:
                    st.warning("⚠️ Posible falla de flujo en nodos de trasbordo")

            # Renderizado visual del grafo usando NetworkX y Matplotlib con nodos rectangulares PERT
            st.subheader("Representación Visual del Grafo")
            fig = None
            try:
                import matplotlib.patches as patches
                
                G = red_pert.grafo
                
                # Intentar calcular distribución en capas (topological generations)
                try:
                    generaciones = list(nx.topological_generations(G))
                    pos = {}
                    
                    # 1. Asignar coordenadas X basadas en las generaciones
                    for col_idx, gen in enumerate(generaciones):
                        for node in gen:
                            pos[node] = [col_idx * 3.0, 0.0]
                            
                    # 2. Propagación inteligente de Y para evitar solapamientos de arcos y nodos
                    topo_order = list(nx.topological_sort(G))
                    y_coords = {n: 0.0 for n in G.nodes()}
                    y_sums = {n: 0.0 for n in G.nodes()}
                    y_counts = {n: 0 for n in G.nodes()}
                    
                    fuentes = [n for n in G.nodes() if G.in_degree(n) == 0]
                    for f in fuentes:
                        y_counts[f] = 1
                        y_sums[f] = 0.0
                        
                    for u in topo_order:
                        y_u = y_sums[u] / y_counts[u] if y_counts[u] > 0 else 0.0
                        y_coords[u] = y_u
                        
                        # Obtener sucesores conectados por arcos reales (no ficticios)
                        sucesores_reales = [
                            v for v in G.successors(u)
                            if not G[u][v].get("es_ficticia", False)
                        ]
                        num_succ = len(sucesores_reales)
                        for idx, v in enumerate(sucesores_reales):
                            if num_succ == 1:
                                y_sums[v] += y_u
                                y_counts[v] += 1
                            else:
                                offset = (idx - (num_succ - 1) / 2.0) * 1.5
                                y_sums[v] += (y_u + offset)
                                y_counts[v] += 1
                                
                        # Propagar a sucesores ficticios solo si no tienen otras entradas reales
                        for v in G.successors(u):
                            if G[u][v].get("es_ficticia", False):
                                in_reales = [
                                    src for src, _ in G.in_edges(v)
                                    if not G[src][v].get("es_ficticia", False)
                                ]
                                if len(in_reales) == 0:
                                    y_sums[v] += y_u
                                    y_counts[v] += 1
                                    
                    # 3. Aplicar Y a las posiciones finales
                    for node in G.nodes():
                        pos[node][1] = y_coords[node]
                        
                except nx.NetworkXUnfeasible:
                    # En caso de ciclos, caer en spring_layout para evitar errores de ordenación
                    pos = nx.spring_layout(G, seed=42)

                # Determinar dimensiones de la figura dinámicamente basadas en el layout
                xs = [p[0] for p in pos.values()]
                ys = [p[1] for p in pos.values()]
                width_fig = max(10, (max(xs) - min(xs)) * 1.8)
                height_fig = max(6, (max(ys) - min(ys)) * 1.8)
                
                fig, ax = plt.subplots(figsize=(width_fig, height_fig))
                
                # Ajustar límites y ocultar ejes
                ax.set_xlim(min(xs) - 1.0, max(xs) + 1.0)
                ax.set_ylim(min(ys) - 1.0, max(ys) + 1.0)
                ax.set_axis_off()

                # Dimensiones de las cajas de nodos
                W = 1.0
                H = 0.6

                # 1. Dibujar los parches rectangulares para cada nodo y guardar referencias
                node_patches = {}
                for node, (x, y) in pos.items():
                    # Rectángulo principal de borde negro y fondo blanco
                    rect = patches.Rectangle(
                        (x - W/2, y - H/2), W, H,
                        linewidth=1.5, edgecolor='black', facecolor='white', zorder=3
                    )
                    ax.add_patch(rect)
                    node_patches[node] = rect
                    
                    # Línea horizontal divisoria (mitad del nodo)
                    ax.plot([x - W/2, x + W/2], [y, y], color='black', linewidth=1.5, zorder=4)
                    
                    # Línea vertical divisoria inferior (mitad inferior del nodo)
                    ax.plot([x, x], [y - H/2, y], color='black', linewidth=1.5, zorder=4)
                    
                    # Texto del número de nodo (arriba)
                    ax.text(
                        x, y + H/4, str(node),
                        color='black', fontsize=12, fontweight='bold',
                        ha='center', va='center', zorder=5
                    )

                # Mapear actividades ficticias a una secuencia S1, S2, S3...
                dummy_mapping = {}
                dummy_index = 1
                for u, v, d in G.edges(data=True):
                    if d.get("es_ficticia", False):
                        act_id = d.get("id_actividad", "")
                        if act_id not in dummy_mapping:
                            dummy_mapping[act_id] = f"S{dummy_index}"
                            dummy_index += 1

                # 2. Dibujar flechas entre los nodos
                for u, v, d in G.edges(data=True):
                    es_fict = d.get("es_ficticia", False)
                    
                    # ConnectionPatch conecta el borde de los rectángulos automáticamente
                    con = patches.ConnectionPatch(
                        xyA=pos[u], xyB=pos[v], coordsA="data", coordsB="data",
                        patchA=node_patches[u], patchB=node_patches[v],
                        arrowstyle="-|>", mutation_scale=15,
                        linestyle="--" if es_fict else "-",
                        color="black", linewidth=1.5, zorder=2
                    )
                    ax.add_artist(con)
                    
                    # Colocar etiquetas en el punto medio de la arista
                    x1, y1 = pos[u]
                    x2, y2 = pos[v]
                    x_mid = (x1 + x2) / 2.0
                    y_mid = (y1 + y2) / 2.0
                    
                    label = dummy_mapping[d.get("id_actividad", "")] if es_fict else d.get("id_actividad", "")
                    
                    # Desplazamiento inteligente de etiquetas
                    dx = x2 - x1
                    dy = y2 - y1
                    if abs(dx) > abs(dy):
                        # Mayormente horizontal: desplazar texto hacia arriba
                        ax.text(
                            x_mid, y_mid + 0.15, label,
                            color="black", fontsize=10, fontweight="bold",
                            ha="center", va="bottom",
                            bbox=dict(facecolor='white', edgecolor='none', alpha=0.8, pad=1),
                            zorder=4
                        )
                    else:
                        # Mayormente vertical: desplazar texto hacia la derecha
                        ax.text(
                            x_mid + 0.15, y_mid, label,
                            color="black", fontsize=10, fontweight="bold",
                            ha="left", va="center",
                            bbox=dict(facecolor='white', edgecolor='none', alpha=0.8, pad=1),
                            zorder=4
                        )

                fig.tight_layout()
                st.pyplot(fig)

            except Exception as e:
                st.warning(f"No se pudo renderizar la representación gráfica: {str(e)}")
            finally:
                if fig is not None:
                    plt.close(fig)

        # ==========================================
        # Pestaña 2: Informe de Auditoría IA (Ollama)
        # ==========================================
        with tab_ia:
            st.subheader("🤖 Informe Ejecutivo Analítico")
            with st.spinner("Generando reporte de IA con Qwen 2.5 (Ollama)... Este proceso puede tardar unos segundos."):
                try:
                    orquestador_ia = AIEngineOrchestrator()
                    reporte_md = orquestador_ia.generar_auditoria_estructural(
                        datos_grafo_json=resultado_validacion
                    )
                    st.markdown(reporte_md, unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"Falla al conectar con Ollama o al procesar la IA: {str(e)}")


if __name__ == "__main__":
    main()
