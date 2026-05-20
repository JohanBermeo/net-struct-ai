import networkx as nx
try:
    from core_math import validate_dag, find_source_nodes, find_sink_nodes, validate_flow_conservation
except ModuleNotFoundError:
    from src.core_math import validate_dag, find_source_nodes, find_sink_nodes, validate_flow_conservation

def validate_network_structure(red_pert) -> dict:
    """
    Realiza la validación topológica de la red PERT y genera el SDD (Structural Diagnostic Data).
    """
    G = red_pert.grafo
    
    # 1. Validar DAG (Grafo Dirigido Acíclico)
    dag_result = validate_dag(G)
    es_dag = dag_result.get("is_dag", False)
    
    # 2. Validar Unicidad
    fuentes = find_source_nodes(G)
    sumideros = find_sink_nodes(G)
    unicidad = len(fuentes) == 1 and len(sumideros) == 1
    
    # 3. Validar Conservación de Flujo
    flujo_errores = validate_flow_conservation(G)
    conservacion = len(flujo_errores) == 0
    
    errores_topologicos = []
    if not es_dag:
        if dag_result.get("cycle_nodes"):
            ciclo_nodos = " -> ".join(map(str, dag_result["cycle_nodes"]))
            errores_topologicos.append(f"Ciclo detectado en los nodos: {ciclo_nodos}")
        else:
            errores_topologicos.append("Se detectaron ciclos en la red (no es un DAG).")
            
    if len(fuentes) != 1:
        errores_topologicos.append(f"Problema de unicidad: se detectaron {len(fuentes)} nodos iniciales (fuentes) {fuentes}.")
        
    if len(sumideros) != 1:
        errores_topologicos.append(f"Problema de unicidad: se detectaron {len(sumideros)} nodos finales (sumideros) {sumideros}.")
        
    for err in flujo_errores:
        errores_topologicos.append(err)
        
    sdd = {
        "estado_red": {
            "es_dag": es_dag,
            "unicidad": unicidad,
            "conservacion_flujo": conservacion
        },
        "errores_topologicos": errores_topologicos,
        "estructura": red_pert.obtener_estructura_json()
    }
    
    return {"SDD": sdd}
