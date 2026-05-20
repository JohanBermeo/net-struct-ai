import pytest
import networkx as nx
from src.core_math import (
    build_graph,
    validate_dag,
    find_all_cycles,
    find_source_nodes,
    find_sink_nodes,
    ensure_unique_source,
    ensure_unique_sink,
    find_orphan_nodes,
    validate_flow_conservation,
    resolve_fictitious_activities,
    topological_sort,
    serialize_network,
)
from src.network_model import PERTNetwork

# ---------------------------------------------------------------------------
# Phase 1 — T2.1: Cycle Detection
# ---------------------------------------------------------------------------

class TestBuildGraph:
    def test_build_simple_acyclic(self):
        g = build_graph(["A", "B", "C"], [("A", "B"), ("B", "C")])
        assert set(g.nodes) == {"A", "B", "C"}
        assert set(g.edges) == {("A", "B"), ("B", "C")}

    def test_build_empty(self):
        g = build_graph([], [])
        assert len(g.nodes) == 0
        assert len(g.edges) == 0

    def test_build_duplicate_edge(self):
        g = build_graph(["A", "B"], [("A", "B"), ("A", "B")])
        assert len(g.edges) == 1


class TestValidateDag:
    def test_acyclic_graph_returns_true(self):
        g = build_graph(["A", "B", "C"], [("A", "B"), ("B", "C")])
        result = validate_dag(g)
        assert result["is_dag"] is True
        assert result["cycle_edges"] == []

    def test_direct_cycle_detected(self):
        g = build_graph(["A", "B"], [("A", "B"), ("B", "A")])
        result = validate_dag(g)
        assert result["is_dag"] is False
        assert len(result["cycle_edges"]) > 0

    def test_indirect_cycle_detected(self):
        g = build_graph(["A", "B", "C"], [("A", "B"), ("B", "C"), ("C", "A")])
        result = validate_dag(g)
        assert result["is_dag"] is False
        assert len(result["cycle_nodes"]) == 3

    def test_self_loop_detected(self):
        g = build_graph(["A"], [("A", "A")])
        result = validate_dag(g)
        assert result["is_dag"] is False

    def test_empty_graph_is_acyclic(self):
        g = build_graph([], [])
        result = validate_dag(g)
        assert result["is_dag"] is True


class TestFindAllCycles:
    def test_no_cycles_empty_list(self):
        g = build_graph(["A", "B"], [("A", "B")])
        assert find_all_cycles(g) == []

    def test_single_direct_cycle(self):
        g = build_graph(["A", "B"], [("A", "B"), ("B", "A")])
        cycles = find_all_cycles(g)
        assert len(cycles) >= 1

    def test_multiple_cycles(self):
        g = build_graph(
            ["A", "B", "C", "D"],
            [("A", "B"), ("B", "A"), ("C", "D"), ("D", "C")]
        )
        cycles = find_all_cycles(g)
        assert len(cycles) >= 2


# ---------------------------------------------------------------------------
# Phase 2 — T2.2: Source/Sink Uniqueness
# ---------------------------------------------------------------------------

class TestSourceSink:
    def test_single_source_and_sink(self):
        g = build_graph(["A", "B", "C"], [("A", "B"), ("B", "C")])
        assert find_source_nodes(g) == ["A"]
        assert find_sink_nodes(g) == ["C"]

    def test_multiple_sources(self):
        g = build_graph(["A", "B", "C"], [("A", "C"), ("B", "C")])
        sources = find_source_nodes(g)
        assert sorted(sources) == ["A", "B"]

    def test_multiple_sinks(self):
        g = build_graph(["A", "B", "C"], [("A", "B"), ("A", "C")])
        sinks = find_sink_nodes(g)
        assert sorted(sinks) == ["B", "C"]

    def test_ensure_unique_source_inserts_virtual(self):
        g = build_graph(["A", "B", "C"], [("A", "C"), ("B", "C")])
        new_g, added = ensure_unique_source(g)
        assert len(added) > 0
        sources = find_source_nodes(new_g)
        assert len(sources) == 1

    def test_ensure_unique_sink_inserts_virtual(self):
        g = build_graph(["A", "B", "C"], [("A", "B"), ("A", "C")])
        new_g, added = ensure_unique_sink(g)
        assert len(added) > 0
        sinks = find_sink_nodes(new_g)
        assert len(sinks) == 1


class TestOrphanNodes:
    def test_no_orphans(self):
        g = build_graph(["A", "B"], [("A", "B")])
        assert find_orphan_nodes(g) == []

    def test_orphan_detected(self):
        g = build_graph(["A", "B", "C"], [("A", "B")])
        orphans = find_orphan_nodes(g)
        assert "C" in orphans

    def test_all_orphans(self):
        g = build_graph(["A", "B", "C"], [])
        assert len(find_orphan_nodes(g)) == 3


