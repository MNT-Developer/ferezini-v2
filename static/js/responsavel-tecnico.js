"use strict";
(() => {
  function inicializarResponsavel(documento, carregar = globalThis.fetch) {
    const seletor = documento.getElementById("responsavel-selector");
    const dialog = documento.getElementById("responsavel-dialog");
    if (!seletor || !dialog) return;
    const campo = documento.getElementById("id_responsavel_tecnico");
    const codigo = documento.getElementById("responsavel-codigo");
    const nome = documento.getElementById("responsavel-nome");
    const pesquisa = documento.getElementById("responsavel-search");
    const resultados = documento.getElementById("responsavel-results");
    const status = documento.getElementById("responsavel-status");
    let requisicao = null, sequencia = 0, agendamento = null;

    function cancelarBusca() {
      clearTimeout(agendamento);
      requisicao?.abort();
      sequencia += 1;
    }

    function selecionar(colaborador) {
      campo.value = colaborador ? String(colaborador.id) : "";
      codigo.value = campo.value;
      nome.value = colaborador ? colaborador.primeiro_nome : "";
      dialog.close();
    }

    async function buscar() {
      cancelarBusca();
      const atual = sequencia;
      requisicao = new AbortController();
      resultados.replaceChildren();
      resultados.setAttribute("aria-busy", "true");
      status.textContent = "Buscando colaboradores…";
      try {
        const resposta = await carregar(`${seletor.dataset.url}?q=${encodeURIComponent(pesquisa.value.trim())}`, {
          headers: {Accept: "application/json"}, credentials: "same-origin", signal: requisicao.signal,
        });
        if (!resposta.ok) throw new Error("Falha ao buscar colaboradores.");
        const dados = await resposta.json();
        if (atual !== sequencia) return;
        for (const colaborador of dados.colaboradores) {
          const linha = documento.createElement("tr");
          const id = documento.createElement("td");
          const celula = documento.createElement("td");
          const botao = documento.createElement("button");
          linha.className = "responsavel-row";
          id.textContent = String(colaborador.id);
          botao.type = "button";
          botao.className = "responsavel-option";
          botao.textContent = colaborador.nome;
          linha.addEventListener("click", () => selecionar(colaborador));
          celula.append(botao);
          linha.append(id, celula);
          resultados.append(linha);
        }
        status.textContent = dados.colaboradores.length
          ? (dados.limitado ? "Até 10 primeiros colaboradores em ordem alfabética. Pesquise para ver todos os resultados." : `${dados.colaboradores.length} colaborador(es) encontrado(s).`)
          : "Nenhum colaborador encontrado.";
      } catch (erro) {
        if (atual !== sequencia || erro.name === "AbortError") return;
        resultados.replaceChildren();
        status.textContent = "Não foi possível carregar os colaboradores. Tente buscar novamente.";
      } finally {
        if (atual === sequencia) resultados.removeAttribute("aria-busy");
      }
    }

    function abrir() {
      if (dialog.open) return;
      pesquisa.value = "";
      dialog.showModal();
      buscar();
    }
    for (const input of [codigo, nome]) {
      input.addEventListener("click", abrir);
      input.addEventListener("keydown", evento => {
        if (evento.key === "Enter" || evento.key === " ") {
          evento.preventDefault();
          abrir();
        }
      });
    }
    pesquisa.addEventListener("input", () => {
      cancelarBusca();
      resultados.replaceChildren();
      status.textContent = "Buscando colaboradores…";
      agendamento = setTimeout(buscar, 250);
    });
    documento.getElementById("responsavel-search-form").addEventListener("submit", evento => {
      evento.preventDefault();
      buscar();
    });
    documento.getElementById("responsavel-clear").addEventListener("click", () => selecionar(null));
    documento.getElementById("responsavel-close").addEventListener("click", () => dialog.close());
    dialog.addEventListener("close", cancelarBusca);
  }

  if (typeof module !== "undefined" && module.exports) module.exports = {inicializarResponsavel};
  else inicializarResponsavel(document);
})();
