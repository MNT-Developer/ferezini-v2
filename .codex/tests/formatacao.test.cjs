const {test} = require("node:test");
const assert = require("node:assert/strict");
const {formatarMoeda, compararDecimais} = require("../../static/js/formatacao.js");

test("valores financeiros preservam centavos além da precisão de Number", () => {
  assert.equal(formatarMoeda("99999999999999.99"), "R$ 99.999.999.999.999,99");
  assert.equal(formatarMoeda("123456789012345678901.01"), "R$ 123.456.789.012.345.678.901,01");
  assert.equal(formatarMoeda("-1500.05"), "-R$ 1.500,05");
  assert.equal(formatarMoeda("0.00"), "R$ 0,00");
});

test("exibição monetária usa arredondamento decimal de meio centavo", () => {
  assert.equal(formatarMoeda("1.005"), "R$ 1,01");
  assert.equal(formatarMoeda("-1.005"), "-R$ 1,01");
  assert.equal(formatarMoeda("0.0049"), "R$ 0,00");
});

test("ordenação numérica distingue centavos e escalas sem alterar valores", () => {
  assert.equal(compararDecimais("99999999999999.98", "99999999999999.99"), -1);
  assert.equal(compararDecimais("10.0000", "10"), 0);
  assert.equal(compararDecimais("100", "9.99"), 1);
  assert.equal(compararDecimais("-2.01", "-2.00"), -1);
});