# ---------------------------------------------------------------------------
# Phase 3 — T2.3: Flow Conservation & Fictitious Activities
# ---------------------------------------------------------------------------

class TestFlowConservation:
    def test_balanced_flow_passes(self):
        g = build_graph(
            ["A", "B", "C", "D"],
            [("A", "B"), ("B", "C"), ("C", "D")]
        )
        for _, _, d in g.edges(data=True):
            d["weight"] = 1
        errors = validate_flow_conservation(g)
        assert errors == []

    def test_unreachable_node_reported(self):
        # A -> B -> C y un ciclo desconectado D -> E -> D
        g = nx.DiGraph()
        g.add_nodes_from(["A", "B", "C", "D", "E"])
        g.add_edges_from([("A", "B"), ("B", "C"), ("D", "E"), ("E", "D")])
        errors = validate_flow_conservation(g)
        assert len(errors) > 0

    def test_fictitious_activity_handled(self):
        g = build_graph(
            ["A", "B", "C", "D", "F1"],
            [("A", "B"), ("A", "C"), ("B", "D"), ("C", "D"), ("F1", "D")]
        )
        for u, v, d in g.edges(data=True):
            d["weight"] = 0 if "F1" in str(u) + str(v) else 1
        errors = validate_flow_conservation(g)
        assert errors == []


class TestResolveFictitious:
    def test_parallel_edges_resolved(self):
        g = build_graph(["A", "B", "C"], [("A", "B"), ("A", "B"), ("B", "C")])
        g.edges[("A", "B")]["parallel"] = True
        new_g = resolve_fictitious_activities(g)
        assert len(new_g.edges) >= len(g.edges)

    def test_fictitious_inserted_between_parallel_paths(self):
        g = build_graph(
            ["A", "B", "C", "D"],
            [("A", "B"), ("A", "C"), ("B", "D"), ("C", "D")]
        )
        new_g = resolve_fictitious_activities(g)
        assert len(new_g.nodes) >= len(g.nodes)


class TestTopologicalSort:
    def test_valid_order(self):
        g = build_graph(["A", "B", "C"], [("A", "B"), ("B", "C")])
        order = topological_sort(g)
        assert order == ["A", "B", "C"]

    def test_empty_graph(self):
        g = build_graph([], [])
        assert topological_sort(g) == []

    def test_single_node(self):
        g = build_graph(["A"], [])
        assert topological_sort(g) == ["A"]


class TestSerializeNetwork:
    def test_basic_serialization(self):
        g = build_graph(["A", "B"], [("A", "B")])
        result = serialize_network(g, {"project": "test"})
        assert "activities" in result
        assert "edges" in result
        assert result["project"] == "test"

    def test_serialized_edges_format(self):
        g = build_graph(["A", "B"], [("A", "B")])
        result = serialize_network(g, {})
        assert {"from": "A", "to": "B"} in result["edges"]

    def test_serialized_activities_list(self):
        g = build_graph(["A", "B", "C"], [("A", "B")])
        result = serialize_network(g, {})
        assert set(result["activities"]) == {"A", "B", "C"}


