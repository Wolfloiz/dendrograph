/* O índice de busca da página, sobre o payload que já está na memória.
 *
 * ┌─ Interface, para quem hospeda ───────────────────────────────────────────┐
 * │                                                                          │
 * │   var index = DendroSearch.create(g);   // g é o objeto do loader.js      │
 * │   var rows  = index.query("melissa");   // ou index.query(text, limit)    │
 * │                                                                          │
 * │   rows[i] = {                                                            │
 * │     id:      "root-c1a3…",   // id do nó, para selecionar numa view       │
 * │     label:   "Melissa-Core", // como o nó se chama                        │
 * │     type:    "Artifact",     // Artifact | Tool | Technique               │
 * │     node:     <o nó do payload>,                                          │
 * │     matched: "name" | "description",   // por que esta linha veio         │
 * │     excerpt: "…trecho…",     // só quando matched === "description"       │
 * │     degree:   14,            // arestas tocando o nó, o critério de       │
 * │     colour:  "#8ab4f8"       //   desempate; cor do tipo, ou null         │
 * │   }                                                                      │
 * │                                                                          │
 * │   index.size  // quantas entradas o índice tem                            │
 * │                                                                          │
 * │ `reason` e `snippet` são apelidos de `matched` e `excerpt`, para a shell  │
 * │ que já os consome. Um dos dois pares sai quando a shell escolher.         │
 * └──────────────────────────────────────────────────────────────────────────┘
 *
 * Busca nomes de Artifact, Tool e Technique, e descrições de Artifact — o que
 * o contrato lista, e nada além. Author e Dependency ficam de fora: são 2.348
 * dos 2.433 nós do site publicado, são identificadores e não prosa, e o rótulo
 * de um Author é a parte local de um endereço de e-mail (ADR-0012).
 *
 * A ordem é mecânica e explicável em uma frase: quanto mais perto do começo do
 * nome está o acerto, mais alto ele fica, e entre iguais vem primeiro o nó com
 * mais arestas. Grau é volume de menção, não qualidade — nada aqui julga qual
 * Artifact importa mais (Princípio I, Princípio V).
 *
 * Nada neste arquivo conta o que não está no payload. Um Artifact retido não
 * está aqui, um Tool cujos Artifacts foram todos retidos também não, e não
 * existe caminho que devolva "3 resultados, 1 oculto" — essa linha contaria ao
 * visitante que existe trabalho privado casando com aquela palavra
 * (FR-009, Princípio IV, ADR-0005).
 *
 * Contrato: specs/002-usable-by-a-stranger/contracts/search.md
 */
