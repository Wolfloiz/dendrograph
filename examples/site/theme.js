// Alternância de tema claro/escuro, compartilhada pelas duas views.
//
// Sem CDN, sem dependência: o tema é um atributo na raiz; o padrão segue o
// prefers-color-scheme do sistema e a escolha manual é persistida em
// localStorage, com acento para `file://`, onde o storage pode não existir.
(function (global) {
  "use strict";

  var KEY = "dendro-theme";

  function stored() {
    try { return global.localStorage.getItem(KEY); } catch (e) { return null; }
  }

  function current() {
    var storedValue = stored();
    if (storedValue === "light" || storedValue === "dark") return storedValue;
    return global.matchMedia && matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark" : "light";
  }

  function apply(theme) {
    document.documentElement.setAttribute("data-theme", theme);
  }

  function toggle() {
    var next = current() === "dark" ? "light" : "dark";
    try { global.localStorage.setItem(KEY, next); } catch (e) {}
    apply(next);
    return next;
  }

  apply(current());
  global.DendroTheme = { apply: apply, toggle: toggle, current: current };
})(window);