class TestAONtoAOA:
    def test_simple_sequence(self):
        # A -> B -> C
        activities = [
            {"id": "A", "predecessors": []},
            {"id": "B", "predecessors": ["A"]},
            {"id": "C", "predecessors": ["B"]}
        ]
        net = PERTNetwork()
        net.cargar_desde_lista(activities)
        g = net.grafo
        
        # Debe tener 4 nodos secuenciales en una ruta lineal
        assert len(g.nodes) == 4
        # Las aristas deben corresponder a A, B, C y no debe haber ficticias
        edges_data = list(g.edges(data=True))
        assert len(edges_data) == 3
        
        actividades_reales = [d["id_actividad"] for u, v, d in edges_data if not d["es_ficticia"]]
        assert sorted(actividades_reales) == ["A", "B", "C"]
        
        ficticias = [d["id_actividad"] for u, v, d in edges_data if d["es_ficticia"]]
        assert len(ficticias) == 0

    def test_parallel_split(self):
        # A es predecesora de B y C (bifurcación)
        activities = [
            {"id": "A", "predecessors": []},
            {"id": "B", "predecessors": ["A"]},
            {"id": "C", "predecessors": ["A"]}
        ]
        net = PERTNetwork()
        net.cargar_desde_lista(activities)
        g = net.grafo
        
        # Al bifurcarse B y C desde A, ambos terminan en el sink.
        # Por lo tanto, son aristas paralelas. La resolución paralela debe activarse
        # para que una de ellas vaya a través de un nodo y arco ficticio.
        edges_data = list(g.edges(data=True))
        ficticias = [d["id_actividad"] for u, v, d in edges_data if d["es_ficticia"]]
        assert len(ficticias) >= 1
        
        reales = [d["id_actividad"] for u, v, d in edges_data if not d["es_ficticia"]]
        assert sorted(reales) == ["A", "B", "C"]

    def test_parallel_merge(self):
        # A y B son predecesoras de C (unión)
        activities = [
            {"id": "A", "predecessors": []},
            {"id": "B", "predecessors": []},
            {"id": "C", "predecessors": ["A", "B"]}
        ]
        net = PERTNetwork()
        net.cargar_desde_lista(activities)
        g = net.grafo
        
        # A y B inician en el nodo 1 y terminan en el mismo nodo inicio de C.
        # Por tanto, son paralelas. La resolución paralela debe activarse.
        edges_data = list(g.edges(data=True))
        ficticias = [d["id_actividad"] for u, v, d in edges_data if d["es_ficticia"]]
        assert len(ficticias) >= 1
        
        reales = [d["id_actividad"] for u, v, d in edges_data if not d["es_ficticia"]]
        assert sorted(reales) == ["A", "B", "C"]

    def test_complex_fictitious_insertion(self):
        # A y B iniciales; C depende de A; D depende de A y B
        # Esto requiere que el final de A se divida (hacia C directamente, y hacia D junto con B)
        activities = [
            {"id": "A", "predecessors": []},
            {"id": "B", "predecessors": []},
            {"id": "C", "predecessors": ["A"]},
            {"id": "D", "predecessors": ["A", "B"]}
        ]
        net = PERTNetwork()
        net.cargar_desde_lista(activities)
        g = net.grafo
        
        # Debería haber actividades ficticias debido a que A está en múltiples conjuntos de precedencias
        edges_data = list(g.edges(data=True))
        ficticias = [d["id_actividad"] for u, v, d in edges_data if d["es_ficticia"]]
        assert len(ficticias) >= 1
        
        reales = [d["id_actividad"] for u, v, d in edges_data if not d["es_ficticia"]]
        assert sorted(reales) == ["A", "B", "C", "D"]

    def test_user_complex_network(self):
        # El conjunto de datos real provisto por el usuario
        activities = [
            {"id": "A", "predecessors": []},
            {"id": "B", "predecessors": ["A"]},
            {"id": "C", "predecessors": ["A"]},
            {"id": "D", "predecessors": ["A"]},
            {"id": "E", "predecessors": ["A"]},
            {"id": "F", "predecessors": ["A"]},
            {"id": "G", "predecessors": ["A"]},
            {"id": "H", "predecessors": ["B"]},
            {"id": "I", "predecessors": ["G"]},
            {"id": "J", "predecessors": ["C", "D", "E", "F"]},
            {"id": "K", "predecessors": ["C", "D", "E", "F"]},
            {"id": "L", "predecessors": ["C", "D", "E", "F"]},
            {"id": "M", "predecessors": ["C", "D", "E", "F"]},
            {"id": "N", "predecessors": ["C", "D", "E", "F"]},
            {"id": "O", "predecessors": ["C", "D", "E", "F"]},
            {"id": "P", "predecessors": ["M", "L"]},
            {"id": "R", "predecessors": ["M"]},
            {"id": "S", "predecessors": ["N"]},
            {"id": "T", "predecessors": ["O", "N"]},
            {"id": "U", "predecessors": ["K", "I"]},
            {"id": "V", "predecessors": ["H", "J"]},
            {"id": "W", "predecessors": ["V", "P", "R", "S", "T", "U"]},
            {"id": "X", "predecessors": ["V", "P", "R", "S", "T", "U"]}
        ]
        net = PERTNetwork()
        net.cargar_desde_lista(activities)
        g = net.grafo
        
        # Debe ser un DAG válido
        assert nx.is_directed_acyclic_graph(g)
        
        # Deben existir todas las actividades reales
        edges_data = list(g.edges(data=True))
        reales = [d["id_actividad"] for u, v, d in edges_data if not d["es_ficticia"]]
        expected_reales = [act["id"] for act in activities]
        assert sorted(reales) == sorted(expected_reales)
        
        # Sin errores de validación de estructura (flujo, unicidad, DAG)
        from src.structural_validator import validate_network_structure
        result = validate_network_structure(net)
        assert result["SDD"]["estado_red"]["es_dag"] is True
        assert result["SDD"]["estado_red"]["unicidad"] is True
        assert result["SDD"]["estado_red"]["conservacion_flujo"] is True
        assert len(result["SDD"]["errores_topologicos"]) == 0
