"""
Visualisation interactive du graphe de tarification.

Ce module génère une visualisation HTML/JavaScript interactive du graphe
permettant d'explorer la structure du tarif et de visualiser les évaluations.
"""
import json
from pathlib import Path
from typing import Dict, Optional, Any
from engine.graph import TariffGraph


def generate_interactive_viz(
    graph: TariffGraph,
    output_path: str = "graph_viz.html",
    trace: Optional[Dict] = None,
    context: Optional[Dict[str, Any]] = None,
    title: str = "Tariff Graph Visualization",
):
    """
    Génère une visualisation HTML interactive du graphe.

    Args:
        graph: Le graphe de tarification à visualiser
        output_path: Chemin du fichier HTML de sortie
        trace: Trace d'évaluation optionnelle (pour afficher les valeurs)
        context: Contexte d'évaluation optionnel (pour afficher les inputs)
        title: Titre de la visualisation

    Examples:
        >>> from engine.loader import TariffLoader
        >>> from engine.graph import TariffGraph
        >>> loader = TariffLoader(tables=tables)
        >>> nodes = loader.load("tariff.yaml")
        >>> graph = TariffGraph(nodes)
        >>>
        >>> # Visualisation simple
        >>> generate_interactive_viz(graph, "my_graph.html")
        >>>
        >>> # Avec évaluation
        >>> context = {"driver_age": 30, "brand": "BMW"}
        >>> trace = {}
        >>> result = graph.evaluate("total_premium", context, trace=trace)
        >>> generate_interactive_viz(graph, "evaluated_graph.html", trace=trace, context=context)
    """
    # Extraire les données du graphe
    nodes_data = []
    edges_data = []

    for name, node in graph.nodes.items():
        # Type de nœud
        node_type = type(node).__name__

        # Valeur évaluée si disponible
        value = None
        if trace and name in trace:
            val = trace[name]["value"]
            if val is not None:
                value = str(val)

        # Valeur d'input si disponible
        input_value = None
        if context and hasattr(node, "dtype") and name in context:
            input_value = str(context[name])

        nodes_data.append({
            "id": name,
            "label": name,
            "type": node_type,
            "value": value,
            "input_value": input_value,
        })

        # Ajouter les edges (dépendances)
        for dep in node.dependencies():
            edges_data.append({
                "from": dep,
                "to": name,
            })

    # Générer le HTML avec vis.js
    html_content = _generate_html_template(
        nodes_data,
        edges_data,
        title,
        bool(trace),
    )

    # Écrire le fichier
    Path(output_path).write_text(html_content, encoding="utf-8")
    print(f"✓ Visualisation interactive générée: {output_path}")
    print(f"  Ouvrir dans un navigateur: file://{Path(output_path).absolute()}")


def _generate_html_template(nodes_data, edges_data, title, has_trace):
    """Génère le template HTML avec vis.js."""

    # Couleurs par type de nœud
    node_colors = {
        "ConstantNode": "#90EE90",
        "InputNode": "#87CEEB",
        "AddNode": "#FFD700",
        "MultiplyNode": "#FFA500",
        "LookupNode": "#DDA0DD",
        "IfNode": "#FF6B6B",
        "RoundNode": "#98D8C8",
        "SwitchNode": "#F7B7A3",
        "CoalesceNode": "#AED8E6",
        "MinNode": "#B8E6B8",
        "MaxNode": "#E6B8B8",
        "AbsNode": "#E6D8B8",
    }

    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <script src="https://unpkg.com/vis-network@9.1.2/standalone/umd/vis-network.min.js"></script>
    <style>
        body {{
            margin: 0;
            padding: 0;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #f5f5f5;
        }}
        #header {{
            background: #2c3e50;
            color: white;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        #header h1 {{
            margin: 0;
            font-size: 24px;
        }}
        #header p {{
            margin: 5px 0 0 0;
            opacity: 0.8;
            font-size: 14px;
        }}
        #container {{
            display: flex;
            height: calc(100vh - 100px);
        }}
        #network {{
            flex: 1;
            background: white;
            border-right: 1px solid #ddd;
        }}
        #sidebar {{
            width: 350px;
            background: white;
            padding: 20px;
            overflow-y: auto;
            box-shadow: -2px 0 4px rgba(0,0,0,0.1);
        }}
        #sidebar h2 {{
            margin-top: 0;
            color: #2c3e50;
            font-size: 18px;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
        }}
        .node-detail {{
            margin: 10px 0;
            padding: 10px;
            background: #f8f9fa;
            border-radius: 4px;
            border-left: 3px solid #3498db;
        }}
        .node-detail strong {{
            color: #2c3e50;
            display: block;
            margin-bottom: 5px;
        }}
        .node-detail .value {{
            font-family: 'Courier New', monospace;
            background: #e9ecef;
            padding: 5px;
            border-radius: 3px;
            display: inline-block;
            margin-top: 5px;
        }}
        .legend {{
            margin-top: 20px;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 4px;
        }}
        .legend h3 {{
            margin: 0 0 10px 0;
            font-size: 14px;
            color: #2c3e50;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            margin: 5px 0;
            font-size: 12px;
        }}
        .legend-color {{
            width: 20px;
            height: 20px;
            border-radius: 50%;
            margin-right: 10px;
            border: 2px solid #333;
        }}
        .controls {{
            padding: 15px;
            background: #ecf0f1;
            border-radius: 4px;
            margin-bottom: 20px;
        }}
        .controls button {{
            background: #3498db;
            color: white;
            border: none;
            padding: 8px 15px;
            border-radius: 4px;
            cursor: pointer;
            margin: 5px 5px 5px 0;
            font-size: 12px;
        }}
        .controls button:hover {{
            background: #2980b9;
        }}
        #stats {{
            font-size: 12px;
            color: #7f8c8d;
            margin-top: 10px;
        }}
    </style>
