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
        Recibe una lista de diccionarios con la estructura AON (Actividad y predecesores)
        y construye dinámicamente un grafo AOA (Actividad en el Arco).

        Estructura esperada de un diccionario en la lista:
        {
            'id': str,                  # ID de la actividad (ej. 'A')
            'predecessors': List[str]   # Lista de IDs de actividades predecesoras
        }
        """
        if not isinstance(actividades, list):
            raise TypeError("El argumento 'actividades' debe ser una lista de diccionarios.")

        # Reiniciar el grafo interno
        self.grafo = nx.DiGraph()

        # 1. Parsear y limpiar actividades y sus predecesores
        act_map = {}
        for idx, act in enumerate(actividades):
            if not isinstance(act, dict):
                raise TypeError(f"El elemento en el índice {idx} no es un diccionario válido.")
            if 'id' not in act:
                raise ValueError(f"Falta la propiedad obligatoria 'id' en la actividad {idx}.")
            
            act_id = str(act['id']).strip()
            if not act_id:
                raise ValueError(f"El ID de la actividad en el índice {idx} no puede estar vacío.")

            preds = act.get('predecessors', [])
            if not isinstance(preds, list):
                raise TypeError(f"Los predecesores de '{act_id}' deben ser una lista de strings.")
            
            cleaned_preds = [p.strip() for p in preds if p.strip()]
            act_map[act_id] = cleaned_preds

        # 2. Encontrar todos los conjuntos únicos de predecesores
        # Convertir a frozenset para usar como claves
        pred_sets = set()
        for preds in act_map.values():
            pred_sets.add(frozenset(preds))
        
        # El conjunto vacío representa el inicio (nodo 1)
        pred_sets.add(frozenset())

        # Ordenar los conjuntos de predecesores (para asignar números de nodos secuenciales consistentes)
        sorted_pred_sets = sorted(list(pred_sets), key=len)
        node_map = {}
        
        # Asignar IDs numéricos temporales a los eventos
        node_map[frozenset()] = 1
        self._next_node_id = 2
        for pset in sorted_pred_sets:
            if pset != frozenset():
                node_map[pset] = self._next_node_id
                self._next_node_id += 1

        # Crear un nodo sumidero final único
        sink_node = self._next_node_id
        self._next_node_id += 1

        # Añadir todos los nodos iniciales al grafo
        for nid in node_map.values():
            self.grafo.add_node(nid)
        self.grafo.add_node(sink_node)

        # 3. Construir los arcos reales y generar nodos/arcos ficticios
        fict_count = 0

        # Para cada actividad real
        for act_id, preds in act_map.items():
            start_node = node_map[frozenset(preds)]

            # Buscar qué conjuntos de predecesores contienen a esta actividad
            containing_sets = [pset for pset in pred_sets if act_id in pset]

            if not containing_sets:
                # Caso A: Ninguna otra actividad depende de esta. Va directo al sumidero final.
                end_node = sink_node
                self._add_edge_safely(start_node, end_node, act_id, es_ficticia=False, weight=1)
            elif len(containing_sets) == 1:
                # Caso B: Solo un conjunto de predecesores contiene a esta actividad.
                # Su nodo de finalización es el nodo de ese conjunto.
                end_node = node_map[containing_sets[0]]
                self._add_edge_safely(start_node, end_node, act_id, es_ficticia=False, weight=1)
            else:
                # Caso C: Múltiples conjuntos de predecesores contienen a esta actividad.
                # Creamos un nodo intermedio exclusivo para finalizar esta actividad.
                end_node = self._next_node_id
                self._next_node_id += 1
                self.grafo.add_node(end_node)

                # Agregar la actividad real del nodo inicio al nodo intermedio de fin
                self._add_edge_safely(start_node, end_node, act_id, es_ficticia=False, weight=1)

                # Agregar arcos ficticios desde el nodo intermedio hacia los nodos de los conjuntos correspondientes
                for pset in containing_sets:
                    target_node = node_map[pset]
                    fict_count += 1
                    fict_id = f"F_{act_id}_{fict_count}"
                    # Las actividades ficticias tienen peso 0 (duración 0) y es_ficticia = True
                    self._add_edge_safely(end_node, target_node, fict_id, es_ficticia=True, weight=0)

        # Simplificar el grafo eliminando nodos y arcos ficticios redundantes
        self._simplificar_grafo(start_node=1, sink_node=sink_node)

        # 4. Numerar los nodos secuencialmente utilizando ordenamiento topológico (si es un DAG)
        try:
            # Ordenamiento topológico
            topo_order = list(nx.topological_sort(self.grafo))
            # Mapeo a números secuenciales 1, 2, ..., N
            mapping = {old_node: new_index for new_index, old_node in enumerate(topo_order, start=1)}
            self.grafo = nx.relabel_nodes(self.grafo, mapping, copy=True)
        except nx.NetworkXUnfeasible:
            # Si hay ciclos, el ordenamiento topológico fallará.
            # Mantenemos los nodos tal como están para que el validador de ciclos los detecte e informe.
            pass

    def _simplificar_grafo(self, start_node: int, sink_node: int) -> None:
        """
        Simplifica la topología del grafo AOA eliminando nodos y arcos ficticios redundantes,
        preservando exactamente las mismas relaciones de dependencia y protegiendo
        los nodos fuente (inicio) y sumidero (fin).
        """
        G = self.grafo
        modificado = True
        while modificado:
            modificado = False
            
            # Regla 1: Si un nodo v tiene exactamente 1 arco entrante, y este es ficticio u -> v (con u != v),
            # podemos fusionar v en u si no genera colisiones de arcos paralelos y v no es el nodo sumidero/fuente.
            nodos = list(G.nodes())
            for v in nodos:
                if not G.has_node(v):
                    continue
                if v == start_node or v == sink_node:
                    continue
                in_edges = list(G.in_edges(v, data=True))
                if len(in_edges) == 1:
                    u, _, data = in_edges[0]
                    if data.get("es_ficticia", False) and u != v:
                        out_edges = list(G.out_edges(v, data=True))
                        # Verificar colisiones de arcos paralelos
                        colision = False
                        for _, dest, _ in out_edges:
                            if G.has_edge(u, dest):
                                colision = True
                                break
                        
                        if not colision:
                            # Fusionar v en u
                            for _, dest, edata in out_edges:
                                G.add_edge(u, dest, **edata)
                            G.remove_node(v)
                            modificado = True
                            break
                            
            if modificado:
                continue
                
            # Regla 2: Si un nodo u tiene exactamente 1 arco saliente, y este es ficticio u -> v (con u != v),
            # podemos fusionar u en v si no genera colisiones y u no es el nodo sumidero/fuente.
            for u in nodos:
                if not G.has_node(u):
                    continue
                if u == start_node or u == sink_node:
                    continue
                out_edges = list(G.out_edges(u, data=True))
                if len(out_edges) == 1:
                    _, v, data = out_edges[0]
                    if data.get("es_ficticia", False) and u != v:
                        in_edges = list(G.in_edges(u, data=True))
                        colision = False
                        for src, _, _ in in_edges:
                            if G.has_edge(src, v):
                                colision = True
                                break
                                
                        if not colision:
                            # Fusionar u en v
                            for src, _, edata in in_edges:
                                G.add_edge(src, v, **edata)
                            G.remove_node(u)
                            modificado = True
                            break

    def _add_edge_safely(self, u: int, v: int, act_id: str, es_ficticia: bool, weight: int) -> None:
        """
        Agrega una arista al grafo de manera segura. Si ya existe una arista entre u y v,
        resuelve la colisión paralela creando un nodo ficticio intermedio para evitar la duplicidad.
        """
        if not self.grafo.has_edge(u, v):
            self.grafo.add_edge(
                u,
                v,
                id_actividad=act_id,
                es_ficticia=es_ficticia,
                weight=weight
            )
        else:
            # Resolver colisión paralela:
            # Crear un nodo ficticio intermedio para esta nueva arista paralela
            # Encontrar un ID de nodo libre
            temp_node = self._next_node_id
            self._next_node_id += 1
            self.grafo.add_node(temp_node)
            
            # La actividad real (o ficticia) va del origen u al nodo temporal
            self.grafo.add_edge(
                u,
                temp_node,
                id_actividad=act_id,
                es_ficticia=es_ficticia,
                weight=weight
            )
            # Y se agrega un arco ficticio del nodo temporal al destino v
            fict_id = f"F_par_{act_id}"
            self.grafo.add_edge(
                temp_node,
                v,
                id_actividad=fict_id,
                es_ficticia=True,
                weight=0
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
