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
        "id_actividad": ["A", "B", "C", "Ficticia_1"],
        "nodo_origen": [1, 2, 2, 3],
        "nodo_destino": [2, 3, 4, 4],
        "es_ficticia": [False, False, False, True]
    })
    return df_plantilla.to_csv(index=False).encode('utf-8')


def validar_datos_frontend(df: pd.DataFrame) -> list:
    """
    Valida las reglas de negocio en el frontend antes de enviar al motor matemático.
    Retorna una lista de strings con los errores encontrados.
    """
    errores = []

    # Verificar columnas requeridas primero (antes de cualquier acceso por nombre)
    columnas_requeridas = ["id_actividad", "nodo_origen", "nodo_destino", "es_ficticia"]
    columnas_faltantes = [col for col in columnas_requeridas if col not in df.columns]
    if columnas_faltantes:
        errores.append(f"Faltan las siguientes columnas requeridas: {', '.join(columnas_faltantes)}")
        return errores

    # Verificar campos vacíos o con solo espacios en blanco
    if df.isnull().values.any() or (df.astype(str).apply(lambda col: col.str.strip()).eq("").any().any()):
        errores.append("La tabla contiene campos vacíos. Por favor complete todas las celdas.")
        return errores

    # Iterar por cada fila para validaciones específicas
    for idx, fila in df.iterrows():
        id_act = str(fila.get("id_actividad", f"Fila {idx+1}")).strip()

        try:
            origen = float(fila["nodo_origen"])
            destino = float(fila["nodo_destino"])

            if not origen.is_integer() or not destino.is_integer():
                errores.append(f"Actividad '{id_act}': nodo_origen y nodo_destino deben ser números enteros.")
            else:
                origen = int(origen)
                destino = int(destino)

                if origen <= 0 or destino <= 0:
                    errores.append(f"Actividad '{id_act}': nodo_origen y nodo_destino deben ser enteros positivos (>0).")

                if origen == destino:
                    errores.append(f"Actividad '{id_act}': nodo_origen y nodo_destino no pueden ser iguales (ambos son {origen}).")
        except (ValueError, TypeError):
            errores.append(f"Actividad '{id_act}': nodo_origen y nodo_destino deben ser de tipo numérico.")

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
            "id_actividad": ["A", "B", "C"],
            "nodo_origen": [1, 2, 2],
            "nodo_destino": [2, 3, 4],
            "es_ficticia": [False, False, False]
        })

    tab_manual, tab_archivo = st.tabs(["📝 Edición Manual Dinámica", "📁 Carga de Archivos"])

    with tab_manual:
        st.subheader("Tabla de Actividades")
        st.info("Agregue, edite o elimine filas dinámicamente.")
        df_editado = st.data_editor(
            st.session_state.datos_pert,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            column_config={
                "id_actividad": st.column_config.TextColumn("ID Actividad", required=True),
                "nodo_origen": st.column_config.NumberColumn("Nodo Origen", required=True, min_value=1, step=1),
                "nodo_destino": st.column_config.NumberColumn("Nodo Destino", required=True, min_value=1, step=1),
                "es_ficticia": st.column_config.CheckboxColumn("¿Es Ficticia?", default=False),
            }
        )
        st.session_state.datos_pert = df_editado

    with tab_archivo:
        st.subheader("Importar Datos de Red")
        col1, col2 = st.columns([1, 2])
        with col1:
            st.markdown("**Plantilla Base**")
            st.download_button(
                label="📥 Descargar Plantilla (.csv)",
                data=generar_plantilla_csv(),
                file_name="plantilla_actividades_pert.csv",
                mime="text/csv",
                use_container_width=True
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
                        st.success("¡Datos aplicados! Vaya a la pestaña 'Edición Manual Dinámica' para verlos.")
                        st.rerun()
                except Exception as e:
                    st.error(f"Error al procesar el archivo: {str(e)}")

    st.divider()

    # ---------------------------------------------------------
    # Botón de Acción Centralizado
    # ---------------------------------------------------------
    if st.button("🚀 Ejecutar Auditoría Estructural y de IA", type="primary", use_container_width=True):
        df_final = st.session_state.datos_pert.copy()

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
                datos_formateados.append({
                    'id': str(fila['id_actividad']).strip(),
                    'origen': int(fila['nodo_origen']),
                    'destino': int(fila['nodo_destino']),
                    'es_ficticia': bool(fila['es_ficticia'])
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

            # Renderizado visual del grafo usando NetworkX y Matplotlib
            st.subheader("Representación Visual del Grafo")
            fig = None
            try:
                fig, ax = plt.subplots(figsize=(10, 6))
                G = red_pert.grafo
                pos = nx.spring_layout(G, seed=42)

                # Separar arcos normales y ficticios para coloreado diferenciado
                arcos_normales = [(u, v) for u, v, d in G.edges(data=True) if not d.get("es_ficticia", False)]
                arcos_ficticios = [(u, v) for u, v, d in G.edges(data=True) if d.get("es_ficticia", False)]

                # Nodos
                nx.draw_networkx_nodes(G, pos, ax=ax, node_color='#87CEEB', node_size=800, edgecolors='black')
                nx.draw_networkx_labels(G, pos, ax=ax, font_size=11, font_weight="bold")

                # Arcos normales (líneas sólidas grises)
                if arcos_normales:
                    nx.draw_networkx_edges(G, pos, edgelist=arcos_normales, ax=ax, edge_color='#555555',
                                           arrows=True, arrowsize=20, width=1.5)
                # Arcos ficticios (líneas discontinuas rojas - Tij = 0)
                if arcos_ficticios:
                    nx.draw_networkx_edges(G, pos, edgelist=arcos_ficticios, ax=ax, edge_color='red',
                                           style='dashed', arrows=True, arrowsize=20, width=1.5)

                # Etiquetas de arcos normales
                edge_labels_normales = {
                    (u, v): d.get("id_actividad", "")
                    for u, v, d in G.edges(data=True)
                    if not d.get("es_ficticia", False)
                }
                nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels_normales, ax=ax, font_color='black')

                # Etiquetas de arcos ficticios (diferenciados en rojo)
                edge_labels_ficticios = {
                    (u, v): f"Fict ({d.get('id_actividad', '')})"
                    for u, v, d in G.edges(data=True)
                    if d.get("es_ficticia", False)
                }
                if edge_labels_ficticios:
                    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels_ficticios, ax=ax, font_color='red')

                ax.set_axis_off()
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
            with st.spinner("Generando reporte de IA con Ollama... Este proceso puede tardar unos segundos."):
                try:
                    orquestador_ia = AIEngineOrchestrator()
                    reporte_md = orquestador_ia.generar_auditoria_estructural(
                        datos_grafo_json=resultado_validacion
                    )
                    st.markdown(reporte_md)
                except Exception as e:
                    st.error(f"Falla al conectar con Ollama o al procesar la IA: {str(e)}")


if __name__ == "__main__":
    main()
