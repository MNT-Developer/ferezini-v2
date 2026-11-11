"use strict";
(() => {
  function unidades(valor, casas, localizado = false) {
    let texto = String(valor).trim();
    if (localizado && texto.includes(",")) {
      if (!/^(?:\d+|\d{1,3}(?:\.\d{3})+),\d{1,2}$/.test(texto)) throw new TypeError("Valor inválido.");
      texto = texto.replaceAll(".", "").replace(",", ".");
    }
    const partes = /^(\d+)(?:\.(\d+))?$/.exec(texto);
    if (!partes || (partes[2] || "").length > casas) throw new TypeError("Valor inválido.");
    return BigInt(partes[1] + (partes[2] || "").padEnd(casas, "0"));
  }

  function decimalCentavos(centavos) {
    return `${centavos / 100n}.${String(centavos % 100n).padStart(2, "0")}`;
  }

  function calcularResumo(valores, percentual) {
    const despesas = valores.reduce((total, valor) => total + unidades(valor, 2), 0n);
    // Percentual tem quatro casas: centavos × percentual / (100 × 10.000).
    const taxa = (despesas * unidades(percentual, 4) + 500000n) / 1000000n;
    return {despesas, taxa};
  }

  function inicializarEnvio(documento, formatarMoeda) {
    const form = documento.getElementById("preparar-lote");
    if (!form) return;
    const caixas = [...form.querySelectorAll('input[name="despesas"]')];
    const todas = documento.getElementById("selecionar-todas");
    const taxa = documento.getElementById("id_valor_taxa");
    const justificativa = documento.getElementById("id_justificativa_taxa");
    const campoJustificativa = documento.getElementById("justificativa-taxa");
    const subtotal = documento.getElementById("subtotal-selecionado");
    const total = documento.getElementById("total-selecionado");
    const confirmar = documento.getElementById("conferir-lote");
    let resumo;
    taxa.required = true;

    function atualizarTaxa() {
      let valor;
      try {
        valor = unidades(taxa.value, 2, true);
        taxa.setCustomValidity("");
      } catch {
        taxa.setCustomValidity("Informe uma taxa válida, não negativa, com até duas casas decimais.");
      }
      const alterada = valor !== undefined && valor !== resumo.taxa;
      campoJustificativa.hidden = !alterada;
      justificativa.required = alterada;
      if (!alterada) justificativa.value = "";
      justificativa.setCustomValidity(alterada && !justificativa.value.trim() ? "Justifique a alteração do valor da taxa." : "");
      total.textContent = valor === undefined ? "—" : formatarMoeda(decimalCentavos(resumo.despesas + valor));
    }

    function recalcular(limparAjuste = true) {
      const selecionadas = caixas.filter(caixa => caixa.checked);
      resumo = calcularResumo(selecionadas.map(caixa => caixa.dataset.valor), form.dataset.percentual);
      subtotal.textContent = formatarMoeda(decimalCentavos(resumo.despesas));
      todas.checked = caixas.length > 0 && selecionadas.length === caixas.length;
      todas.indeterminate = selecionadas.length > 0 && selecionadas.length < caixas.length;
      confirmar.disabled = selecionadas.length === 0;
      if (limparAjuste) {
        taxa.value = decimalCentavos(resumo.taxa).replace(".", ",");
        justificativa.value = "";
      }
      atualizarTaxa();
    }

    caixas.forEach(caixa => caixa.addEventListener("change", () => recalcular()));
    todas.addEventListener("change", () => {
      caixas.forEach(caixa => { caixa.checked = todas.checked; });
      recalcular();
    });
    taxa.addEventListener("input", atualizarTaxa);
    justificativa.addEventListener("input", atualizarTaxa);
    recalcular(form.dataset.bound !== "true" || !taxa.value.trim());
  }

  if (typeof module !== "undefined" && module.exports) {
    module.exports = {calcularResumo, inicializarEnvio};
  } else {
    inicializarEnvio(document, globalThis.FereziniFormatacao.formatarMoeda);
  }
})();