</head>
<body>
    <div id="header">
        <h1>{title}</h1>
        <p>Exploration interactive du graphe de tarification</p>
    </div>

    <div id="container">
        <div id="network"></div>
        <div id="sidebar">
            <div class="controls">
                <button onclick="network.fit()">🔍 Recentrer</button>
                <button onclick="togglePhysics()">⚡ Toggle Physics</button>
                <button onclick="exportImage()">📷 Export PNG</button>
                <div id="stats"></div>
            </div>

            <div id="node-info">
                <h2>Node Information</h2>
                <p style="color: #7f8c8d;">Cliquez sur un nœud pour voir ses détails</p>
            </div>

            <div class="legend">
                <h3>Légende des types de nœuds</h3>
                {_generate_legend_html(node_colors)}
            </div>
        </div>
    </div>

    <script>
        // Données du graphe
        const nodesData = {json.dumps(nodes_data, indent=2)};
        const edgesData = {json.dumps(edges_data, indent=2)};
        const hasTrace = {json.dumps(has_trace)};
        const nodeColors = {json.dumps(node_colors, indent=2)};

        // Préparer les nœuds pour vis.js
        const nodes = new vis.DataSet(nodesData.map(node => ({{
            id: node.id,
            label: node.label,
            title: generateNodeTooltip(node),
            color: {{
                background: nodeColors[node.type] || '#ccc',
                border: node.value ? '#27ae60' : '#333',
                highlight: {{
                    background: nodeColors[node.type] || '#ccc',
                    border: '#e74c3c'
                }}
            }},
            borderWidth: node.value ? 3 : 2,
            font: {{
                size: 14,
                color: '#2c3e50'
            }},
            shape: 'box',
            margin: 10,
        }})));

        // Préparer les edges pour vis.js
        const edges = new vis.DataSet(edgesData.map(edge => ({{
            from: edge.from,
            to: edge.to,
            arrows: 'to',
            color: {{
                color: '#95a5a6',
                highlight: '#3498db'
            }},
            smooth: {{
                type: 'cubicBezier',
                forceDirection: 'vertical',
                roundness: 0.4
            }}
        }})));

        // Configuration du réseau
        const container = document.getElementById('network');
        const data = {{ nodes: nodes, edges: edges }};
        const options = {{
            layout: {{
                hierarchical: {{
                    direction: 'UD',
                    sortMethod: 'directed',
                    levelSeparation: 150,
                    nodeSpacing: 100,
                }}
            }},
            physics: {{
                enabled: false
            }},
            interaction: {{
                hover: true,
                navigationButtons: true,
                keyboard: true
            }},
            nodes: {{
                shadow: true
            }},
            edges: {{
                shadow: true
            }}
        }};

        // Créer le réseau
        const network = new vis.Network(container, data, options);

        // Stats
        document.getElementById('stats').innerHTML =
            `📊 ${{nodesData.length}} nœuds, ${{edgesData.length}} connexions`;

        // Event listener pour les clics
        network.on('click', function(params) {{
            if (params.nodes.length > 0) {{
                const nodeId = params.nodes[0];
                const node = nodesData.find(n => n.id === nodeId);
                displayNodeInfo(node);
            }}
        }});

        // Générer le tooltip d'un nœud
        function generateNodeTooltip(node) {{
            let tooltip = `<b>${{node.label}}</b><br>Type: ${{node.type}}`;
            if (node.input_value) {{
                tooltip += `<br>Input: ${{node.input_value}}`;
            }}
            if (node.value) {{
                tooltip += `<br>Value: ${{node.value}}`;
            }}
            return tooltip;
        }}

        // Afficher les informations d'un nœud
        function displayNodeInfo(node) {{
            let html = `
                <h2>${{node.label}}</h2>
                <div class="node-detail">
                    <strong>Type:</strong> ${{node.type}}
                </div>
            `;

            if (node.input_value) {{
                html += `
                    <div class="node-detail">
                        <strong>Input Value:</strong>
                        <div class="value">${{node.input_value}}</div>
                    </div>
                `;
            }}

            if (node.value) {{
                html += `
                    <div class="node-detail">
                        <strong>Evaluated Value:</strong>
                        <div class="value">${{node.value}}</div>
                    </div>
                `;
            }}

            // Dependencies
            const deps = edgesData.filter(e => e.to === node.id);
            if (deps.length > 0) {{
                html += `
                    <div class="node-detail">
                        <strong>Dependencies (${{deps.length}}):</strong><br>
                        ${{deps.map(d => d.from).join(', ')}}
                    </div>
                `;
            }}

            // Dependents
            const dependents = edgesData.filter(e => e.from === node.id);
            if (dependents.length > 0) {{
                html += `
                    <div class="node-detail">
                        <strong>Used by (${{dependents.length}}):</strong><br>
                        ${{dependents.map(d => d.to).join(', ')}}
                    </div>
                `;
            }}

            document.getElementById('node-info').innerHTML = html;
        }}

        // Toggle physics
        let physicsEnabled = false;
        function togglePhysics() {{
            physicsEnabled = !physicsEnabled;
            network.setOptions({{ physics: {{ enabled: physicsEnabled }} }});
        }}

        // Export image (requires vis-network with canvas support)
        function exportImage() {{
            const canvas = document.querySelector('#network canvas');
            if (canvas) {{
                const link = document.createElement('a');
                link.download = 'graph.png';
                link.href = canvas.toDataURL();
                link.click();
            }} else {{
                alert('Export not available');
            }}
        }}
    </script>
