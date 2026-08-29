/* O perfil de uma Tool: desde quando, em quê, e o que não conta.
 *
 * É a pergunta do currículo — a SC-007 da v0.1, *dizer anos de experiência sem
 * estimar de memória* — navegável em vez de calculada. O que a v0.1 já
 * publicava e ninguém renderizava: `indexes.tool_to_artifacts`.
 *
 * A obrigação desta vista é o contrário de afirmar: ela existe para dizer o que
 * *não* pode ser reivindicado. Um span sem datas não vira intervalo vazio, e um
 * span não atribuído não vira o span do Author.
 */
(function (global) {
  "use strict";

  function create(root, g, options) {
    options = options || {};
    var host = root.querySelector("#tool");
    var subject = null;

    var byId = {};
    g.nodes.forEach(function (node) { byId[node.id] = node; });
    var indexes = (g.raw && g.raw.indexes) || {};
    var index = indexes.tool_to_artifacts || {};
    var untouchedIndex = indexes.tool_to_untouched || {};

    function line(parent, className, text) {
      var el = document.createElement("div");
      el.className = className;
      el.textContent = text;
      parent.appendChild(el);
      return el;
    }

    // A lista vem do mesmo cálculo que produziu o span. Derivá-la de
    // `authorship.share` foi a primeira tentativa e a conta não fechou: são
    // duas perguntas diferentes — quanto material é do Author, e se ele
    // commitou. Marcar linhas por uma e contá-las pela outra dava um perfil com
    // treze linhas sob um título dizendo doze.
    function untouchedFor(toolId) {
      var ids = untouchedIndex[toolId] || [];
      var set = {};
      for (var i = 0; i < ids.length; i++) set[ids[i]] = true;
      return set;
    }

    function years(tool) {
      if (!tool.first || !tool.last) return null;
      var from = new Date(tool.first), to = new Date(tool.last);
      var span = (to - from) / (365.25 * 24 * 3600 * 1000);
      return span < 1 ? "under a year" : span.toFixed(1) + " years";
    }

    function render() {
      host.innerHTML = "";
      var tool = subject ? byId[subject] : null;

      // Um assunto que não existe e um assunto retido renderizam igual. Saber
      // distinguir os dois é a própria divulgação (ADR-0005).
      if (!tool || tool.type !== "Tool") {
        line(host, "empty", subject
          ? "No Tool by that name in this archive."
          : "Pick a Tool from a search result, or from a node in the graph.");
        return;
      }

      var head = document.createElement("div");
      head.className = "toolhead";
      host.appendChild(head);
      line(head, "name", tool.label);

      var claimed = tool.artifact_count || 0;
      var spare = tool.untouched_count || 0;

      if (!tool.first || !claimed) {
        // Nunca um intervalo vazio: "não reivindica nada" é uma frase, e um
        // traço entre dois vazios é um defeito com cara de dado.
        line(head, "claim none", spare
          ? "Claims no dates — every Artifact using it is a fork the Author never committed to."
          : "Claims no dates.");
      } else if (tool.attributed === false) {
        line(head, "claim loose",
          tool.first + " to " + tool.last + " — observed activity, not attributed to the "
          + "Author. No emails are configured, so there is no “mine” to measure.");
      } else {
        line(head, "claim",
          tool.first + " to " + tool.last + (years(tool) ? " · " + years(tool) : ""));
      }

      var members = (index[tool.id] || []).map(function (id) { return byId[id]; })
        .filter(Boolean);
      var spare_ids = untouchedFor(tool.id);
      var mine = members.filter(function (a) { return !spare_ids[a.id]; });
      var forks = members.filter(function (a) { return !!spare_ids[a.id]; });

      line(host, "count",
        claimed + (claimed === 1 ? " Artifact" : " Artifacts") + " behind the span"
        + (spare ? ", and " + spare + " more that contribute no dates" : ""));

      list("Artifacts that count", mine, false);
      if (forks.length) {
        list("Used, but contributes no dates", forks, true);
      }
    }

    function list(heading, members, faint) {
      if (!members.length) return;
      var section = document.createElement("div");
      section.className = "toolgroup" + (faint ? " faint" : "");
      host.appendChild(section);
      line(section, "grouphead", heading);
      members.sort(function (a, b) {
        return (a.first || "9999") < (b.first || "9999") ? -1 : 1;
      }).forEach(function (artifact) {
        var row = document.createElement("button");
        row.type = "button";
        row.className = "toolrow";
        row.setAttribute("data-id", artifact.id);
        var name = document.createElement("span");
        name.className = "lbl";
        name.textContent = artifact.label;
        var when = document.createElement("span");
        when.className = "when";
        when.textContent = artifact.first
          ? artifact.first.slice(0, 4) + (artifact.last ? "–" + artifact.last.slice(0, 4) : "")
          : "no dates";
        row.appendChild(name);
        row.appendChild(when);
        row.addEventListener("click", function () {
          if (options.onPick) options.onPick(artifact.id);
        });
        section.appendChild(row);
      });
    }

    render();

    return {
      activate: function () { render(); },
      suspend: function () {},
      select: function (nodeId) { subject = nodeId || null; render(); },
      selected: function () { return subject; },
      search: function () {},
      retheme: function () { render(); }
    };
  }

  global.DendroViewTool = { create: create };
})(window);
