/* A view da linha do tempo, fora da página que a hospeda.
 *
 * Mesma forma de fábrica do `view-graph.js`, e o mesmo motivo para o prefixo no
 * nome: `views/graph.js` seria sobrescrito pelo arquivo de dados que o build
 * escreve antes de copiar as views.
 *
 * Esta view não tem laço de animação nem canvas — `activate` e `suspend`
 * existem para que quem hospeda trate as duas do mesmo jeito, não porque ela
 * precise de algo.
 */
(function (global) {
  "use strict";

  function create(root, g, options) {
    options = options || {};
    function el(id) { return root.querySelector("#" + id); }

    var LBL = 0; // definido abaixo


    // ---- meta e cartões de resumo ----
    var artifacts = g.artifacts;
    var span = artifacts.reduce(function (acc, a) {
    if (a.first) acc.min = acc.min < a.first ? acc.min : a.first;
    if (a.last) acc.max = acc.max > a.last ? acc.max : a.last;
    return acc;
    }, { min: "\uffff", max: "" });
    var toolsTouched = g.tools.filter(function (t) { return t.artifact_count; }).length;
    if (options.meta) {
    options.meta.textContent =
      artifacts.length + " Artifacts · built " + g.generatedAt + " · mode: " + g.mode;
    }
    el("tiles").innerHTML = [
    [artifacts.length, "Artifacts"],
    [toolsTouched + "/" + g.tools.length, "Tools touched"],
    [(span.min !== "\uffff" ? span.min.slice(0, 4) + "–" + span.max.slice(0, 4) : "—"), "Period"],
    [g.epochMarkers.length || "—", "Epoch markers"],
    ].map(function (t) {
    return '<div class="tile"><span class="v">' + t[0] + '</span><span class="k">' + t[1] + "</span></div>";
    }).join("");

    // ---- avisos ----
    var notices = el("notices");
    function notice(text) {
    var el = document.createElement("p");
    el.className = "notice";
    el.textContent = text;
    notices.appendChild(el);
    }
    if (g.aggregates && g.aggregates.private_withheld) {
    var w = g.aggregates.private_withheld;
    notice(w.count + " private Artifact(s) withheld from this site. Their shape only: " +
           (w.tools || []).join(", ") + " · " + w.first + "–" + w.last);
    }
    g.unreachable.forEach(function (source) {
    notice("Not reached this build: " + (source.locator || source.kind) +
           (source.last_seen ? " (last seen " + source.last_seen + ")" : ""));
    });

    // ---- eixo temporal (meses, como no pôster) ----
    function month(date) {
    var p = date.split("-");
    return Number(p[0]) * 12 + (Number(p[1] || 1) - 1);
    }
    var m0 = Infinity, m1 = -Infinity;
    artifacts.forEach(function (a) {
    if (!a.first) return;
    m0 = Math.min(m0, month(a.first));
    m1 = Math.max(m1, month(a.last || a.first));
    });
    g.epochMarkers.forEach(function (m) {
    if (m.date) { m0 = Math.min(m0, month(m.date)); m1 = Math.max(m1, month(m.date)); }
    });
    if (!isFinite(m0)) { m0 = month(g.generatedAt.slice(0, 10)); m1 = m0 + 11; }
    // Domínio encostado em anos inteiros: cada rótulo cai numa linha da malha.
    // "Malha" e não o sinônimo com cinco letras: a varredura de julgamento
    // procura essa palavra em inglês e não distingue idioma
    // (tests/test_no_judgement.py).
    var t0 = Math.floor(m0 / 12) * 12;
    var t1 = (Math.floor(m1 / 12) + 1) * 12;
    function pos(m) { return (m - t0) / (t1 - t0) * 100; }

    var y0 = Math.floor(t0 / 12), y1 = Math.floor((t1 - 1) / 12);
    LBL = y1 - y0 > 12 ? 230 : 200;
    document.documentElement.style.setProperty("--lbl", LBL + "px");
    document.documentElement.style.setProperty("--step", (100 / (y1 - y0 + 1)) + "%");

    var axis = el("axis");
    var html = "";
    for (var y = y0; y <= y1; y++) {
    html += '<span style="left:' + pos(y * 12) + '%">' + y + "</span>";
    }
    axis.innerHTML = html;

    // ---- agrupamento: Collections quando existem, senão um grupo só ----
    var collections = g.nodesOfType("Collection");
    var groups = collections.map(function (c) {
    return {
      node: c,
      members: [],
      memberIds: (g.incoming[c.id] || [])
        .filter(function (e) { return e.type === "IN_COLLECTION"; })
        .map(function (e) { return e.from; })
    };
  });
  var grouped = {};
  groups.forEach(function (gr) { gr.memberIds.forEach(function (id) { grouped[id] = gr; }); });
  var rest = { node: { label: "Everything else", id: "_rest" }, members: [], memberIds: [] };

  var aById = g.byId;
  artifacts.forEach(function (a) { (grouped[a.id] || rest).members.push(a); });
  aById = null;

  // ---- filtros ----
  var active = {};
  var controls = el("controls");
  var filterDefs = groups.filter(function (gr) { return gr.members.length; })
    .map(function (gr) {
      return { id: gr.node.id, label: gr.node.label, colour: "var(--accent)" };
    });
  filterDefs.push({ id: "_forks", label: "forks", colour: "var(--fork)" });
  filterDefs.forEach(function (f) { active[f.id] = true; });

  function isVisible(a) {
    if (g.isBarelyMine(a) && !active._forks) return false;
    var gr = grouped[a.id];
    if (gr && !active[gr.node.id]) return false;
    return true;
  }

  filterDefs.forEach(function (f) {
    var chip = document.createElement("button");
    chip.className = "chipf";
    chip.setAttribute("aria-pressed", "true");
    chip.innerHTML = '<span class="sw" style="background:' + f.colour + '"></span>' + f.label;
    chip.onclick = function () {
      active[f.id] = !active[f.id];
      chip.setAttribute("aria-pressed", active[f.id]);
      render();
    };
    controls.appendChild(chip);
  });

  // ---- marcadores de época: linhas verticais sobre o painel inteiro ----
  var lanes = el("lanes");
  var markerHtml = "";
  g.epochMarkers.slice().sort(function (a, b) {
    return (a.date || "").localeCompare(b.date || "");
  }).forEach(function (m) {
    if (!m.date) return;
    markerHtml += '<div class="markerline" style="left: calc(var(--lbl) + (100% - var(--lbl)) * ' +
      (pos(month(m.date)) / 100) + ')"><i>' + m.date + " — " + m.label + "</i></div>";
  });

  // ---- tooltip ----
  var tip = el("tip");
  function showTip(a, ev) {
    var share = g.authorshipShare(a);
    var mline = g.epochMarkers.filter(function (m) { return m.date; })
      .sort(function (x, y) { return x.date.localeCompare(y.date); })
      .map(function (m) {
        if (!a.first) return null;
        if (a.last && a.last < m.date) return "before “" + m.label + "”";
        if (a.first > m.date) return "after “" + m.label + "”";
        return "spans “" + m.label + "”";
      }).filter(Boolean).join(" · ");
    tip.innerHTML =
      "<h4>" + escapeHtml(a.label) + (a.aliased ? " · aliased" : "") + "</h4>" +
      '<div class="m">' + (a.first || "?") + " → " + (a.last || a.first || "?") + "</div>" +
      (share !== null ? '<div class="m">' + Math.round(share * 100) + "% authored by you</div>" : "") +
      (mline ? '<div class="m">' + escapeHtml(mline) + "</div>" : "") +
      (a.aliased ? '<div class="d">Published under an alias — the node and its dates only.</div>' : "");
    tip.style.opacity = 1;
    var r = tip.getBoundingClientRect();
    tip.style.left = Math.min(ev.clientX + 14, innerWidth - r.width - 12) + "px";
    tip.style.top = Math.min(ev.clientY + 14, innerHeight - r.height - 12) + "px";
  }
  function hideTip() { tip.style.opacity = 0; }
  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  // ---- render das lanes ----
  function groupSection(gr) {
    var visible = gr.members.filter(isVisible);
    if (!visible.length) return "";
    var out = '<div class="grouphead">' + escapeHtml(gr.node.label) +
      ' <span class="ct">' + visible.length + " Artifacts</span></div>";
    visible.sort(function (a, b) {
      return (a.first || "").localeCompare(b.first || "");
    }).forEach(function (a) {
      var fork = g.isBarelyMine(a);
      var cls = "row" + (fork ? " fork" : "") + (a.aliased ? " aliased" : "");
      var mark = "";
      if (a.first) {
        var x = pos(month(a.first));
        var x2 = pos(month(a.last || a.first) + 1);
        var period = (a.first.slice(0, 7) === (a.last || "").slice(0, 7) || !a.last);
        if (period) {
          mark = '<span class="lane-mark dot" style="left:' + x + '%"></span>';
        } else {
          mark = '<span class="lane-mark bar" style="left:' + x + "%;width:" + Math.max(x2 - x, 0.4) + '%"></span>';
        }
      }
      out += '<div class="' + cls + '" data-id="' + escapeHtml(a.id) + '">' +
        '<div class="lbl" title="' + escapeHtml(a.label) + '">' + escapeHtml(a.label) + "</div>" +
        '<div class="track">' + mark + "</div></div>";
    });
    return out;
  }

  // O que o grafo selecionou aparece aqui: a seleção é da casca, não da vista,
  // e trocar de vista não pode custar o lugar onde a pessoa estava.
  var chosen = null;

  function markChosen() {
    var rows = lanes.querySelectorAll(".row.chosen");
    for (var i = 0; i < rows.length; i++) rows[i].classList.remove("chosen");
    if (!chosen) return null;
    var row = lanes.querySelector('.row[data-id="' + chosen.replace(/"/g, '\\"') + '"]');
    if (row) row.classList.add("chosen");
    return row;
  }

  function render() {
    var out = groups.map(groupSection).join("") + groupSection(rest);
    lanes.innerHTML = markerHtml + out;
    markChosen();
    var shown = artifacts.filter(isVisible).length;
    el("note").textContent =
      "Each bar runs from the first to the last observed date. " + shown + " of " + artifacts.length +
      " Artifacts visible. Hover a row for detail.";
  }

  lanes.addEventListener("mousemove", function (e) {
    var row = e.target.closest(".row");
    if (!row) return hideTip();
    var a = g.byId[row.dataset.id];
    if (a) showTip(a, e);
  });
  lanes.addEventListener("mouseleave", hideTip);

  render();

  // ---- tabela de Tools ----
  var body = document.querySelector("#tools tbody");
  g.tools.slice().sort(function (a, b) {
    return (a.first || "\uffff").localeCompare(b.first || "\uffff");
  }).forEach(function (tool) {
    var tr = document.createElement("tr");
    var years = (tool.first && tool.last)
      ? (((new Date(tool.last) - new Date(tool.first)) / 31557600000).toFixed(1))
      : "—";
    var basis = tool.attributed === false
      ? "observed, not yours"
      : (tool.untouched_count ? "+" + tool.untouched_count + " untouched" : "yours");
    if (tool.attributed !== false && !tool.artifact_count) basis = "forks only";
    [tool.label, tool.first || "—", tool.last || "—", years, tool.artifact_count || 0, basis]
      .forEach(function (value, i) {
        var td = document.createElement("td");
        if (i > 0 && i < 4) td.className = "span";
        if (i === 4) td.className = "n";
        if (i === 5) td.className = "basis";
        td.textContent = value;
        tr.appendChild(td);
      });
    body.appendChild(tr);

    var contributors = (g.raw.indexes && g.raw.indexes.tool_to_artifacts &&
      g.raw.indexes.tool_to_artifacts[tool.id]) || [];
    if (!contributors.length) return;
    tr.className = "expandable";
    tr.title = "Show the Artifacts behind this span";
    var detail = document.createElement("tr");
    detail.className = "detail";
    detail.hidden = true;
    var cell = document.createElement("td");
    cell.colSpan = 6;
    contributors.forEach(function (id) {
      var artifact = g.byId[id];
      if (!artifact) return;
      var chip = document.createElement("span");
      chip.className = "atchip";
      chip.textContent = artifact.label + (artifact.first ? " (" + artifact.first.slice(0, 4) + ")" : "");
      chip.title = g.isBarelyMine(artifact)
        ? "a fork you barely touched — contributes no dates to this span"
        : "contributes to this span";
      cell.appendChild(chip);
    });
    detail.appendChild(cell);
    body.appendChild(detail);
    tr.addEventListener("click", function () { detail.hidden = !detail.hidden; });
  });

    return {
      activate: function () { markChosen(); },
      suspend: function () {},
      select: function (nodeId) {
        chosen = nodeId || null;
        // Um Artifact selecionado no grafo tem uma linha aqui; uma Tool não.
        // A vista mostra o seu estado normal nesse caso — a seleção não se
        // perde por não caber nela.
        var row = markChosen();
        if (row && row.scrollIntoView) {
          row.scrollIntoView({ block: "center", behavior: "auto" });
        }
      },
      selected: function () { return chosen; },
      search: function () {},
      retheme: function () {}
    };
  }

  global.DendroViewTimeline = { create: create };
})(window);
