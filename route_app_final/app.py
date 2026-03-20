from flask import Flask, render_template, request, jsonify
from arbol import Nodo
import json, os

app = Flask(__name__)

# ─── Carga de datos ───────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(BASE_DIR, "routes_data.json"), "r", encoding="utf-8") as f:
    DATA = json.load(f)

CITIES      = DATA["cities"]
CONNECTIONS = DATA["connections"]


def build_graph():
    """Grafo bidireccional: ciudad -> [(vecino, distancia, tiempo), ...]"""
    graph = {city: [] for city in CITIES}
    for conn in CONNECTIONS:
        a, b = conn["from"], conn["to"]
        d, t = conn["distance"], conn["time"]
        if a in graph and b in graph:
            graph[a].append((b, d, t))
            graph[b].append((a, d, t))
    return graph


GRAPH = build_graph()


# ─── BFS con tu clase Nodo ────────────────────────────────────────────────────
def buscar_solucion_BFS(ciudad_origen, ciudad_destino):
    """
    Búsqueda en amplitud usando la clase Nodo de arbol.py.
    Cada nodo guarda el nombre de la ciudad como dato.
    Devuelve el nodo solución (para remontar el camino) o None.
    """
    nodos_visitados = []
    nodos_frontera  = []

    nodo_inicial = Nodo(ciudad_origen)
    nodo_inicial.set_costos({"distance": 0, "time": 0})
    nodos_frontera.append(nodo_inicial)

    while nodos_frontera:
        nodo = nodos_frontera.pop(0)            # FIFO → BFS
        nodos_visitados.append(nodo)

        # ¿Solución encontrada?
        if nodo.get_datos() == ciudad_destino:
            return nodo

        # Expandir vecinos
        ciudad_actual = nodo.get_datos()
        costo_actual  = nodo.get_costo() or {"distance": 0, "time": 0}
        hijos = []

        for vecino, dist, tiempo in GRAPH.get(ciudad_actual, []):
            hijo = Nodo(vecino)
            hijo.set_costos({
                "distance": costo_actual["distance"] + dist,
                "time":     costo_actual["time"]     + tiempo,
            })

            if not hijo.en_lista(nodos_visitados) and \
               not hijo.en_lista(nodos_frontera):
                nodos_frontera.append(hijo)
                hijos.append(hijo)

        nodo.set_hijos(hijos if hijos else None)

    return None   # sin solución


def reconstruir_ruta(nodo_solucion, ciudad_origen):
    """Remonta el árbol de padres igual que en tu BFS.py original."""
    resultado = []
    nodo = nodo_solucion
    while nodo.get_padre() is not None:
        resultado.append(nodo.get_datos())
        nodo = nodo.get_padre()
    resultado.append(ciudad_origen)
    resultado.reverse()
    return resultado


# ─── Rutas Flask ──────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/cities")
def get_cities():
    return jsonify(CITIES)


@app.route("/api/route", methods=["POST"])
def get_route():
    body        = request.get_json()
    origin      = body.get("origin", "").strip()
    destination = body.get("destination", "").strip()

    if not origin or not destination:
        return jsonify({"error": "Debes indicar origen y destino."}), 400
    if origin not in CITIES:
        return jsonify({"error": f"Ciudad de origen no encontrada: '{origin}'"}), 404
    if destination not in CITIES:
        return jsonify({"error": f"Ciudad destino no encontrada: '{destination}'"}), 404
    if origin == destination:
        return jsonify({"error": "El origen y destino deben ser ciudades distintas."}), 400

    nodo_solucion = buscar_solucion_BFS(origin, destination)

    if nodo_solucion is None:
        return jsonify({"error": "No existe ruta disponible entre esas ciudades."}), 404

    path       = reconstruir_ruta(nodo_solucion, origin)
    costo_fin  = nodo_solucion.get_costo() or {"distance": 0, "time": 0}

    waypoints = [
        {"city": c, "lat": CITIES[c]["lat"], "lng": CITIES[c]["lng"]}
        for c in path
    ]

    return jsonify({
        "path":               path,
        "waypoints":          waypoints,
        "total_distance_km":  costo_fin["distance"],
        "total_time_hours":   costo_fin["time"],
        "stops":              len(path) - 2,
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)
