import streamlit as st
import pandas as pd
from network_model import PERTNetwork

# Configuración principal de la página para un aspecto profesional
st.set_page_config(
    page_title="Validador Estructural PERT/CPM",
    page_icon="🕸️",
    layout="wide"
)

def generar_plantilla_csv():
    """Genera un archivo CSV de plantilla para que el usuario lo descargue."""
    df_plantilla = pd.DataFrame({
        "id_actividad": ["A", "B", "Ficticia_1"],
        "nodo_origen": [1, 2, 3],
        "nodo_destino": [2, 3, 4],
        "tiempo_optimista": [2.0, 3.5, 0.0],
        "tiempo_pesimista": [4.0, 6.0, 0.0],
        "duracion_estimada": [3.0, 4.5, 0.0]
    })
    return df_plantilla.to_csv(index=False).encode('utf-8')

def validar_datos(df: pd.DataFrame) -> list:
    """
    Valida las reglas de negocio en el frontend antes de enviar al motor matemático.
    Retorna una lista de strings con los errores encontrados.
    """
    errores = []
    
    # 1. Comprobar que no existan campos vacíos
    if df.isnull().values.any() or (df == "").any().any():
        errores.append("La tabla contiene campos vacíos. Por favor complete todas las celdas.")
        return errores # Si hay campos vacíos, abortamos la validación temprana para evitar excepciones de tipo
        
    columnas_requeridas = [
        "id_actividad", "nodo_origen", "nodo_destino", 
        "tiempo_optimista", "tiempo_pesimista", "duracion_estimada"
    ]
    
    columnas_faltantes = [col for col in columnas_requeridas if col not in df.columns]
    if columnas_faltantes:
        errores.append(f"Faltan las siguientes columnas requeridas: {', '.join(columnas_faltantes)}")
        return errores

    # Iterar por cada fila para validaciones específicas
    for idx, fila in df.iterrows():
        id_act = str(fila.get("id_actividad", f"Fila {idx+1}")).strip()
        
        # 2. Validar nodo_origen y nodo_destino (Enteros positivos diferentes)
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
        except ValueError:
            errores.append(f"Actividad '{id_act}': nodo_origen y nodo_destino deben ser de tipo numérico.")

        # 3. Validar tiempos y duraciones (Flotantes >= 0)
        try:
            t_opt = float(fila["tiempo_optimista"])
            t_pes = float(fila["tiempo_pesimista"])
            duracion = float(fila["duracion_estimada"])
            
            if t_opt < 0 or t_pes < 0 or duracion < 0:
                errores.append(f"Actividad '{id_act}': tiempo_optimista, tiempo_pesimista y duracion_estimada no pueden ser negativos.")
        except ValueError:
            errores.append(f"Actividad '{id_act}': Los tiempos y duración deben ser valores numéricos flotantes.")

    return errores

def main():
    st.title("⚙️ Motor de Validación Estructural de Redes PERT/CPM")
    st.markdown("""
    **Interfaz Base de Carga de Datos - Hito 1**  
    Construya la topología de la red definiendo las actividades y sus relaciones a través de nodos origen y destino.
    Puede usar la edición manual en pantalla o cargar un archivo con los datos.
    """)

    # Inicializar el estado de sesión para mantener los datos de la tabla si el usuario interactúa con otras pestañas
    if 'datos_pert' not in st.session_state:
        st.session_state.datos_pert = pd.DataFrame({
            "id_actividad": ["A", "B", "C"],
            "nodo_origen": [1, 2, 2],
            "nodo_destino": [2, 3, 4],
            "tiempo_optimista": [1.0, 2.0, 1.5],
            "tiempo_pesimista": [3.0, 4.0, 2.5],
            "duracion_estimada": [2.0, 3.0, 2.0]
        })

    # Doble método de entrada mediante pestañas (Tabs)
    tab_manual, tab_archivo = st.tabs(["📝 Edición Manual Dinámica (Método B)", "📁 Carga de Archivos (Método A)"])

    # Método B: Edición Manual Dinámica
    with tab_manual:
        st.subheader("Tabla de Actividades")
        st.info("Agregue (haciendo clic en la fila inferior), edite o elimine filas dinámicamente.")
        
        df_editado = st.data_editor(
            st.session_state.datos_pert,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            column_config={
                "id_actividad": st.column_config.TextColumn("ID Actividad", required=True),
                "nodo_origen": st.column_config.NumberColumn("Nodo Origen", required=True, min_value=1, step=1),
                "nodo_destino": st.column_config.NumberColumn("Nodo Destino", required=True, min_value=1, step=1),
                "tiempo_optimista": st.column_config.NumberColumn("T. Optimista ($a$)", required=True, min_value=0.0),
                "tiempo_pesimista": st.column_config.NumberColumn("T. Pesimista ($b$)", required=True, min_value=0.0),
                "duracion_estimada": st.column_config.NumberColumn("Duración ($T_{ij}$)", required=True, min_value=0.0),
            }
        )
        st.session_state.datos_pert = df_editado

    # Método A: Carga de Archivos
    with tab_archivo:
        st.subheader("Importar Datos de Red")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown("**Plantilla Base**")
            st.markdown("Si no tienes el archivo estructurado, puedes descargar la plantilla oficial:")
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
                        st.success("¡Datos aplicados! Vaya a la pestaña 'Edición Manual Dinámica' para visualizarlos.")
                        st.rerun()
                except Exception as e:
                    st.error(f"Error al procesar el archivo: {str(e)}")

    st.divider()

    # Procesamiento e integración con el Backend
    if st.button("🚀 Procesar y Cargar Estructura", type="primary", use_container_width=True):
        df_final = st.session_state.datos_pert.copy()
        
        # Validar en frontend antes de mandar a backend
        errores = validar_datos(df_final)
        
        if errores:
            st.error("🚨 Se encontraron errores en los datos que impiden construir la red:")
            for error in errores:
                st.warning(f"• {error}")
        else:
            try:
                # Transformar DataFrame a la lista de diccionarios requerida por PERTNetwork
                datos_formateados = []
                for _, fila in df_final.iterrows():
                    datos_formateados.append({
                        'id': str(fila['id_actividad']).strip(),
                        'origen': int(fila['nodo_origen']),
                        'destino': int(fila['nodo_destino']),
                        'tiempo_a': float(fila['tiempo_optimista']),
                        'tiempo_b': float(fila['tiempo_pesimista']),
                        'duracion': float(fila['duracion_estimada'])
                    })

                # Instanciar y cargar en el modelo del Integrante 2
                red_pert = PERTNetwork()
                red_pert.cargar_desde_lista(datos_formateados)
                
                st.success("✅ La estructura de la red fue validada y cargada exitosamente en el motor matemático.")
                
                # Renderizar JSON resultante como confirmación visual
                st.markdown("### 📊 Representación JSON de la Topología")
                st.json(red_pert.obtener_estructura_json())
                
            except ValueError as ve:
                st.error(f"❌ Error de Validación del Modelo (Backend): {str(ve)}")
            except TypeError as te:
                st.error(f"❌ Error de Tipo de Datos (Backend): {str(te)}")
            except Exception as e:
                st.error(f"❌ Ocurrió un error inesperado al procesar la red: {str(e)}")

if __name__ == "__main__":
    main()
