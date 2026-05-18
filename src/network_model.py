import networkx as nx
from typing import List, Dict, Any

class PERTNetwork:
    """
    Motor de Validación Estructural de Redes PERT/CPM.
    Capa de Abstracción del Grafo y Estructuras de Datos.
    
    Esta clase modela una red PERT/CPM como un Grafo Dirigido Acíclico (DAG),
    preparando la estructura de datos para validaciones topológicas, análisis 
    de conectividad y cálculo probabilístico en hitos posteriores.
    """

    def __init__(self):
        """
        Inicializa un nuevo objeto PERTNetwork.
        Instancia internamente un grafo dirigido de NetworkX (nx.DiGraph),
        asegurando el flujo temporal unidireccional y las propiedades necesarias
        para modelar hitos (nodos) y actividades (arcos).
        """
        self.grafo: nx.DiGraph = nx.DiGraph()

    def cargar_desde_lista(self, actividades: List[Dict[str, Any]]) -> None:
        """
        Recibe una lista de diccionarios con la estructura de las actividades y
        puebla el grafo con nodos (eventos) y arcos (actividades).

        Estructura esperada de un diccionario en la lista:
        {
            'id': str,           # ID de la actividad (ej. 'A', 'Dummy1')
            'origen': int,       # ID numérico del nodo origen (evento inicio)
            'destino': int,      # ID numérico del nodo destino (evento fin)
            'tiempo_a': float,   # Tiempo optimista
            'tiempo_b': float,   # Tiempo pesimista
            'duracion': float    # Duración estimada o base
        }
        
        Args:
            actividades (List[Dict[str, Any]]): Lista de definiciones de actividades.
            
        Raises:
            TypeError: Si el tipo de datos proporcionado no es el esperado.
            ValueError: Si faltan claves obligatorias o los valores son malformados.
        """
        if not isinstance(actividades, list):
            raise TypeError("El argumento 'actividades' debe ser una lista de diccionarios.")

        # Atributos obligatorios para cada actividad según el requerimiento
        claves_requeridas = {'id', 'origen', 'destino', 'tiempo_a', 'tiempo_b', 'duracion'}

        for indice, act in enumerate(actividades):
            if not isinstance(act, dict):
                raise TypeError(f"El elemento en el índice {indice} no es un diccionario válido.")

            claves_faltantes = claves_requeridas - set(act.keys())
            if claves_faltantes:
                raise ValueError(
                    f"Faltan las siguientes propiedades obligatorias en la actividad {indice}: "
                    f"{claves_faltantes}"
                )

            try:
                # Los nodos representan eventos secuenciales de tiempo (IDs numéricos)
                nodo_origen = int(act['origen'])
                nodo_destino = int(act['destino'])
                
                # Conversión de parámetros de tiempo
                tiempo_a = float(act['tiempo_a'])
                tiempo_b = float(act['tiempo_b'])
                duracion = float(act['duracion'])
                
                # Soporte para Tareas Ficticias:
                # Se considera que un arco es tarea ficticia si su duración estipulada es 0.
                # Sirven para mantener relaciones de precedencia lógicas complejas sin
                # consumir tiempo real. Se fuerzan todos los tiempos a 0 para consistencia.
                es_ficticia = (duracion == 0.0)

                if es_ficticia:
                    tiempo_a = 0.0
                    tiempo_b = 0.0
                    duracion = 0.0

            except (ValueError, TypeError) as error_conversion:
                raise ValueError(
                    f"Error de formato o tipo de dato en la actividad '{act.get('id', 'Desconocido')}' "
                    f"(Índice {indice}): {error_conversion}"
                )

            # Agrega los nodos al grafo. En NetworkX, los nodos que ya existen son omitidos.
            self.grafo.add_node(nodo_origen)
            self.grafo.add_node(nodo_destino)

            # Agrega la arista (actividad) que conecta ambos nodos
            # Almacenando como metadata los atributos obligatorios solicitados
            self.grafo.add_edge(
                nodo_origen, 
                nodo_destino, 
                id_actividad=str(act['id']),
                duracion_estimada=duracion,
                tiempo_a=tiempo_a,
                tiempo_b=tiempo_b,
                es_ficticia=es_ficticia
            )

    def obtener_estructura_json(self) -> Dict[str, Any]:
        """
        Exporta la topología completa del grafo (nodos y arcos con todos sus 
        atributos internos) en un formato nativo de Python (dict), fácilmente 
        serializable a JSON para los módulos de IA (Ollama) y frontend (Streamlit).

        Returns:
            Dict[str, Any]: Diccionario que contiene las listas de "nodos" y "arcos".
        """
        estructura_exportada = {
            "nodos": list(self.grafo.nodes()),
            "arcos": []
        }

        for origen, destino, datos in self.grafo.edges(data=True):
            arco = {
                "origen": origen,
                "destino": destino,
                "atributos": datos
            }
            estructura_exportada["arcos"].append(arco)

        return estructura_exportada
