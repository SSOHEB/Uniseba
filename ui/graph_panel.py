"""Knowledge graph panel using pywebview and vis.js."""

import json
import subprocess
import sys
import tempfile


def _build_graph_html(graph_data, title):
    safe_title = str(title or "").strip()
    payload = graph_data if isinstance(graph_data, dict) else {"nodes": [], "edges": []}
    graph_json = json.dumps(payload, ensure_ascii=False)
    title_json = json.dumps(safe_title, ensure_ascii=False)

    return f"""<!doctype html>
<html>
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
  <title>Knowledge Graph</title>
  <link rel=\"stylesheet\" href=\"https://cdnjs.cloudflare.com/ajax/libs/vis/4.21.0/vis.min.css\">
  <script src=\"https://cdnjs.cloudflare.com/ajax/libs/vis/4.21.0/vis.min.js\"></script>
  <style>
    html, body {{
      margin: 0;
      width: 100%;
      height: 100%;
      overflow: hidden;
      background: #0d1117;
      background-image: linear-gradient(#21262d 1px, transparent 1px), linear-gradient(90deg, #21262d 1px, transparent 1px);
      background-size: 40px 40px;
      font-family: \"Segoe UI\", sans-serif;
    }}
    #graph {{
      width: 100vw;
      height: 100vh;
    }}
    .title-pill {{
      position: fixed;
      top: 14px;
      left: 50%;
      transform: translateX(-50%);
      color: #00d4ff;
      background: rgba(0, 212, 255, 0.1);
      border: 1px solid rgba(0, 212, 255, 0.3);
      border-radius: 999px;
      padding: 8px 16px;
      font-size: 14px;
      letter-spacing: 0.05em;
      z-index: 10;
      backdrop-filter: blur(4px);
      pointer-events: none;
    }}
    .close-btn {{
      position: fixed;
      top: 14px;
      right: 14px;
      color: #8b949e;
      background: #161b22;
      border: 1px solid #30363d;
      border-radius: 8px;
      padding: 8px 12px;
      font-size: 13px;
      cursor: pointer;
      z-index: 10;
    }}
  </style>
</head>
<body>
  <div class=\"title-pill\" id=\"title\"></div>
  <button class=\"close-btn\" onclick=\"window.close()\">Close</button>
  <div id=\"graph\"></div>
  <script>
    const graphData = {graph_json};
    const graphTitle = {title_json};
    document.getElementById(\"title\").textContent = \"Knowledge Graph - \" + graphTitle;

    const nodes = new vis.DataSet(graphData.nodes || []);
    const edges = new vis.DataSet(graphData.edges || []);
    const container = document.getElementById(\"graph\");
    const data = {{ nodes, edges }};
    const options = {{
      nodes: {{
        shape: \"dot\",
        size: 22,
        shadow: {{
          enabled: true,
          color: \"rgba(0,212,255,0.3)\",
        }},
        font: {{ color: \"#e6edf3\" }},
        color: {{
          background: \"#1a2332\",
          border: \"#00d4ff\",
          highlight: {{
            background: \"#0d2137\",
            border: \"#00d4ff\",
          }}
        }}
      }},
      edges: {{
        arrows: {{ to: {{ enabled: true }} }},
        smooth: {{ type: \"dynamic\" }},
        shadow: true,
        width: 1.5,
        color: {{ color: \"#21262d\", highlight: \"#00d4ff\" }},
        font: {{ color: \"#484f58\", size: 11 }}
      }},
      physics: {{
        barnesHut: {{
          gravitationalConstant: -12000,
          centralGravity: 0.3,
          springLength: 200
        }},
        stabilization: {{
          iterations: 200
        }}
      }},
      interaction: {{
        hover: true,
        dragNodes: true,
        dragView: true,
        zoomView: true
      }}
    }};

    const network = new vis.Network(container, data, options);
    const target = String(graphTitle || \"\").trim().toLowerCase();
    if (target) {{
      const allNodes = nodes.get();
      const match = allNodes.find((n) => String(n.label || \"\").trim().toLowerCase() === target);
      if (match) {{
        nodes.update({{
          id: match.id,
          size: 38,
          color: {{
            background: \"#2d1a00\",
            border: \"#f59e0b\"
          }},
          font: {{
            color: \"#f59e0b\",
            bold: true
          }}
        }});
      }}
    }}
  </script>
</body>
</html>
"""


def open_graph(graph_data, title):
    html = _build_graph_html(graph_data, title)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".html", encoding="utf-8", delete=False) as temp_file:
        temp_file.write(html)
        temp_path = temp_file.name

    url = f"file:///{temp_path.replace(chr(92), '/')}"
    launcher = (
        "import sys, webview\n"
        "url = sys.argv[1]\n"
        "webview.create_window("
        "'Knowledge Graph', "
        "url=url, "
        "width=1100, "
        "height=750, "
        "resizable=True, "
        "on_top=True, "
        "frameless=False"
        ")\n"
        "webview.start()\n"
    )
    subprocess.Popen([sys.executable, "-c", launcher, url], close_fds=True)