</body>
</html>"""


def _generate_legend_html(node_colors):
    """Génère le HTML de la légende."""
    html_parts = []
    for node_type, color in node_colors.items():
        display_name = node_type.replace("Node", "")
        html_parts.append(f"""
                <div class="legend-item">
                    <div class="legend-color" style="background: {color};"></div>
                    <span>{display_name}</span>
                </div>
        """)
    return "".join(html_parts)


# Fonction helper pour une utilisation rapide
def quick_viz(tariff_path: str, tables: dict, output_path: str = "graph.html"):
    """
    Fonction helper pour visualiser rapidement un tarif.

    Args:
        tariff_path: Chemin vers le fichier YAML du tarif
        tables: Dictionnaire des tables de lookup
        output_path: Chemin du fichier HTML de sortie

    Examples:
        >>> from engine.tables import load_range_table, load_exact_table
        >>> tables = {
        ...     "age_table": load_range_table("tables/age_factors.csv"),
        ...     "brand_table": load_exact_table("tables/brand_factors.csv"),
        ... }
        >>> quick_viz("tariff.yaml", tables, "my_viz.html")
    """
    from engine.loader import TariffLoader

    loader = TariffLoader(tables=tables)
    nodes = loader.load(tariff_path)
    graph = TariffGraph(nodes)

    generate_interactive_viz(graph, output_path)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python interactive_viz.py <tariff.yaml> [output.html]")
        print("\nExemple:")
        print("  python interactive_viz.py tariffs/motor_private/2024_09/tariff.yaml")
        sys.exit(1)

    tariff_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else "graph_viz.html"

    # Pour l'exemple, charger avec des tables vides
    # En production, charger les vraies tables
    from engine.loader import TariffLoader

    try:
        # Essayer de charger avec les tables du tarif
        from pathlib import Path
        tariff_dir = Path(tariff_path).parent
        # TODO: Auto-detect tables from YAML
        loader = TariffLoader(tables={})
        nodes = loader.load(tariff_path)
        graph = TariffGraph(nodes)

        generate_interactive_viz(graph, output_path, title=f"Tariff: {Path(tariff_path).name}")
    except Exception as e:
        print(f"❌ Erreur: {e}")
        sys.exit(1)
