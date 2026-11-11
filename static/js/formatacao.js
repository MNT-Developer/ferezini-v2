"use strict";
(() => {
  const integers = new Intl.NumberFormat("pt-BR", {maximumFractionDigits: 0});

  function decimalParts(value) {
    const match = /^(-?)(\d+)(?:\.(\d+))?$/.exec(String(value ?? "0"));
    if (!match) throw new TypeError("Valor decimal inválido.");
    return {negative: match[1] === "-", whole: match[2], fraction: match[3] || ""};
  }

  function formatarMoeda(value) {
    const parts = decimalParts(value || "0");
    const fraction = parts.fraction.padEnd(3, "0");
    let cents = BigInt(parts.whole) * 100n + BigInt(fraction.slice(0, 2));
    if (fraction[2] >= "5") cents += 1n;
    const sign = parts.negative && cents !== 0n ? "-" : "";
    return `${sign}R$ ${integers.format(cents / 100n)},${String(cents % 100n).padStart(2, "0")}`;
  }

  function compararDecimais(first, second) {
    const a = decimalParts(first || "0"), b = decimalParts(second || "0");
    const scale = Math.max(a.fraction.length, b.fraction.length);
    const aValue = BigInt(`${a.negative ? "-" : ""}${a.whole}${a.fraction.padEnd(scale, "0")}`);
    const bValue = BigInt(`${b.negative ? "-" : ""}${b.whole}${b.fraction.padEnd(scale, "0")}`);
    return aValue < bValue ? -1 : aValue > bValue ? 1 : 0;
  }

  const exports = {formatarMoeda, compararDecimais};
  if (typeof module !== "undefined" && module.exports) module.exports = exports;
  else globalThis.FereziniFormatacao = exports;
})();
