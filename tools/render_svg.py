"""Render a `graph.json` as a static SVG, for a README or a slide.

Not part of the tool: `dendro build` produces the interactive views, and this
exists only so the picture in the README comes from a real scan instead of a
mockup. Same force layout as `views/graph.html`, run to completion and frozen.

    python3 tools/render_svg.py path/to/graph.json out.svg
"""
import json, math, random, sys

SHOW = {"Artifact", "Tool", "Technique"}
COLOR = {"Artifact": "#4c7ef3", "Tool": "#e0803a", "Technique": "#2f9e74"}
R = {"Artifact": 5, "Tool": 8, "Technique": 6.5}
W, H = 960, 400
FLOOR = H - 74          # onde ficam os isolados
PAD_X, PAD_TOP = 70, 40

g = json.load(open(sys.argv[1]))
nodes = {n["id"]: n for n in g["nodes"] if n["type"] in SHOW}
edges = [e for e in g["edges"] if e["from"] in nodes and e["to"] in nodes]

degree = {i: 0 for i in nodes}
for e in edges:
    degree[e["from"]] += 1
    degree[e["to"]] += 1

# Um Artifact sem aresta deriva para a borda e estica a caixa, achatando o
# resto. Vai para uma fileira própria, dito com todas as letras.
linked = {i for i, d in degree.items() if d}
loose = [i for i in nodes if i not in linked]

# Ordenado, não sobre o set: a ordem de iteração de um set de strings muda
# a cada processo, e com ela as posições iniciais. A figura tem que sair igual
# toda vez, senão "regenerate with" no README é uma promessa falsa.
random.seed(11)
pos = {i: [random.uniform(-200, 200), random.uniform(-120, 120)] for i in sorted(linked)}
for step in range(900):
    cool = 1 - step / 900
    force = {i: [0.0, 0.0] for i in pos}
    items = sorted(pos.items())
    for a in range(len(items)):
        ia, pa = items[a]
        for b in range(a + 1, len(items)):
            ib, pb = items[b]
            dx, dy = pa[0] - pb[0], pa[1] - pb[1]
            d2 = dx * dx + dy * dy + 0.01
            rep = 2600 / d2
            force[ia][0] += dx * rep; force[ia][1] += dy * rep
            force[ib][0] -= dx * rep; force[ib][1] -= dy * rep
    for e in edges:
        pa, pb = pos[e["from"]], pos[e["to"]]
        dx, dy = pb[0] - pa[0], pb[1] - pa[1]
        d = math.hypot(dx, dy) + 0.01
        pull = (d - 78) * 0.010
        force[e["from"]][0] += dx / d * pull; force[e["from"]][1] += dy / d * pull
        force[e["to"]][0] -= dx / d * pull; force[e["to"]][1] -= dy / d * pull
    for i, p in pos.items():
        # Achata levemente na vertical: o espaço é largo e baixo.
        p[0] += max(-9, min(9, force[i][0])) * cool - p[0] * 0.0012
        p[1] += max(-9, min(9, force[i][1] * 0.62)) * cool - p[1] * 0.0022

xs = [p[0] for p in pos.values()]; ys = [p[1] for p in pos.values()]
# Escala por eixo: um layout de força não tem proporção verdadeira, e
# preservá-la aqui só deixaria metade da largura vazia.
sx = (W - 2 * PAD_X - 140) / max(1e-6, max(xs) - min(xs))
sy = (FLOOR - PAD_TOP - 34) / max(1e-6, max(ys) - min(ys))
def place(i):
    return (PAD_X + (pos[i][0] - min(xs)) * sx, PAD_TOP + (pos[i][1] - min(ys)) * sy)

out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="100%" role="img" '
       f'aria-label="Artifacts linked to the Tools and Techniques they use, from a real scan">']
out.append('<style>text{font:12px ui-sans-serif,system-ui,-apple-system,sans-serif}'
           '.t{font-size:11px;fill:#8a8f98}.k{font-size:12px;fill:#6b7280;font-weight:500}</style>')
for e in edges:
    x1, y1 = place(e["from"]); x2, y2 = place(e["to"])
    out.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
               f'stroke="#9aa0a6" stroke-opacity=".2"/>')
placed: list = []   # rótulos já colocados, para não escreverem uns por cima dos outros
# Desempate pelo id: `sorted` é estável, então empatar no tipo deixaria a
# ordem do set decidir — e com ela a ordem dos elementos e dos rótulos.
for i in sorted(linked, key=lambda i: (nodes[i]["type"] != "Artifact", i)):
    kind = nodes[i]["type"]
    x, y = place(i)
    out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{R[kind]}" fill="{COLOR[kind]}" fill-opacity=".88"/>')
    if kind not in ("Tool", "Technique"):
        continue
    label = nodes[i]["label"]
    width = len(label) * 6.6
    right = x + R[kind] + 5
    anchor, lx = ("start", right) if right + width < W - 12 else ("end", x - R[kind] - 5)
    ly = y + 4
    for _ in range(14):
        left = lx if anchor == "start" else lx - width
        if not any(
            abs(ly - py) < 12 and left < px + pw and lx + (width if anchor == "start" else 0) > px
            for px, py, pw in placed
        ):
            break
        ly += 13
    placed.append((lx if anchor == "start" else lx - width, ly, width))
    out.append(f'<text class="k" x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anchor}">{label}</text>')

if loose:
    for n, i in enumerate(sorted(loose)):
        out.append(f'<circle cx="{PAD_X + n * 17}" cy="{FLOOR + 6}" r="{R["Artifact"]}" '
                   f'fill="{COLOR["Artifact"]}" fill-opacity=".35"/>')
    out.append(f'<text class="t" x="{PAD_X + len(loose) * 17 + 8}" y="{FLOOR + 10}">'
               f'{len(loose)} Artifact(s) with no Tool detected — still in the archive</text>')

for n, kind in enumerate(("Artifact", "Tool", "Technique")):
    x = PAD_X + n * 108
    out.append(f'<circle cx="{x}" cy="{H - 20}" r="{R[kind]}" fill="{COLOR[kind]}" fill-opacity=".88"/>')
    out.append(f'<text class="t" x="{x + 14}" y="{H - 16}">{kind}</text>')
out.append(f'<text class="t" x="{W - 12}" y="{H - 16}" text-anchor="end">'
           f'{sum(1 for i in nodes if nodes[i]["type"]=="Artifact")} Artifacts · '
           f'{len(edges)} edges · rendered from a real scan</text>')
out.append("</svg>")
open(sys.argv[2], "w").write("\n".join(out) + "\n")
print("wrote", sys.argv[2])
