/* A view do grafo, fora da página que a hospeda.
 *
 * O nome tem prefixo porque `core/build.emit` escreve os dados como `graph.js`
 * e só então copia `views/*.js` por cima: um arquivo chamado `graph.js` aqui
 * substituiria o arquivo inteiro por este renderizador, e a falha apareceria
 * como um grafo vazio em vez de um erro de build (tests/test_view_assets.py).
 *
 * `create` recebe a raiz onde os elementos da view vivem — um documento hoje,
 * um contêiner quando a tela única chegar — e devolve o punhado de coisas que
 * quem hospeda precisa: ligar, desligar, selecionar, buscar e repintar.
 */
(function (global) {
  "use strict";

  function create(root, g, options) {
    options = options || {};
    function el(id) { return root.querySelector("#" + id); }

    // A legenda vai para quem tem cabeçalho — o módulo desenha, não titula.
    if (options.meta) {
    options.meta.textContent =
      g.nodes.length + " nodes · " + g.edges.length +
      " edges · hover or click a node, search by name, filter by type";
    }

    // Movimento reduzido desliga o que é decoração — o enquadramento
    // interpolado e a transição do foco. O assentamento do layout fica: ele é o
    // conteúdo sendo calculado, não um enfeite, e congelar a página por oito
    // segundos para escondê-lo seria pior do que mostrá-lo.
    var calm = window.matchMedia
    && matchMedia("(prefers-reduced-motion: reduce)").matches;

    // Paleta por variável CSS: o botão de tema troca os tokens e o canvas
    // é redesenhado com a mesma fonte de verdade das outras views.
    function palette() {
    var css = getComputedStyle(document.documentElement);
    function v(name) { return css.getPropertyValue(name).trim(); }
    return {
      COLOUR: {
        Artifact: v("--c-artifact"), Tool: v("--c-tool"),
        Technique: v("--c-technique"), Period: v("--c-period"),
        Collection: v("--c-collection"), Author: v("--c-author"),
        Dependency: v("--c-dependency"), EpochMarker: v("--c-marker")
      },
      FORK: v("--fork"),
      EDGE: v("--border"),
      TEXT: v("--text-primary"),
      MUTED: v("--text-muted"),
      SURFACE: v("--surface-0")
    };
  }

  var canvas = el("canvas");
  var ctx = canvas.getContext("2d");
  var chip = el("chip");
  var view = { x: 0, y: 0, k: 1 };
  var pal = palette();
  var COLOUR = pal.COLOUR;
  var FORK = pal.FORK;

  // A simulação para quando assenta, e a vista se enquadra sozinha até que
  // alguém arraste ou role. Sem as duas coisas um grafo de 2.000 nós sai do
  // quadro nos primeiros segundos e não volta (T042).
  var settled = false, userMoved = false, dirty = true, quiet = 0, ticks = 0;

  // Cada nó vira um ponto com velocidade; nada aqui vem de biblioteca.
  var nodes = g.nodes.map(function (node, i) {
    var angle = i * 2.399963;             // ângulo áureo: espalha sem agrupar
    var radius = 14 * Math.sqrt(i);
    return {
      ref: node, x: Math.cos(angle) * radius, y: Math.sin(angle) * radius,
      vx: 0, vy: 0, sx: 0, sy: 0, degree: 0,
      r: node.type === "Artifact" ? 5 : 3.2,
      colour: null
    };
  });
  // Cor, condição de fork e balde de desenho ficam presos ao nó. `isBarelyMine`
  // percorre a autoria inteira, e perguntá-la 2.300 vezes por quadro é pagar
  // por uma resposta que só muda quando o tema muda.
  var shades = [], shadeOf = {}, groups = [];
  function recolour() {
    shades = []; shadeOf = {};
    nodes.forEach(function (n) {
      n.fork = g.isBarelyMine(n.ref);
      n.colour = n.fork ? FORK : (COLOUR[n.ref.type] || "#888");
      if (shadeOf[n.colour] === undefined) {
        shadeOf[n.colour] = shades.length;
        shades.push(n.colour);
      }
      n.shade = shadeOf[n.colour];
    });
    stamps = {}; stampCount = 0;
  }
  var index = {};
  nodes.forEach(function (n) { index[n.ref.id] = n; });
  var links = g.edges.map(function (edge) {
    return { source: index[edge.from], target: index[edge.to], type: edge.type };
  }).filter(function (l) { return l.source && l.target; });
  links.forEach(function (l) { l.source.degree++; l.target.degree++; });

  // Vizinhança pré-calculada: o realce precisa dela a cada movimento do
  // ponteiro, e varrer 3.000 arestas por quadro para descobri-la não cabe.
  var incident = {};
  links.forEach(function (l) {
    (incident[l.source.ref.id] = incident[l.source.ref.id] || []).push(l);
    (incident[l.target.ref.id] = incident[l.target.ref.id] || []).push(l);
  });

  function resize() {
    var ratio = window.devicePixelRatio || 1;
    canvas.width = canvas.clientWidth * ratio;
    canvas.height = canvas.clientHeight * ratio;
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  }
  window.addEventListener("resize", function () { resize(); dirty = true; });
  resize();

  var alpha = 1;
  function tick() {
    // Repulsão par a par: a 3.000 nós isto ainda cabe num quadro. Barnes-Hut
    // fica para a v0.3, e a validação de SC-005 é o que diz quando ele passa
    // a ser necessário.
    for (var i = 0; i < nodes.length; i++) {
      var a = nodes[i];
      for (var j = i + 1; j < nodes.length; j++) {
        var b = nodes[j];
        var dx = b.x - a.x, dy = b.y - a.y;
        // O `+ 400` é o que impede a singularidade: em `220 / d2` puro, dois
        // nós que se encostam trocam uma força ilimitada e são arremessados
        // para fora de qualquer vista possível.
        var d2 = dx * dx + dy * dy + 400;
        var force = 220 / d2;
        var d = Math.sqrt(d2);
        var fx = (dx / d) * force, fy = (dy / d) * force;
        a.vx -= fx; a.vy -= fy; b.vx += fx; b.vy += fy;
      }
    }
    links.forEach(function (link) {
      var dx = link.target.x - link.source.x, dy = link.target.y - link.source.y;
      var d = Math.sqrt(dx * dx + dy * dy) || 0.01;
      var force = (d - 42) * 0.012;
      var fx = (dx / d) * force, fy = (dy / d) * force;
      link.source.vx += fx; link.source.vy += fy;
      link.target.vx -= fx; link.target.vy -= fy;
    });
    var moved = 0;
    nodes.forEach(function (n) {
      n.vx -= n.x * 0.004; n.vy -= n.y * 0.004;     // gravidade ao centro
      // Teto de velocidade: a repulsão de milhares de vizinhos soma mais
      // rápido do que o amortecimento tira, e um único quadro sem teto já
      // leva o nó a coordenadas das quais ele não volta.
      var speed = Math.sqrt(n.vx * n.vx + n.vy * n.vy);
      if (speed > 25) { n.vx *= 25 / speed; n.vy *= 25 / speed; }
      var dx = n.vx * alpha, dy = n.vy * alpha;
      n.x += dx; n.y += dy;
      moved += Math.sqrt(dx * dx + dy * dy);
      n.vx *= 0.82; n.vy *= 0.82;
    });
    alpha *= 0.995;
    if (alpha < 0.02) alpha = 0.02;

    // Assentado: nada mais se move o bastante para ser visto. Parar aqui é o
    // que devolve a CPU — cada quadro percorre todos os pares de nós, e a
    // 2.300 nós isso é 2,6 milhões deles, para sempre.
    ticks++;
    quiet = moved / nodes.length < 0.05 ? quiet + 1 : 0;
    if (quiet > 30 || ticks > 1500) settled = true;
  }

  // Enquadra a caixa que os nós ocupam, seja ela qual for. É o que garante que
  // o grafo esteja na tela em vez de em algum lugar fora dela.
  function fitToLayout() {
    var w = canvas.clientWidth, h = canvas.clientHeight;
    if (!w || !h || !nodes.length) return;
    var minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    // Só o que está visível: com Dependency e Author desligados, enquadrar a
    // caixa de todos deixaria os poucos que sobraram num canto.
    var seen = 0;
    nodes.forEach(function (n) {
      if (n.off) return;
      seen++;
      if (n.x < minX) minX = n.x;
      if (n.x > maxX) maxX = n.x;
      if (n.y < minY) minY = n.y;
      if (n.y > maxY) maxY = n.y;
    });
    if (!seen || !isFinite(minX) || !isFinite(minY)) return;
    var target = Math.min(w / (maxX - minX + 96), h / (maxY - minY + 96));
    target = Math.min(6, Math.max(0.05, target));
    // Interpolado, não saltado: o layout ainda respira nos primeiros quadros e
    // um enquadramento instantâneo a cada um deles pisca.
    var ease = calm ? 1 : 0.12;
    view.k += (target - view.k) * ease;
    view.x += (-((minX + maxX) / 2) * view.k - view.x) * ease;
    view.y += (-((minY + maxY) / 2) * view.k - view.y) * ease;
    dirty = true;
  }

  // ---------- foco, seleção e filtros ----------
  // `focus` é o nó em torno do qual o grafo está aceso, venha do cursor ou de
  // um clique. `selected` é para onde o foco volta quando o cursor sai: sem
  // ele, ler as ligações de um nó exige manter a mão parada.
  var focus = null, selected = null, focusAmount = 0, litSet = null;

  // Tipo desligado não sai da simulação, só do desenho. Tirá-lo da física faz
  // o layout inteiro se reorganizar a cada interruptor, e quem estava lendo
  // uma vizinhança perde o lugar — o filtro é sobre o que se vê, não sobre
  // onde as coisas estão.
  var hiddenTypes = Object.create(null);
  function applyFilters() {
    for (var i = 0; i < nodes.length; i++) {
      nodes[i].off = hiddenTypes[nodes[i].ref.type] === true;
    }
    if (focus && focus.off) setFocus(null);
    if (selected && selected.off) { selected = null; hideChip(); }
    dirty = true;
  }

  // Quem fica aceso é decidido quando o foco muda, e não a cada nó de cada
  // quadro: sobre um nó de 500 arestas a varredura por nó custava um milhão
  // de comparações por quadro, bem no momento em que a página não pode travar.
  function setFocus(node) {
    focus = node;
    if (!node) { litSet = null; return; }
    litSet = Object.create(null);
    litSet[node.ref.id] = 1;
    var edges = incident[node.ref.id] || [];
    for (var i = 0; i < edges.length; i++) {
      litSet[edges[i].source.ref.id] = 1;
      litSet[edges[i].target.ref.id] = 1;
    }
  }
  function lit(node) {
    return !litSet || litSet[node.ref.id] === 1;
  }

  // Clicar prende. O mesmo realce do cursor, só que fica: é o que permite
  // arrastar a vista, dar zoom e continuar lendo as mesmas arestas.
  function select(node) {
    selected = node;
    setFocus(node);
    if (node) { fillChip(node); chip.classList.add("pinned"); }
    else hideChip();
    dirty = true;
  }

  // Levar a vista até um nó em vez de teleportar: quem procurou um nome
  // precisa ver para onde a tela foi, ou perde a noção de onde ele está.
  var glide = null;
  function centreOn(node) {
    userMoved = true;
    var k = Math.min(6, Math.max(view.k, 1.8));
    glide = { x: -node.x * k, y: -node.y * k, k: k };
    if (calm) { view.x = glide.x; view.y = glide.y; view.k = glide.k; glide = null; }
    dirty = true;
  }
  function litEdge(link) {
    return !focus || link.source === focus || link.target === focus;
  }

  // ---------- rótulos ----------
  // Desenhados em espaço de tela, com tamanho constante: em espaço do grafo
  // eles encolhem com o zoom até sumir e crescem até tapar o desenho. Uma
  // malha de ocupação impede que dois rótulos se sobreponham — texto empilhado
  // é menos legível que texto ausente.
  var CELL = 14, occupied = null, cols = 0, rows = 0;
  function resetLabels(w, h) {
    cols = Math.ceil(w / CELL) + 2;
    rows = Math.ceil(h / CELL) + 2;
    if (!occupied || occupied.length !== cols * rows) occupied = new Uint8Array(cols * rows);
    else occupied.fill(0);
  }
  function claim(x, y, textWidth, height) {
    var c0 = Math.floor(x / CELL), c1 = Math.floor((x + textWidth) / CELL);
    var r0 = Math.floor((y - height) / CELL), r1 = Math.floor(y / CELL);
    if (c0 < 0 || r0 < 0 || c1 >= cols || r1 >= rows) return false;
    var c, r;
    for (r = r0; r <= r1; r++) {
      for (c = c0; c <= c1; c++) if (occupied[r * cols + c]) return false;
    }
    for (r = r0; r <= r1; r++) {
      for (c = c0; c <= c1; c++) occupied[r * cols + c] = 1;
    }
    return true;
  }
  // Halo antes do preenchimento: sem ele o texto compete com as arestas que
  // passam por baixo e nenhum dos dois se lê. Só que contornar texto obriga o
  // motor a traçar cada glifo como caminho, sem passar pelo cache de glifos —
  // duzentos rótulos por quadro custam mais que os 2.300 nós somados. Então
  // cada rótulo é desenhado uma vez fora da tela e a partir daí é copiado.
  // Largura e desenho vêm de caches separados: a largura é precisa saber antes
  // de disputar a célula, e rasterizar quem vai perder a disputa é desperdício.
  var FONT = ' 11px "IBM Plex Sans", ui-sans-serif, system-ui, sans-serif';
  var PAD = 3, STAMP_H = 18;
  var widths = {}, stamps = {}, stampCount = 0;

  function widthOf(text, weight) {
    var key = weight + "|" + text;
    var width = widths[key];
    if (width === undefined) {
      ctx.font = weight + FONT;
      width = widths[key] = ctx.measureText(text).width;
    }
    return width;
  }

  function stamp(text, weight, colour, width) {
    var key = weight + "|" + colour + "|" + text;
    var found = stamps[key];
    if (found) return found;
    // Um teto: quem explorar o grafo inteiro não deve acumular um bitmap por
    // nó até o fim da sessão.
    if (stampCount > 3000) { stamps = {}; stampCount = 0; }
    var ratio = window.devicePixelRatio || 1;
    var box = Math.ceil(width) + PAD * 2;
    var tile = document.createElement("canvas");
    tile.width = Math.ceil(box * ratio);
    tile.height = Math.ceil(STAMP_H * ratio);
    var pen = tile.getContext("2d");
    pen.setTransform(ratio, 0, 0, ratio, 0, 0);
    pen.font = weight + FONT;
    pen.textBaseline = "middle";
    pen.lineJoin = "round";
    pen.lineWidth = 3;
    pen.strokeStyle = pal.SURFACE;
    pen.strokeText(text, PAD, STAMP_H / 2);
    pen.fillStyle = colour;
    pen.fillText(text, PAD, STAMP_H / 2);
    stampCount++;
    return (stamps[key] = { tile: tile, box: box });
  }

  function label(text, x, y, colour, weight) {
    var width = widthOf(text, weight);
    if (!claim(x, y, width, 11)) return false;
    var s = stamp(text, weight, colour, width);
    ctx.drawImage(s.tile, x - PAD, y - STAMP_H / 2, s.box, STAMP_H);
    return true;
  }

  // Quanto mais perto, mais nomes. O que um Artifact é chama-se pelo nome em
  // qualquer zoom — inclusive no enquadramento inicial, onde `k` fica abaixo
  // de 1 e um limiar absoluto deixaria a tela sem uma única palavra. Os tipos
  // que só fazem sentido de perto esperam a sua vez; sem escalonar, 2.300
  // rótulos saem juntos e não se lê nenhum.
  var TIER = { Artifact: 0, Collection: 0, EpochMarker: 0,
               Tool: 1.1, Technique: 1.1, Period: 1.1,
               Author: 2.4, Dependency: 2.4 };

  function draw() {
    var w = canvas.clientWidth, h = canvas.clientHeight;
    var cx = w / 2 + view.x, cy = h / 2 + view.y, k = view.k;
    ctx.clearRect(0, 0, w, h);
    resetLabels(w, h);

    var i, n, link;
    for (i = 0; i < nodes.length; i++) {
      n = nodes[i];
      n.sx = cx + k * n.x;
      n.sy = cy + k * n.y;
    }

    // Arestas em duas passadas para que o realce fique por cima do apagado.
    var dim = 1 - 0.82 * focusAmount;
    ctx.lineWidth = 0.7;
    ctx.strokeStyle = pal.EDGE;
    ctx.globalAlpha = dim;
    ctx.beginPath();
    for (i = 0; i < links.length; i++) {
      link = links[i];
      if (link.source.off || link.target.off) continue;
      if (focusAmount > 0.02 && litEdge(link)) continue;
      ctx.moveTo(link.source.sx, link.source.sy);
      ctx.lineTo(link.target.sx, link.target.sy);
    }
    ctx.stroke();

    if (focus) {
      ctx.globalAlpha = 1;
      ctx.lineWidth = 1.4;
      ctx.strokeStyle = focus.colour;
      ctx.beginPath();
      for (i = 0; i < links.length; i++) {
        link = links[i];
        if (link.source.off || link.target.off) continue;
        if (!litEdge(link)) continue;
        ctx.moveTo(link.source.sx, link.source.sy);
        ctx.lineTo(link.target.sx, link.target.sy);
      }
      ctx.stroke();
      // Ponta no destino: uma aresta sem direção deixa metade da frase por
      // dizer, e num grafo de proveniência a metade que falta é qual dos dois
      // veio antes.
      ctx.fillStyle = focus.colour;
      for (i = 0; i < links.length; i++) {
        link = links[i];
        if (link.source.off || link.target.off) continue;
        if (!litEdge(link)) continue;
        var ax = link.target.sx - link.source.sx, ay = link.target.sy - link.source.sy;
        var span = Math.sqrt(ax * ax + ay * ay);
        if (span < 16) continue;
        var ux = ax / span, uy = ay / span;
        var tipX = link.target.sx - ux * (link.target.r + 1.5);
        var tipY = link.target.sy - uy * (link.target.r + 1.5);
        ctx.beginPath();
        ctx.moveTo(tipX, tipY);
        ctx.lineTo(tipX - ux * 7 - uy * 3, tipY - uy * 7 + ux * 3);
        ctx.lineTo(tipX - ux * 7 + uy * 3, tipY - uy * 7 - ux * 3);
        ctx.closePath();
        ctx.fill();
      }
    }

    // Nós, agrupados por cor e por aceso ou apagado. O motor cobra por chamada
    // de desenho, não por círculo: 2.300 chamadas por quadro custam mais que os
    // 2.300 círculos que elas desenham, e a paleta tem menos de dez cores.
    var slot;
    for (i = 0; i < groups.length; i++) if (groups[i]) groups[i].length = 0;
    for (i = 0; i < nodes.length; i++) {
      n = nodes[i];
      if (n.off || n === focus) continue;
      if (n.sx < -20 || n.sy < -20 || n.sx > w + 20 || n.sy > h + 20) continue;
      slot = n.shade * 4 + (n.fork ? 2 : 0) + (lit(n) ? 1 : 0);
      (groups[slot] || (groups[slot] = [])).push(n);
    }
    for (slot = 0; slot < groups.length; slot++) {
      var bucket = groups[slot];
      if (!bucket || !bucket.length) continue;
      ctx.globalAlpha = (slot & 1) ? 1 : dim;
      ctx.fillStyle = shades[slot >> 2];
      ctx.beginPath();
      for (i = 0; i < bucket.length; i++) {
        n = bucket[i];
        // `moveTo` antes de cada arco: sem ele o caminho liga um círculo ao
        // seguinte com uma reta.
        ctx.moveTo(n.sx + n.r, n.sy);
        ctx.arc(n.sx, n.sy, n.r, 0, 6.2832);
      }
      ctx.fill();
      // Um fork intocado sai contornado, e não infla a contagem (ADR-0003).
      if (slot & 2) {
        ctx.strokeStyle = shades[slot >> 2]; ctx.lineWidth = 0.9; ctx.stroke();
      }
    }
    ctx.globalAlpha = 1;
    if (focus) {
      ctx.beginPath();
      ctx.arc(focus.sx, focus.sy, focus.r * 1.6, 0, 6.2832);
      ctx.fillStyle = focus.colour;
      ctx.fill();
      if (focus.fork) {
        ctx.strokeStyle = focus.colour; ctx.lineWidth = 0.9; ctx.stroke();
      }
    }

    // Anel do nó em foco: o alvo do cursor tem que ser inequívoco.
    if (focus) {
      ctx.beginPath();
      ctx.arc(focus.sx, focus.sy, focus.r * 1.6 + 4, 0, 6.2832);
      ctx.strokeStyle = focus.colour;
      ctx.lineWidth = 1.6;
      ctx.stroke();
    }

    // Ordem de disputa pelo espaço: quem é quem antes de qual é a relação.
    // A malha dá a célula ao primeiro que a pede, e uma aresta curta tem o
    // seu meio a poucos pixels do nó — desenhar a relação primeiro rouba
    // exatamente as células do nome, e sobra uma tela de verbos sem sujeito.
    function nameOf(node, weight) {
      var colour = (focus && !lit(node)) ? pal.MUTED : pal.TEXT;
      return label(node.ref.label, node.sx + node.r + 4, node.sy, colour, weight);
    }

    var drawn = 0;
    if (focus) {
      nameOf(focus, 600);
      var edges = incident[focus.ref.id] || [];
      for (i = 0; i < edges.length; i++) {
        link = edges[i];
        var other = link.source === focus ? link.target : link.source;
        if (!other.off && nameOf(other, 500)) drawn++;
      }
      // A relação sai deslocada na perpendicular da aresta, não sobre ela:
      // em cima da linha o texto disputa com os dois nós que ela liga. Ainda
      // assim uma aresta curta não tem onde pôr um rótulo — para essas, quem
      // responde é a ficha, que não depende de geometria nenhuma.
      for (i = 0; i < edges.length && i < 40; i++) {
        link = edges[i];
        if (link.source.off || link.target.off) continue;
        var ex = link.target.sx - link.source.sx, ey = link.target.sy - link.source.sy;
        var span = Math.sqrt(ex * ex + ey * ey);
        if (span < 34) continue;
        var mx = (link.source.sx + link.target.sx) / 2 - (ey / span) * 7;
        var my = (link.source.sy + link.target.sy) / 2 + (ex / span) * 7;
        if (mx < 0 || my < 0 || mx > w || my > h) continue;
        label(link.type, mx + 4, my, pal.MUTED, 500);
      }
    }

    // O resto por prioridade: Artifact antes de tudo, e entre iguais o mais
    // conectado primeiro — é o que orienta quem chegou agora.
    var candidates = [];
    for (i = 0; i < nodes.length; i++) {
      n = nodes[i];
      if (n.off || n === focus) continue;
      if (n.sx < 0 || n.sy < 0 || n.sx > w || n.sy > h) continue;
      if (k < (TIER[n.ref.type] === undefined ? 2.4 : TIER[n.ref.type])) continue;
      candidates.push(n);
    }
    candidates.sort(function (a, b) {
      if ((a.ref.type === "Artifact") !== (b.ref.type === "Artifact")) {
        return a.ref.type === "Artifact" ? -1 : 1;
      }
      return b.degree - a.degree;
    });
    for (i = 0; i < candidates.length && drawn < 200; i++) {
      if (nameOf(candidates[i], 400)) drawn++;
    }
  }

  function frame() {
    if (!settled) { tick(); dirty = true; }
    if (!userMoved && !settled) fitToLayout();
    if (glide) {
      view.x += (glide.x - view.x) * 0.18;
      view.y += (glide.y - view.y) * 0.18;
      view.k += (glide.k - view.k) * 0.18;
      if (Math.abs(glide.x - view.x) < 0.5 && Math.abs(glide.y - view.y) < 0.5
          && Math.abs(glide.k - view.k) < 0.002) {
        view.x = glide.x; view.y = glide.y; view.k = glide.k; glide = null;
      }
      dirty = true;
    }
    // Foco responde em mola criticamente amortecida: sem oscilação, e sempre
    // partindo do valor que está na tela, não do alvo.
    var wanted = focus ? 1 : 0;
    if (focusAmount !== wanted) {
      focusAmount = calm ? wanted : focusAmount + (wanted - focusAmount) * 0.25;
      if (Math.abs(wanted - focusAmount) < 0.01) focusAmount = wanted;
      dirty = true;
    }
    if (dirty) {
      draw();
      dirty = false;
      // A ficha presa segue o nó: sem isto ela fica onde o nó estava antes do
      // arrasto, apontando para o vazio.
      if (selected && chip.classList.contains("pinned")) placeChipOnNode(selected);
    }
    requestAnimationFrame(frame);
  }
  recolour();
  frame();

  // O botão de tema é cromo da página; o módulo só sabe se repintar.
  function retheme() {
    pal = palette();
    COLOUR = pal.COLOUR;
    FORK = pal.FORK;
    recolour();
    buildLegend();
    dirty = true;
  }

  // ---------- ponteiro ----------
  // Pointer Events com captura: o arrasto continua quando o cursor sai do
  // canvas, e o mesmo caminho serve para toque.
  var dragging = false, lastX = 0, lastY = 0;

  function local(e) {
    var rect = canvas.getBoundingClientRect();
    return { x: e.clientX - rect.left, y: e.clientY - rect.top };
  }

  function nodeAt(px, py) {
    var best = null, bestDistance = 196;   // 14px de tolerância, ao quadrado
    for (var i = 0; i < nodes.length; i++) {
      var n = nodes[i];
      if (n.off) continue;
      var dx = n.sx - px, dy = n.sy - py;
      var d2 = dx * dx + dy * dy;
      if (d2 < bestDistance) { bestDistance = d2; best = n; }
    }
    return best;
  }

  // A ficha é montada quando o nó muda e só reposicionada depois. Remontar o
  // DOM a cada `pointermove` — e a cada quadro, agora que ela acompanha um nó
  // preso — é trabalho que ninguém vê.
  var chipNode = null;

  function hideChip() {
    chipNode = null;
    chip.classList.remove("on", "pinned");
  }

  function placeChip(px, py) {
    var box = chip.getBoundingClientRect();
    var x = px + 16, y = py + 16;
    if (x + box.width > window.innerWidth - 8) x = px - box.width - 16;
    if (y + box.height > window.innerHeight - 8) y = py - box.height - 16;
    chip.style.left = Math.max(8, x) + "px";
    chip.style.top = Math.max(8, y) + "px";
    chip.classList.add("on");
  }

  // Ancorada no próprio nó, que é onde o olho está quando a ficha veio de um
  // clique ou de uma busca — o ponteiro pode estar em qualquer canto.
  function placeChipOnNode(n) {
    var rect = canvas.getBoundingClientRect();
    placeChip(rect.left + n.sx, rect.top + n.sy);
  }

  function fillChip(n) {
    chipNode = n;
    var node = n.ref;
    var facts = [];
    if (node.first || node.last) facts.push((node.first || "?") + " → " + (node.last || "?"));
    if (node.artifact_count) facts.push(node.artifact_count + " Artifacts");
    if (g.isBarelyMine(node)) facts.push("fork, barely yours");
    var degree = (incident[node.id] || []).length;
    facts.push(degree + (degree === 1 ? " link" : " links"));
    chip.innerHTML = "";
    function line(className, text) {
      var el = document.createElement("div");
      el.className = className;
      el.textContent = text;
      chip.appendChild(el);
    }
    line("name", node.label);
    line("kind", node.type);
    if (facts.length) line("fact", facts.join(" · "));

    // As relações por extenso. É a leitura que não depende do zoom: numa
    // aresta de vinte pixels nenhum rótulo cabe, e a pergunta "ligado a quê,
    // como" continua de pé.
    var byType = {}, order = [];
    (incident[node.id] || []).forEach(function (link) {
      var outgoing = link.source === n;
      var other = outgoing ? link.target : link.source;
      // A seta é a direção da aresta em relação a este nó. Sem ela,
      // "DEPENDS_ON Melissa-Core" numa Dependency afirma o oposto da verdade:
      // quem depende é o Artifact, não o pacote.
      var key = (outgoing ? "→ " : "← ") + link.type;
      if (!byType[key]) { byType[key] = []; order.push(key); }
      byType[key].push(other.ref.label);
    });
    order.slice(0, 5).forEach(function (type) {
      var names = byType[type];
      var shown = names.slice(0, 3).join(", ");
      if (names.length > 3) shown += " +" + (names.length - 3);
      var row = document.createElement("div");
      row.className = "rel";
      var key = document.createElement("span");
      key.className = "verb";
      key.textContent = type;
      row.appendChild(key);
      row.appendChild(document.createTextNode(shown));
      chip.appendChild(row);
    });
  }

  // Ancorada no ponteiro, virando para dentro quando encosta na borda.
  function showChip(n, px, py) {
    if (n !== chipNode) fillChip(n);
    chip.classList.remove("pinned");
    placeChip(px, py);
  }

  // Um clique é um arrasto que não saiu do lugar. Sem essa distinção, prender
  // um nó ficaria impossível para quem move a mão dois pixels ao apertar.
  var downX = 0, downY = 0;
  canvas.addEventListener("pointerdown", function (e) {
    canvas.setPointerCapture(e.pointerId);
    dragging = true;
    lastX = downX = e.clientX; lastY = downY = e.clientY;
    canvas.classList.add("grabbing");
  });
  canvas.addEventListener("pointerup", function (e) {
    dragging = false;
    canvas.classList.remove("grabbing");
    if (canvas.hasPointerCapture(e.pointerId)) canvas.releasePointerCapture(e.pointerId);
    if (Math.abs(e.clientX - downX) > 4 || Math.abs(e.clientY - downY) > 4) return;
    var p = local(e);
    var hit = nodeAt(p.x, p.y);
    // Clicar no vazio solta: é a saída óbvia, e não exige encontrar um botão.
    select(hit === selected ? null : hit);
    if (selected) placeChipOnNode(selected);
  });
  canvas.addEventListener("pointercancel", function () {
    dragging = false; canvas.classList.remove("grabbing");
  });
  canvas.addEventListener("pointermove", function (e) {
    if (dragging) {
      view.x += e.clientX - lastX;
      view.y += e.clientY - lastY;
      lastX = e.clientX; lastY = e.clientY;
      userMoved = true; dirty = true; glide = null;
      return;
    }
    var p = local(e);
    var hit = nodeAt(p.x, p.y);
    if (hit !== focus) {
      // Sem nó sob o cursor o realce volta para o que está preso, em vez de
      // apagar tudo: a seleção é o estado, o cursor é a visita.
      setFocus(hit || selected);
      dirty = true;
      canvas.classList.toggle("pointing", !!hit);
    }
    if (hit) showChip(hit, e.clientX, e.clientY);
    else if (selected) { fillChip(selected); chip.classList.add("pinned"); }
    else hideChip();
  });
  canvas.addEventListener("pointerleave", function () {
    setFocus(selected);
    canvas.classList.remove("pointing");
    if (selected) { fillChip(selected); chip.classList.add("pinned"); }
    else hideChip();
    dirty = true;
  });

  // Zoom ancorado no cursor: o ponto do grafo sob o ponteiro é o que fica
  // parado. Zoom no centro da tela obriga a pessoa a reencontrar onde estava.
  canvas.addEventListener("wheel", function (e) {
    e.preventDefault();
    var p = local(e);
    var w = canvas.clientWidth, h = canvas.clientHeight;
    var gx = (p.x - w / 2 - view.x) / view.k;
    var gy = (p.y - h / 2 - view.y) / view.k;
    glide = null;
    var next = Math.min(6, Math.max(0.05, view.k * (e.deltaY < 0 ? 1.1 : 0.9)));
    view.k = next;
    view.x = p.x - w / 2 - next * gx;
    view.y = p.y - h / 2 - next * gy;
    userMoved = true; dirty = true;
  }, { passive: false });

  // Sem isto, quem se perde no zoom não tem como voltar ao grafo inteiro. Em
  // cima de um nó a intenção é a oposta — aproximar dele.
  canvas.addEventListener("dblclick", function (e) {
    var p = local(e);
    var hit = nodeAt(p.x, p.y);
    if (hit) { select(hit); centreOn(hit); return; }
    glide = null; userMoved = false; fitToLayout(); dirty = true;
  });

  // ---------- filtros: a legenda já dizia o que cada cor é ----------
  // Um segundo painel de tipos repetiria a legenda inteira. A linha que
  // nomeia o tipo é o lugar óbvio para desligá-lo.
  var legend = el("legend");
  function buildLegend() {
    legend.innerHTML = "";
    Object.keys(COLOUR).forEach(function (type) {
      var total = g.nodesOfType(type).length;
      if (!total) return;
      var row = document.createElement("button");
      row.type = "button";
      row.setAttribute("aria-pressed", hiddenTypes[type] ? "false" : "true");
      // O rótulo lido em voz alta: sem ele o contador cola no nome e sai
      // "Artifact97".
      row.setAttribute("aria-label", type + ", " + total + " nodes");
      var dot = document.createElement("i");
      dot.style.background = COLOUR[type];
      var name = document.createElement("span");
      name.textContent = type;
      var count = document.createElement("span");
      count.className = "count";
      count.textContent = total;
      row.appendChild(dot);
      row.appendChild(name);
      row.appendChild(count);
      row.addEventListener("click", function () {
        if (hiddenTypes[type]) delete hiddenTypes[type];
        else hiddenTypes[type] = true;
        row.setAttribute("aria-pressed", hiddenTypes[type] ? "false" : "true");
        applyFilters();
        if (find.value) search(find.value);
      });
      legend.appendChild(row);
    });
    if (g.artifacts.some(function (a) { return g.isBarelyMine(a); })) {
      // Fork não é um tipo, é uma condição de Artifact: nada para desligar.
      var fork = document.createElement("div");
      fork.className = "fork";
      fork.innerHTML = '<i style="background:' + FORK + '"></i>fork, barely yours';
      legend.appendChild(fork);
    }
    var hint = document.createElement("span");
    hint.className = "hint";
    hint.textContent = "Names appear as you zoom in. Hover a node to read its links, "
      + "click to keep it lit, and press / to search by name. A legend row "
      + "switches its type off.";
    legend.appendChild(hint);
  }

  // ---------- busca ----------
  var find = el("find");
  var results = el("results");
  var matches = [], cursor = -1;
  var SHOWN = 12;

  function search(query) {
    var needle = query.trim().toLowerCase();
    matches = [];
    if (needle) {
      // Quem começa com o que foi digitado vem antes de quem só contém, e
      // entre iguais o mais conectado: é o que se estava procurando.
      var starts = [], contains = [];
      for (var i = 0; i < nodes.length; i++) {
        var n = nodes[i];
        if (n.off) continue;
        var at = n.ref.label.toLowerCase().indexOf(needle);
        if (at === 0) starts.push(n);
        else if (at > 0) contains.push(n);
      }
      function rank(a, b) {
        return b.degree - a.degree || (a.ref.label < b.ref.label ? -1 : 1);
      }
      starts.sort(rank);
      contains.sort(rank);
      matches = starts.concat(contains);
    }
    cursor = matches.length ? 0 : -1;
    renderResults();
  }

  function renderResults() {
    results.innerHTML = "";
    matches.slice(0, SHOWN).forEach(function (n, i) {
      var row = document.createElement("li");
      row.setAttribute("role", "option");
      row.setAttribute("aria-selected", i === cursor ? "true" : "false");
      var dot = document.createElement("i");
      dot.style.background = n.colour;
      var name = document.createElement("span");
      name.textContent = n.ref.label;
      var kind = document.createElement("span");
      kind.className = "kind";
      kind.textContent = n.ref.type;
      row.appendChild(dot);
      row.appendChild(name);
      row.appendChild(kind);
      // `mousedown`, não `click`: o blur do campo fecharia a lista antes de o
      // clique chegar.
      row.addEventListener("mousedown", function (event) {
        event.preventDefault();
        reveal(n);
      });
      results.appendChild(row);
    });
    if (matches.length > SHOWN) {
      var more = document.createElement("li");
      more.className = "more";
      more.textContent = "+" + (matches.length - SHOWN) + " more — keep typing";
      results.appendChild(more);
    }
  }

  function reveal(n) {
    select(n);
    centreOn(n);
    placeChipOnNode(n);
  }

  find.addEventListener("input", function () { search(find.value); });
  find.addEventListener("focus", function () { if (find.value) search(find.value); });
  find.addEventListener("blur", function () { results.innerHTML = ""; });
  find.addEventListener("keydown", function (e) {
    var limit = Math.min(matches.length, SHOWN);
    if ((e.key === "ArrowDown" || e.key === "ArrowUp") && limit) {
      e.preventDefault();
      cursor = (cursor + (e.key === "ArrowDown" ? 1 : limit - 1)) % limit;
      renderResults();
      return;
    }
    if (e.key === "Enter" && cursor >= 0) { e.preventDefault(); reveal(matches[cursor]); return; }
    if (e.key === "Escape") { find.value = ""; search(""); find.blur(); }
  });

  document.addEventListener("keydown", function (e) {
    var active = document.activeElement;
    var typing = active && /^(INPUT|TEXTAREA|SELECT)$/.test(active.tagName);
    if (e.key === "/" && !typing) { e.preventDefault(); find.focus(); find.select(); return; }
    // Escape solta o nó preso, que é a mesma saída do clique no vazio.
    if (e.key === "Escape" && !typing && selected) select(null);
  });

  applyFilters();
  buildLegend();

    return {
      // `suspend` ainda não para o laço: isso é a T010, e fazê-lo aqui seria
      // mudar comportamento numa extração que promete não mudar nenhum.
      activate: function () { dirty = true; },
      suspend: function () {},
      select: function (nodeId) {
        var node = null;
        for (var i = 0; i < nodes.length; i++) {
          if (nodes[i].ref.id === nodeId) { node = nodes[i]; break; }
        }
        select(node);
        if (node) centreOn(node);
      },
      selected: function () { return selected ? selected.ref.id : null; },
      search: function (query) { find.value = query || ""; search(find.value); },
      retheme: retheme
    };
  }

  global.DendroViewGraph = { create: create };
})(window);
