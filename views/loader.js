// The one place either view reads data from.
//
// A browser blocks fetch() from a file:// page under CORS, so graph.js hands us
// a global instead. Both views go through this layer rather than being two
// standalone pages: v0.2 puts them behind one screen, and a second copy of this
// logic is what would make that expensive.
(function (global) {
  "use strict";

  function load() {
    var graph = global.DENDROGRAPH_GRAPH;
    if (!graph) {
      throw new Error("graph.js did not load — open this page from a built site/ directory");
    }
    return decorate(graph);
  }

  function decorate(graph) {
    var byId = {};
    graph.nodes.forEach(function (node) { byId[node.id] = node; });

    var outgoing = {};
    var incoming = {};
    graph.edges.forEach(function (edge) {
      (outgoing[edge.from] = outgoing[edge.from] || []).push(edge);
      (incoming[edge.to] = incoming[edge.to] || []).push(edge);
    });

    function nodesOfType(type) {
      return graph.nodes.filter(function (n) { return n.type === type; });
    }

    function neighbours(id, type) {
      return (outgoing[id] || [])
        .filter(function (e) { return !type || e.type === type; })
        .map(function (e) { return byId[e.to]; })
        .filter(Boolean);
    }

    // Um fork intocado tem share perto de zero. É o que distingue "isto é meu"
    // de "isto está no meu arquivo" sem inflar a contagem (ADR-0003).
    function authorshipShare(node) {
      return node.authorship && typeof node.authorship.share === "number"
        ? node.authorship.share
        : null;
    }

    function isBarelyMine(node) {
      var share = authorshipShare(node);
      return share !== null && share < 0.1;
    }

    return {
      raw: graph,
      mode: graph.build_mode,
      generatedAt: graph.generated_at,
      nodes: graph.nodes,
      edges: graph.edges,
      byId: byId,
      outgoing: outgoing,
      incoming: incoming,
      nodesOfType: nodesOfType,
      neighbours: neighbours,
      artifacts: nodesOfType("Artifact"),
      tools: nodesOfType("Tool"),
      periods: nodesOfType("Period"),
      epochMarkers: nodesOfType("EpochMarker"),
      aggregates: graph.aggregates || null,
      unreachable: graph.unreachable_sources || [],
      authorshipShare: authorshipShare,
      isBarelyMine: isBarelyMine
    };
  }

  global.DendroLoader = { load: load, decorate: decorate };
})(window);