(function (global) {
  "use strict";

  // Tipos buscáveis, e quais deles têm prosa a buscar.
  var SEARCHABLE = { Artifact: true, Tool: true, Technique: true };

  // Camadas de acerto, em ordem. O número é a posição na lista, não uma nota.
  var STARTS_NAME = 0;   // o nome começa com o que foi digitado
  var STARTS_WORD = 1;   // uma palavra dentro do nome começa com ele
  var IN_NAME = 2;       // o nome contém em algum lugar
  var IN_DESCRIPTION = 3; // a descrição de um Artifact contém

  var COLOUR = null;

  /* A cor do tipo, lida dos mesmos tokens CSS que as outras views usam.
   *
   * Protegida porque o índice também roda fora de uma página pintada — a
   * medição de latência não monta estilo nenhum — e uma busca que estoura
   * porque não achou uma variável de tema seria um defeito onde não há tema.
   */
  function colour(type) {
    if (COLOUR === null) {
      COLOUR = {};
      try {
        var css = getComputedStyle(document.documentElement);
        var names = {
          Artifact: "--c-artifact", Tool: "--c-tool", Technique: "--c-technique",
          Period: "--c-period", Collection: "--c-collection", Author: "--c-author",
          Dependency: "--c-dependency", EpochMarker: "--c-marker"
        };
        for (var key in names) {
          if (Object.prototype.hasOwnProperty.call(names, key)) {
            COLOUR[key] = css.getPropertyValue(names[key]).trim();
          }
        }
      } catch (e) {
        COLOUR = {};
      }
    }
    return COLOUR[type] || null;
  }

  /* Minúsculas e sem acento, dos dois lados.
   *
   * O tokenizador unicode61 do FTS5 remove diacríticos por padrão, então é
   * assim que o CLI já se comporta; dobrar aqui também é o que mantém as duas
   * superfícies respondendo à mesma palavra. `normalize` não é biblioteca — é
   * método de String, e a guarda cobre onde não houver.
   */
  function fold(text) {
    var lowered = (text || "").toLowerCase();
    if (typeof lowered.normalize !== "function") return lowered;
    return lowered.normalize("NFD").replace(/[\u0300-\u036f]/g, "");
  }

  // Grau: quantas arestas tocam o nó. É o desempate do contrato — "o mais
  // conectado primeiro" — e é contagem, não julgamento.
  function degree(g, id) {
    return (g.outgoing[id] || []).length + (g.incoming[id] || []).length;
  }

  // Uma palavra do nome começa com a agulha? Fronteira é qualquer coisa que
  // não seja letra ou dígito: `pxt-melissa` responde a `melissa`.
  function wordStarts(haystack, needle) {
    var at = haystack.indexOf(needle);
    while (at > 0) {
      if (!/[0-9a-z]/.test(haystack.charAt(at - 1))) return true;
      at = haystack.indexOf(needle, at + 1);
    }
    return false;
  }

  // Trecho da descrição em volta do acerto, recortado do texto original: o
  // visitante lê a prosa como ela foi escrita, não em caixa baixa.
  function excerptAround(description, folded, needle) {
    var at = folded.indexOf(needle);
    if (at < 0) return "";
    var start = Math.max(0, at - 30);
    var end = Math.min(description.length, at + needle.length + 40);
    var text = description.slice(start, end);
    if (start > 0) text = "…" + text;
    if (end < description.length) text = text + "…";
    return text;
  }

  function create(g) {
    // O índice é montado uma vez. Por busca sobram comparações de string
    // sobre esta lista — 71 entradas no site publicado, 120 no build cheio —
    // e é por isso que a tecla não espera nada (SC-005).
    var entries = [];
    var nodes = g.nodes;
    for (var i = 0; i < nodes.length; i++) {
      var node = nodes[i];
      if (!SEARCHABLE[node.type]) continue;
      entries.push({
        node: node,
        type: node.type,
        label: node.label || "",
        name: fold(node.label),
        // Descrição só existe em Artifact, e só quando o build a publicou:
        // um Artifact sob alias entra sem prosa nenhuma (ADR-0011).
        description: node.description || "",
        prose: node.type === "Artifact" ? fold(node.description) : "",
        degree: degree(g, node.id)
      });
    }

    function query(text, limit) {
      var needle = fold(text).replace(/^\s+|\s+$/g, "");
      if (!needle) return [];

      var found = [];
      for (var i = 0; i < entries.length; i++) {
        var e = entries[i];
        var tier = -1;
        var matched = "name";

        if (e.name.indexOf(needle) === 0) {
          tier = STARTS_NAME;
        } else if (wordStarts(e.name, needle)) {
          tier = STARTS_WORD;
        } else if (e.name.indexOf(needle) > 0) {
          tier = IN_NAME;
        } else if (e.prose && e.prose.indexOf(needle) >= 0) {
          tier = IN_DESCRIPTION;
          matched = "description";
        }
        if (tier < 0) continue;

        var excerpt = matched === "description"
          ? excerptAround(e.description, e.prose, needle)
          : "";
        found.push({
          id: e.node.id,
          label: e.label,
          type: e.type,
          node: e.node,
          matched: matched,
          excerpt: excerpt,
          degree: e.degree,
          colour: colour(e.type),
          tier: tier,
          // Apelidos para a shell; ver o cabeçalho.
          reason: matched,
          snippet: excerpt || null
        });
      }

      found.sort(function (a, b) {
        return a.tier - b.tier
          || b.degree - a.degree
          || (a.label < b.label ? -1 : a.label > b.label ? 1 : 0);
      });
      return typeof limit === "number" && limit >= 0 ? found.slice(0, limit) : found;
    }

    return {
      query: query,
      // `search` é o nome que a shell em construção chama. Mesmo retorno.
      search: query,
      size: entries.length,
      entries: entries
    };
  }

  global.DendroSearch = { create: create };
})(window);
