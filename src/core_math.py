import networkx as nx
from collections import deque
from typing import List, Tuple, Dict, Any


def build_graph(activities: List[str], edges: List[Tuple[str, str]]) -> nx.DiGraph:
    g = nx.DiGraph()
    for act in activities:
        g.add_node(act)
    for u, v in edges:
        if g.has_edge(u, v):
            g.add_edge(u, v, weight=1, parallel=True)
        else:
            g.add_edge(u, v, weight=1)
    return g


def validate_dag(graph: nx.DiGraph) -> Dict[str, Any]:
    try:
        cycle_edges = []
        cycle_nodes = []
        visited = set()
        rec_stack = set()
        parent = {}

        def dfs(node):
            visited.add(node)
            rec_stack.add(node)
            for neighbor in graph.successors(node):
                if neighbor not in visited:
                    parent[neighbor] = node
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    cycle_nodes.append(neighbor)
                    curr = node
                    while curr != neighbor:
                        cycle_nodes.append(curr)
                        curr = parent.get(curr)
                        if curr is None:
                            break
                    cycle_nodes.append(neighbor)
                    cycle_nodes.reverse()
                    for i in range(len(cycle_nodes) - 1):
                        cycle_edges.append((cycle_nodes[i], cycle_nodes[i + 1]))
                    return True
            rec_stack.discard(node)
            return False

        for node in graph.nodes():
            if node not in visited:
                if dfs(node):
                    return {
                        "is_dag": False,
                        "cycle_edges": list(dict.fromkeys(cycle_edges)),
                        "cycle_nodes": list(dict.fromkeys(cycle_nodes)),
                    }

        return {"is_dag": True, "cycle_edges": [], "cycle_nodes": []}
    except Exception:
        return {"is_dag": False, "cycle_edges": [], "cycle_nodes": []}


def find_all_cycles(graph: nx.DiGraph) -> List[List[str]]:
    cycles = []
    try:
        while True:
            result = validate_dag(graph)
            if result["is_dag"]:
                break
            cycle = result["cycle_nodes"]
            if cycle:
                cycles.append(cycle)
                for i in range(len(cycle) - 1):
                    u, v = cycle[i], cycle[i + 1]
                    if graph.has_edge(u, v):
                        graph.remove_edge(u, v)
    except Exception:
        pass
    return cycles


def find_source_nodes(graph: nx.DiGraph) -> List[str]:
    return [n for n in graph.nodes() if graph.in_degree(n) == 0]


def find_sink_nodes(graph: nx.DiGraph) -> List[str]:
    return [n for n in graph.nodes() if graph.out_degree(n) == 0]


def ensure_unique_source(graph: nx.DiGraph) -> Tuple[nx.DiGraph, List[str]]:
    sources = find_source_nodes(graph)
    added = []
    if len(sources) > 1:
        virtual = "__VIRTUAL_SOURCE__"
        graph.add_node(virtual, is_virtual=True)
        for s in sources:
            graph.add_edge(virtual, s)
        added.append(virtual)
    return graph, added


def ensure_unique_sink(graph: nx.DiGraph) -> Tuple[nx.DiGraph, List[str]]:
    sinks = find_sink_nodes(graph)
    added = []
    if len(sinks) > 1:
        virtual = "__VIRTUAL_SINK__"
        graph.add_node(virtual, is_virtual=True)
        for s in sinks:
            graph.add_edge(s, virtual)
        added.append(virtual)
    return graph, added


def find_orphan_nodes(graph: nx.DiGraph) -> List[str]:
    return [
        n
        for n in graph.nodes()
        if graph.in_degree(n) == 0 and graph.out_degree(n) == 0
    ]


def validate_flow_conservation(graph: nx.DiGraph) -> List[str]:
    """
    Valida la continuidad del flujo en la red PERT/CPM (AOA).
    Todo nodo (evento) en el grafo debe estar en un camino desde el nodo de inicio único (fuente)
    hasta el nodo de fin único (sumidero). Si un nodo no es alcanzable desde la fuente, o no puede
    alcanzar el sumidero, se reporta como un error de flujo.
    """
    errors = []
    if len(graph.nodes) == 0:
        return errors

    sources = [n for n in graph.nodes() if graph.in_degree(n) == 0]
    sinks = [n for n in graph.nodes() if graph.out_degree(n) == 0]

    # Si hay múltiples fuentes o sumideros, la unicidad ya reportará esto,
    # pero aún podemos validar el alcance para cada una de las fuentes/sumideros.
    # Si el grafo no tiene fuentes o sumideros (por ejemplo, es un ciclo puro), salimos.
    if not sources or not sinks:
        return errors

    # Usar BFS para encontrar todos los nodos alcanzables desde cualquier fuente
    reachable_from_source = set()
    for s in sources:
        reachable_from_source.add(s)
        visited = set()
        queue = deque([s])
        while queue:
            curr = queue.popleft()
            for neighbor in graph.successors(curr):
                if neighbor not in visited:
                    visited.add(neighbor)
                    reachable_from_source.add(neighbor)
                    queue.append(neighbor)

    # Usar BFS en el grafo invertido para encontrar todos los nodos que pueden alcanzar algún sumidero
    can_reach_sink = set()
    for t in sinks:
        can_reach_sink.add(t)
        visited = set()
        queue = deque([t])
        while queue:
            curr = queue.popleft()
            for neighbor in graph.predecessors(curr):
                if neighbor not in visited:
                    visited.add(neighbor)
                    can_reach_sink.add(neighbor)
                    queue.append(neighbor)

    for node in graph.nodes():
        if node not in reachable_from_source:
            errors.append(f"El nodo '{node}' no es alcanzable desde el nodo inicial del proyecto.")
        if node not in can_reach_sink:
            errors.append(f"El nodo '{node}' no puede alcanzar el nodo final (callejón sin salida).")

    return errors


def resolve_fictitious_activities(graph: nx.DiGraph) -> nx.DiGraph:
    g = graph.copy()
    fid = 0

    for u, v in list(g.edges()):
        edge_data = g.edges[u, v]
        current_weight = edge_data.get("weight", 1)
        if current_weight == 0:
            continue
        is_parallel = edge_data.get("parallel", False)
        if is_parallel:
            fid += 1
            fict_node = f"__FICT_{fid}__"
            g.add_node(fict_node, is_virtual=True)
            g.add_edge(u, fict_node, weight=0)
            g.add_edge(fict_node, v, weight=0)

    return g


def topological_sort(graph: nx.DiGraph) -> List[str]:
    try:
        return list(nx.topological_sort(graph))
    except (nx.NetworkXUnfeasible, Exception):
        in_degree = {n: 0 for n in graph.nodes()}
        for u, v in graph.edges():
            in_degree[v] = in_degree.get(v, 0) + 1

        queue = deque([n for n, d in in_degree.items() if d == 0])
        result = []

        while queue:
            node = queue.popleft()
            result.append(node)
            for neighbor in graph.successors(node):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return result


def serialize_network(
    graph: nx.DiGraph, metadata: Dict[str, Any]
) -> Dict[str, Any]:
    result = dict(metadata) if metadata else {}
    result["activities"] = sorted(graph.nodes())
    result["edges"] = [
        {"from": u, "to": v} for u, v in graph.edges()
    ]
    sources = find_source_nodes(graph)
    sinks = find_sink_nodes(graph)
    if sources:
        result["source"] = sources[0]
    if sinks:
        result["sink"] = sinks[0]
    return result
