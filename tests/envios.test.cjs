const {test} = require("node:test");
const assert = require("node:assert/strict");
const {calcularResumo, inicializarEnvio} = require("../static/js/envios.js");
const {formatarMoeda} = require("../static/js/formatacao.js");

function campo(props = {}) {
  return Object.assign(new EventTarget(), {
    value: "", checked: false, hidden: false, dataset: {}, textContent: "",
    setCustomValidity(message) { this.validationMessage = message; },
  }, props);
}

function formulario(bound = false) {
  const caixas = [campo({checked: true, dataset: {valor: "100.10"}}),
    campo({checked: true, dataset: {valor: "200.20"}}),
    campo({checked: false, dataset: {valor: "90.00"}})];
  const elementos = {};
  for (const id of ["selecionar-todas", "id_valor_taxa", "id_justificativa_taxa",
    "justificativa-taxa", "subtotal-selecionado", "total-selecionado", "conferir-lote"]) {
    elementos[id] = campo();
  }
  elementos["preparar-lote"] = {
    dataset: {percentual: "10.5000", bound: String(bound)},
    querySelectorAll() { return caixas; },
  };
  return {caixas, elementos, documento: {getElementById(id) { return elementos[id]; }}};
}

test("taxa usa todas as despesas, HALF_UP e precisão além de Number", () => {
  assert.deepEqual(calcularResumo(["100.10", "200.20"], "10.5000"), {despesas: 30030n, taxa: 3153n});
  assert.equal(calcularResumo(["0.05"], "10").taxa, 1n);
  assert.deepEqual(calcularResumo([], "10"), {despesas: 0n, taxa: 0n});
  assert.equal(calcularResumo(["99999999999999.99", "0.01"], "10").taxa, 1000000000000000n);
});

test("alterar taxa exige justificativa; mudar flags recalcula e limpa o ajuste", () => {
  const {documento, caixas, elementos} = formulario();
  inicializarEnvio(documento, formatarMoeda);
  const taxa = elementos.id_valor_taxa;
  const motivo = elementos.id_justificativa_taxa;
  assert.equal(taxa.value, "31,53");
  assert.equal(elementos["justificativa-taxa"].hidden, true);
  taxa.value = "30,00";
  taxa.dispatchEvent(new Event("input"));
  assert.equal(elementos["justificativa-taxa"].hidden, false);
  assert.equal(motivo.required, true);
  assert.ok(motivo.validationMessage);
  motivo.value = "Desconto aprovado";
  motivo.dispatchEvent(new Event("input"));
  assert.equal(motivo.validationMessage, "");
  caixas[0].checked = false;
  caixas[0].dispatchEvent(new Event("change"));
  assert.equal(taxa.value, "21,02");
  assert.equal(motivo.value, "");
  assert.equal(motivo.required, false);
  assert.equal(elementos["justificativa-taxa"].hidden, true);
  assert.equal(elementos["total-selecionado"].textContent, formatarMoeda("221.22"));
  caixas[0].checked = true;
  caixas[0].dispatchEvent(new Event("change"));
  assert.equal(taxa.value, "31,53");
});

test("selecionar e desmarcar todas atualiza taxa, total e disponibilidade", () => {
  const {documento, elementos} = formulario();
  inicializarEnvio(documento, formatarMoeda);
  const todas = elementos["selecionar-todas"];
  assert.equal(todas.indeterminate, true);
  todas.checked = false;
  todas.dispatchEvent(new Event("change"));
  assert.equal(elementos.id_valor_taxa.value, "0,00");
  assert.equal(elementos["conferir-lote"].disabled, true);
  todas.checked = true;
  todas.dispatchEvent(new Event("change"));
  assert.equal(elementos.id_valor_taxa.value, "40,98");
  assert.equal(elementos["conferir-lote"].disabled, false);
  assert.equal(todas.indeterminate, false);
});

test("erro do servidor preserva ajuste e motivo até a próxima mudança de seleção", () => {
  const {documento, elementos} = formulario(true);
  elementos.id_valor_taxa.value = "25,00";
  elementos.id_justificativa_taxa.value = "Ajuste revisado";
  inicializarEnvio(documento, formatarMoeda);
  assert.equal(elementos.id_valor_taxa.value, "25,00");
  assert.equal(elementos.id_justificativa_taxa.value, "Ajuste revisado");
  assert.equal(elementos["justificativa-taxa"].hidden, false);
});
