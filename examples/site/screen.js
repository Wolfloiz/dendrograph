/* A casca: uma tela, várias views, uma seleção, um endereço.
 *
 * As views sabem desenhar e mais nada. Elas são informadas do que está
 * selecionado; não decidem, não buscam dado, não conversam entre si. O que
 * sobrevive à troca de vista mora aqui — que é o que faltava quando eram dois
 * documentos que não sabiam um do outro.
 *
 * Contrato: specs/002-usable-by-a-stranger/contracts/screen.md
 */
(function (global) {
  "use strict";

  var g = DendroLoader.load();
  var body = document.body;
  var title = document.getElementById("title");
  var meta = document.getElementById("meta");
  var switcher = document.getElementById("views");

  // Cada view: o id do seu `<section>`, como se chama e quem a constrói. A
  // ordem aqui é a ordem dos botões.
  var VIEWS = [
    { id: "graph", label: "Graph", title: "Knowledge graph",
      factory: global.DendroViewGraph },
    { id: "timeline", label: "Timeline", title: "Archive timeline",
      factory: global.DendroViewTimeline },
    // Sem botão: não é uma vista do arquivo inteiro, é a vista de um assunto.
    // Chega-se a ela por um resultado de busca ou por um nó, nunca por
    // navegação vazia.
    { id: "tool", label: null, title: "Tool", factory: global.DendroViewTool }
  ];

  var live = {};        // id → o punhado que a view devolveu
  var current = null;   // id da view visível
  var selection = null; // id de nó, ou null
  var query = "";

  function section(id) { return document.getElementById("view-" + id); }

  function definition(id) {
    for (var i = 0; i < VIEWS.length; i++) if (VIEWS[i].id === id) return VIEWS[i];
    return null;
  }

  // Construída na primeira vez que é pedida, não no carregamento: o grafo
  // assenta um layout de 3.000 nós, e pagar isso por uma vista que ninguém
  // abriu seria pagar duas vezes pela mesma tela.
  function instance(id) {
    if (live[id]) return live[id];
    var def = definition(id);
    if (!def || !def.factory) return null;
    live[id] = def.factory.create(section(id), g, {
      meta: meta,
      // Um tipo desligado no grafo sai também dos resultados: oferecer um nó
      // que a vista não desenha é oferecer um beco.
      onFilterChange: function () { if (find && find.value) rerun(); },
      onPick: function (nodeId) { selection = nodeId; show(VIEWS[0].id); tell(VIEWS[0].id); }
    });
    return live[id];
  }

  // ---------- endereço ----------
  // O fragmento é a única parte de um endereço `file://` que carrega estado
  // sem virar requisição — e é o que sobrevive a ser colado numa mensagem.
  // Fora dele, de propósito: pan, zoom e a semente do layout. Um endereço
  // compartilhado tem que cair no mesmo assunto, não nos mesmos pixels.
  function parse(hash) {
    var raw = String(hash || "").replace(/^#/, "");
    var q = "";
    var at = raw.indexOf("?");
    if (at >= 0) {
      var search = raw.slice(at + 1);
      raw = raw.slice(0, at);
      var pairs = search.split("&");
      for (var i = 0; i < pairs.length; i++) {
        var pair = pairs[i].split("=");
        if (pair[0] === "q") q = decodeURIComponent((pair[1] || "").replace(/\+/g, " "));
      }
    }
    var slash = raw.indexOf("/");
    var view = slash >= 0 ? raw.slice(0, slash) : raw;
    var subject = slash >= 0 ? decodeURIComponent(raw.slice(slash + 1)) : null;
    return { view: definition(view) ? view : VIEWS[0].id, subject: subject, query: q };
  }

  function serialise() {
    var out = "#" + current;
    if (selection) out += "/" + encodeURIComponent(selection);
    if (query) out += "?q=" + encodeURIComponent(query);
    return out;
  }

  var writing = false;
  function writeAddress() {
    writing = true;
    if (global.location.hash !== serialise()) global.location.hash = serialise();
    // `hashchange` chega depois; o sinalizador só cai quando ele chega ou no
    // próximo quadro, o que vier antes.
    global.setTimeout(function () { writing = false; }, 0);
  }

  // ---------- seleção ----------
  // Uma view que não sabe mostrar o que está selecionado mostra o seu estado
  // normal. A seleção não se perde por não caber numa vista.
  function tell(id) {
    var view = live[id];
    if (!view) return;
    if (view.select) view.select(selection);
    if (query && view.search) view.search(query);
  }

  function setSelection(nodeId, from) {
    selection = nodeId || null;
    for (var id in live) if (live.hasOwnProperty(id) && id !== from) tell(id);
    writeAddress();
  }

  // ---------- troca de vista ----------
  function show(id, options) {
    options = options || {};
    if (!definition(id)) id = VIEWS[0].id;
    if (current === id && live[id]) return;

    var previous = current;
    if (previous && live[previous] && live[previous].suspend) live[previous].suspend();
    if (previous) section(previous).hidden = true;

    current = id;
    body.setAttribute("data-view", id);
    title.textContent = definition(id).title;
    document.title = definition(id).title + " — dendrograph";
    section(id).hidden = false;

    var view = instance(id);
    tell(id);
    if (view && view.activate) view.activate();

    var buttons = switcher.querySelectorAll("button");
    for (var i = 0; i < buttons.length; i++) {
      var on = buttons[i].getAttribute("data-view") === id;
      if (on) buttons[i].setAttribute("aria-current", "page");
      else buttons[i].removeAttribute("aria-current");
    }
    if (!options.silent) writeAddress();
  }

  VIEWS.forEach(function (def) {
    if (!def.label) return;
    var button = document.createElement("button");
    button.type = "button";
    button.textContent = def.label;
    button.setAttribute("data-view", def.id);
    button.addEventListener("click", function () { show(def.id); });
    switcher.appendChild(button);
  });

  global.addEventListener("hashchange", function () {
    if (writing) return;
    var route = parse(global.location.hash);
    query = route.query;
    selection = route.subject;
    show(route.view, { silent: true });
    tell(route.view);
  });

  // O que a casca oferece às views e a quem vier depois — a busca da US2
  // seleciona por aqui em vez de conhecer as views uma a uma.
  global.DendroScreen = {
    graph: g,
    views: VIEWS.map(function (d) { return d.id; }),
    show: show,
    current: function () { return current; },
    select: setSelection,
    selected: function () { return selection; },
    setQuery: function (text) { query = text || ""; writeAddress(); },
    query: function () { return query; },
    instance: instance
  };

  // ---------- busca compartilhada (US2) ----------
  // O índice mora na casca, não em nenhuma view. O visitante busca uma vez
  // e o resultado aparece em qualquer vista que saiba mostrar o assunto.
  var searchIndex = DendroSearch.create(g);
  var find = document.getElementById("find");
  var resultsEl = document.getElementById("results");
  var matches = [], cursor = -1;
  var SHOWN = 12;

  function renderResults() {
    resultsEl.innerHTML = "";
    matches.slice(0, SHOWN).forEach(function (m, i) {
      var row = document.createElement("li");
      row.setAttribute("role", "option");
      row.setAttribute("aria-selected", i === cursor ? "true" : "false");
      var dot = document.createElement("i");
      dot.style.background = m.colour;
      var name = document.createElement("span");
      name.textContent = m.label;
      var kind = document.createElement("span");
      kind.className = "kind";
      kind.textContent = m.type;
      row.appendChild(dot);
      row.appendChild(name);
      row.appendChild(kind);
      if (m.snippet) {
        var snip = document.createElement("span");
        snip.className = "snip";
        snip.textContent = m.snippet;
        row.appendChild(snip);
      }
      // `mousedown`, não `click`: o blur do campo fecharia a lista antes
      // de o clique chegar.
      row.addEventListener("mousedown", function (event) {
        event.preventDefault();
        selectResult(m);
      });
      resultsEl.appendChild(row);
    });
    if (matches.length > SHOWN) {
      var more = document.createElement("li");
      more.className = "more";
      more.textContent = "+" + (matches.length - SHOWN) + " more \u2014 keep typing";
      resultsEl.appendChild(more);
    }
  }

  function selectResult(m) {
    // Uma Tool tem uma vista própria e é onde a pergunta dela se responde.
    if (m.type === "Tool") {
      selection = m.id;
      show("tool");
      tell("tool");
    } else {
      if (current === "tool") show(VIEWS[0].id);
      setSelection(m.id);
    }
    find.value = "";
    query = "";
    matches = [];
    cursor = -1;
    renderResults();
    writeAddress();
  }

  function rerun() {
    var needle = find.value.trim();
    matches = needle ? searchIndex.search(needle) : [];
    cursor = matches.length ? 0 : -1;
    renderResults();
  }

  find.addEventListener("input", function () {
    rerun();
    // Atualiza a query na tela para que views que queiram reagir saibam.
    query = find.value;
  });
  find.addEventListener("focus", function () {
    if (find.value) {
      matches = searchIndex.search(find.value);
      cursor = matches.length ? 0 : -1;
      renderResults();
    }
  });
  find.addEventListener("blur", function () { resultsEl.innerHTML = ""; });
  find.addEventListener("keydown", function (e) {
    var limit = Math.min(matches.length, SHOWN);
    if ((e.key === "ArrowDown" || e.key === "ArrowUp") && limit) {
      e.preventDefault();
      cursor = (cursor + (e.key === "ArrowDown" ? 1 : limit - 1)) % limit;
      renderResults();
      return;
    }
    if (e.key === "Enter" && cursor >= 0) {
      e.preventDefault();
      selectResult(matches[cursor]);
      return;
    }
    if (e.key === "Escape") {
      find.value = "";
      matches = [];
      cursor = -1;
      renderResults();
      find.blur();
    }
  });

  // `/` abre a busca de qualquer lugar — atalho que o grafo já oferecia e
  // que agora é da casca.
  document.addEventListener("keydown", function (e) {
    var active = document.activeElement;
    var typing = active && /^(INPUT|TEXTAREA|SELECT)$/.test(active.tagName);
    if (e.key === "/" && !typing) {
      e.preventDefault();
      find.focus();
      find.select();
    }
  });

  document.getElementById("theme").onclick = function () {
    DendroTheme.toggle();
    for (var id in live) {
      if (live.hasOwnProperty(id) && live[id].retheme) live[id].retheme();
    }
  };

  var initial = parse(global.location.hash);
  query = initial.query;
  selection = initial.subject;
  show(initial.view, { silent: true });
  writeAddress();
})(window);
