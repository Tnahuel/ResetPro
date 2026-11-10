// Copia el texto de cada <th> como data-label en las celdas de su columna,
// para que en celular cada fila se muestre como tarjeta con su etiqueta.
// Se re-aplica solo cuando admin.js / valoraciones.js vuelven a dibujar filas.
(function () {
  function etiquetar(tabla) {
    var heads = Array.prototype.map.call(
      tabla.querySelectorAll("thead th"),
      function (th) { return th.textContent.trim(); }
    );
    Array.prototype.forEach.call(tabla.querySelectorAll("tbody tr"), function (tr) {
      Array.prototype.forEach.call(tr.children, function (td, i) {
        if (td.hasAttribute("colspan") || td.classList.contains("who-cell")) return;
        if (heads[i] && td.getAttribute("data-label") !== heads[i]) td.setAttribute("data-label", heads[i]);
      });
    });
  }
  function iniciar() {
    Array.prototype.forEach.call(document.querySelectorAll(".table-wrap table"), function (tabla) {
      etiquetar(tabla);
      var tbody = tabla.querySelector("tbody");
      if (tbody) new MutationObserver(function () { etiquetar(tabla); }).observe(tbody, { childList: true });
    });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", iniciar);
  else iniciar();
})();
