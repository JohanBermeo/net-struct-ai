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
    errors = []
    for node in graph.nodes():
        in_flow = sum(
            graph.edges[u, v].get("weight", 1)
            for u, v in graph.in_edges(node)
        )
        out_flow = sum(
            graph.edges[u, v].get("weight", 1)
            for u, v in graph.out_edges(node)
        )
        if in_flow == 0 or out_flow == 0:
            continue
        if abs(in_flow - out_flow) > 1e-9:
            errors.append(
                f"Flow mismatch at node '{node}': in={in_flow}, out={out_flow}"
            )
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
