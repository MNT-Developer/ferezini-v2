"use strict";
(() => {
  const sheet = document.getElementById("project-sheet");
  if (!sheet) return;
  let data = JSON.parse(document.getElementById("projeto-dados").textContent);
  let tab = new URLSearchParams(location.search).get("aba") === "orcamento" ? "orcamento" : "geral";
  let operations = Promise.resolve();
  const content = document.getElementById("sheet-content");
  const status = document.getElementById("save-status");
  const inactive = document.getElementById("show-inactive");
  const filters = new Map();
  let sort = { field: "fornecedor", direction: 0 };
  const expanded = new Map();
  const {formatarMoeda, compararDecimais} = globalThis.FereziniFormatacao;
  const decimal = new Intl.NumberFormat("pt-BR", {maximumFractionDigits: 4});
  const collator = new Intl.Collator("pt-BR", {sensitivity: "base", numeric: true});
  const expenseFields = [
    ["fornecedor", "Fornecedor", "text"], ["descricao", "Descrição", "text"],
    ["cpf_cnpj_fornecedor", "CPF / CNPJ", "text"], ["numero_nf", "NF", "text"],
    ["data_nf", "Data NF", "date"], ["valor", "Valor", "number"],
    ["observacao", "Observação", "text"]
  ];

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function button(text, className, action) {
    const node = element("button", className, text);
    node.type = "button";
    node.addEventListener("click", event => { event.preventDefault(); event.stopPropagation(); action(); });
    return node;
  }

  function currency(value) { return formatarMoeda(value); }
  function record(type, id) {
    for (const stage of data.etapas) {
      if (type === "etapa" && stage.id === Number(id)) return stage;
      for (const item of stage.itens) {
        if (type === "orcamento" && item.id === Number(id)) return item;
        if (type === "despesa") {
          const found = item.despesas.find(expense => expense.id === Number(id));
          if (found) return found;
        }
      }
      if (type === "despesa") {
        const found = stage.despesas.find(expense => expense.id === Number(id));
        if (found) return found;
      }
    }
    return null;
  }

  function announce(message, error = false) {
    status.textContent = message;
    status.classList.toggle("negative", error);
  }

  function errorText(value) {
    if (typeof value === "string") return value;
    if (Array.isArray(value)) return value.map(errorText).join(" ");
    if (value && typeof value === "object") return Object.entries(value).map(([key, val]) => `${key}: ${errorText(val)}`).join(" ");
    return "Não foi possível concluir a operação.";
  }

  async function api(path, method = "GET", body) {
    const token = document.querySelector('input[name="csrfmiddlewaretoken"]')?.value;
    let response;
    try {
      response = await fetch(`${sheet.dataset.base}${path}${path.includes("?") ? "&" : "?"}inativos=${inactive.checked ? "1" : "0"}`, {
        method, credentials: "same-origin", headers: {"Accept": "application/json", "Content-Type": "application/json", "X-CSRFToken": token || ""},
        body: body === undefined ? undefined : JSON.stringify(body)
      });
    } catch {
      throw new Error("Falha de conexão. Tente novamente ou reverta a edição.");
    }
    const type = response.headers.get("content-type") || "";
    const result = type.includes("application/json") ? await response.json() : {};
    if (!response.ok) {
      const message = errorText(result.erro || result.errors || result.error || result) || "Não foi possível concluir a operação. Tente novamente.";
      const error = new Error(response.status === 403 ? "Você não tem permissão para esta ação ou sua sessão expirou." : message);
      error.conflict = response.status === 409;
      error.requiresReason = result.exige_justificativa === true;
      throw error;
    }
    if (!type.includes("application/json")) throw new Error("A sessão expirou ou o servidor retornou uma resposta inesperada. Recarregue a página.");
    return result;
  }

  function enqueue(action) {
    const task = operations.then(action);
    operations = task.catch(() => {});
    return task;
  }

  function needsResolution() {
    return Boolean(content.querySelector(".sheet-input.dirty, .sheet-input.invalid, .sheet-input.saving"));
  }

  async function beforeRender() {
    await operations;
    if (needsResolution()) {
      window.fereziniToast("Conclua ou reverta as células pendentes antes de continuar.", true);
      return false;
    }
    return true;
  }

  function updateTotals() {
    for (const node of document.querySelectorAll("[data-total]")) {
      const value = data.totais[node.dataset.total];
      node.textContent = node.dataset.total === "execucao" ? `${decimal.format(Number(value || 0))}%` : currency(value);
      node.classList.toggle("negative", node.dataset.total === "saldo" && Number(value) < 0);
    }
    for (const node of content.querySelectorAll("[data-subtotal]")) {
      const obj = record(node.dataset.type, node.dataset.id);
      if (obj) {
        node.textContent = currency(obj[node.dataset.subtotal]);
        node.classList.toggle("negative", node.dataset.subtotal === "saldo" && Number(obj.saldo) < 0);
      }
    }
    for (const node of content.querySelectorAll("[data-record-state]")) {
      const obj = record(node.dataset.type, node.dataset.id);
      if (obj) renderState(node, obj);
    }
  }

  function renderState(node, obj) {
    node.replaceChildren();
    if (!obj.ativo) node.append(element("span", "badge", "Inativo"));
    else if (obj.rascunho) node.append(element("span", "draft-badge", "Rascunho"));
    else if (obj.lote_envio) node.append(element("span", "sent-badge", `Lote #${obj.lote_envio}`));
    else node.append(element("span", "badge", "Completo"));
  }

  function stateCell(obj, type) {
    const cell = element("td", "state-cell");
    cell.dataset.recordState = "1"; cell.dataset.id = obj.id; cell.dataset.type = type;
    renderState(cell, obj);
    return cell;
  }

  function showReason(title, description, required = true) {
    const dialog = document.getElementById("reason-dialog");
    document.getElementById("reason-title").textContent = title;
    document.getElementById("reason-description").textContent = description;
    const input = document.getElementById("reason-input");
    input.value = ""; input.required = required;
    return new Promise(resolve => {
      dialog.addEventListener("close", () => resolve(dialog.returnValue === "confirm" ? input.value.trim() : null), {once: true});
      dialog.returnValue = "";
      dialog.showModal();
      input.focus();
    });
  }

  function clearCellError(input) {
    input.classList.remove("invalid");
    input.removeAttribute("aria-invalid");
    input.parentElement.querySelector(".cell-error")?.remove();
  }

  function cellError(input, error, type, id, field) {
    clearCellError(input);
    input.classList.add("invalid");
    input.setAttribute("aria-invalid", "true");
    const box = element("div", "cell-error");
    box.append(element("span", "", error.message));
    if (error.conflict) box.append(button("Recarregar", "", () => location.reload()));
    else box.append(button("Tentar novamente", "", () => saveCell(input, type, id, field)));
    box.append(button("Reverter", "", () => {
      input.value = input.dataset.confirmed;
      input.classList.remove("dirty", "saving");
      clearCellError(input);
      announce("Edição revertida para o último valor confirmado.");
    }));
    input.parentElement.append(box);
    announce("Há uma célula com erro. Sua edição foi preservada.", true);
  }

  function editableCell(obj, type, field, label, inputType = "text", disabled = false) {
    const cell = element("td", field === "fornecedor" ? "supplier-cell" : field === "descricao" ? "description-cell" : "");
    const input = element("input", "sheet-input");
    input.type = inputType;
    input.value = obj[field] ?? "";
    input.dataset.confirmed = input.value;
    input.dataset.type = type; input.dataset.id = obj.id; input.dataset.field = field;
    input.setAttribute("aria-label", `${label}, ${type === "despesa" ? "despesa" : type === "etapa" ? "etapa" : "item"} ${obj.id}`);
    input.disabled = disabled || !obj.ativo;
    input.autocomplete = "off";
    if (inputType === "number") { input.min = "0"; input.step = field === "quantidade" ? "0.0001" : "0.01"; }
    if (inputType === "text") {
      const limits = {unidade: 30, cpf_cnpj_fornecedor: 18, numero_nf: 100, fornecedor: 200, titulo: 200};
      input.maxLength = field === "descricao" && type !== "etapa" ? 250 : limits[field] || 10000;
    }
    input.addEventListener("input", () => {
      input.classList.toggle("dirty", input.value !== input.dataset.confirmed);
      announce("Editando…");
    });
    input.addEventListener("blur", () => saveCell(input, type, obj.id, field));
    input.addEventListener("keydown", event => {
      if (event.key === "Enter") { event.preventDefault(); input.blur(); }
      if (event.key === "Escape") {
        input.value = input.dataset.confirmed;
        input.classList.remove("dirty"); clearCellError(input); input.blur();
      }
    });
    cell.append(input);
    return cell;
  }

  function saveCell(input, type, id, field) {
    if (input.disabled || input.classList.contains("saving") || input.value === input.dataset.confirmed) return;
    const sentValue = input.value;
    input.classList.add("saving");
    return enqueue(async () => {
      const obj = record(type, id);
      if (!obj) return;
      let reason = "";
      if (obj.exige_justificativa || (type === "despesa" && obj.lote_envio)) {
        reason = await showReason("Justificar alteração", "Este registro possui histórico financeiro. Explique o motivo da alteração.");
        if (reason === null) {
          input.value = input.dataset.confirmed;
          input.classList.remove("dirty", "saving"); clearCellError(input);
          announce("Alteração cancelada."); return;
        }
      }
      announce("Salvando…");
      clearCellError(input);
      try {
        const result = await api(`linhas/${type}/${id}/`, "PATCH", {campo: field, valor: sentValue, versao: obj.versao, justificativa: reason});
        data = result.dados;
        const canonical = (result.registro || record(type, id))[field] ?? "";
        input.dataset.confirmed = String(canonical);
        if (input.value === sentValue) input.value = String(canonical);
        input.classList.toggle("dirty", input.value !== String(canonical));
        updateTotals();
        announce(content.querySelector(".sheet-input.dirty, .sheet-input.invalid") ? "Célula salva. Há outras edições pendentes." : "Salvo.");
      } catch (error) {
        if (error.requiresReason) obj.exige_justificativa = true;
        cellError(input, error, type, id, field);
      }
      finally {
        input.classList.remove("saving");
        if (!input.classList.contains("invalid") && input.value !== input.dataset.confirmed && document.activeElement !== input) saveCell(input, type, id, field);
      }
    });
  }

  async function mutate(path, body) {
    if (!await beforeRender()) return;
    sheet.inert = true;
    announce("Salvando…");
    try {
      const result = await enqueue(() => api(path, "POST", body));
      data = result.dados;
      render(); announce("Salvo.");
      return result;
    } catch (error) {
      window.fereziniToast(error.message, true); announce(error.message, true);
    } finally { sheet.inert = false; }
  }

  async function changeState(type, obj) {
    if (!await beforeRender()) return;
    const reactivating = !obj.ativo;
    const required = reactivating || type !== "orcamento" || obj.exige_justificativa;
    const reason = await showReason(reactivating ? "Reativar registro" : "Inativar registro", reactivating ? "Registre a observação para reativar este registro." : "O registro e seu histórico serão preservados. Informe o motivo da inativação.", required);
    if (reason === null) return;
    await mutate(`linhas/${type}/${obj.id}/estado/`, {ativo: reactivating, versao: obj.versao, justificativa: reason});
  }

  function historyLink(type, id) {
    const link = element("a", "", "Histórico");
    link.href = `${sheet.dataset.history}?tipo=${type}&id=${id}`;
    link.addEventListener("click", event => event.stopPropagation());
    return link;
  }

  function actionsFor(type, obj, parentActive = true) {
    const actions = element("div", "row-actions");
    actions.append(historyLink(type, obj.id));
    if (parentActive) actions.append(button(obj.ativo ? "Inativar" : "Reativar", obj.ativo ? "danger" : "", () => changeState(type, obj)));
    return actions;
  }

  function subtotalNode(type, obj, field) {
    const node = element("strong", Number(obj[field]) < 0 ? "negative" : "", currency(obj[field]));
    node.dataset.subtotal = field; node.dataset.type = type; node.dataset.id = obj.id;
    return node;
  }

  function groupTotals(type, obj, fields = ["orcado", "realizado", "saldo"]) {
    const node = element("div", "group-totals");
    const labels = {orcado: "Orçado", realizado: "Realizado", saldo: "Saldo"};
    for (const field of fields) {
      const item = element("span");
      item.append(element("small", "", labels[field]), subtotalNode(type, obj, field));
      node.append(item);
    }
    return node;
  }

  function trackedDetails(key, className) {
    const details = element("details", className);
    details.open = expanded.has(key) ? expanded.get(key) : true;
    details.addEventListener("toggle", () => expanded.set(key, details.open));
    return details;
  }

  function expenseTable(expenses, stage) {
    const wrap = element("div", "table-wrap");
    const table = element("table", "table expense-table");
    const thead = element("thead"); const header = element("tr");
    for (const [field, label] of expenseFields) {
      const th = element("th");
      const sortButton = button(label, "sort-button", () => {
        sort = sort.field === field ? {field, direction: (sort.direction + 1) % 3} : {field, direction: 1};
        applyExpenseView();
      });
      sortButton.dataset.sortField = field;
      sortButton.setAttribute("aria-label", `Ordenar despesas por ${label}`);
      const mark = element("span", "sort-mark"); mark.setAttribute("aria-hidden", "true"); sortButton.append(mark);
      const filterButton = button("⌕", "column-filter", () => openFilter(field, label));
      filterButton.dataset.filterField = field; filterButton.setAttribute("aria-label", `Filtrar por ${label}`);
      th.append(sortButton, filterButton); header.append(th);
    }
    header.append(element("th", "", "Situação"), element("th", "", "Ações"));
    thead.append(header); table.append(thead);
    const body = element("tbody"); body.dataset.expenseGroup = "1";
    for (const expense of expenses) {
      const tr = element("tr", expense.ativo ? "" : "row-inactive");
      tr.dataset.expenseId = expense.id;
      for (const [field, label, inputType] of expenseFields) tr.append(editableCell(expense, "despesa", field, label, inputType, !stage.ativo));
      tr.append(stateCell(expense, "despesa"));
      const td = element("td"); td.append(actionsFor("despesa", expense, stage.ativo)); tr.append(td);
      body.append(tr);
    }
    if (!expenses.length) { const tr = element("tr"); const td = element("td", "muted", "Nenhuma despesa neste agrupamento."); td.colSpan = 9; tr.append(td); body.append(tr); }
    table.append(body); wrap.append(table); return wrap;
  }

  function addExpense(stage, item) {
    const node = element("div", "add-expense");
    if (stage.ativo && (!item || item.ativo)) node.append(button("+ Adicionar despesa", "btn btn-quiet btn-sm", async () => {
      const result = await mutate("linhas/", {tipo: "despesa", etapa: stage.id, orcamento: item ? item.id : null});
      if (result?.registro) content.querySelector(`input[data-type="despesa"][data-id="${result.registro.id}"][data-field="fornecedor"]`)?.focus();
    }));
    return node;
  }

  function generalStage(stage) {
    const group = trackedDetails(`etapa-${stage.id}`, `group${stage.ativo ? "" : " inactive"}`);
    const summary = element("summary");
    summary.append(element("span", "group-title", stage.titulo), element("span", "group-subtitle", `${stage.itens.filter(item => item.ativo).length} itens`));
    if (!stage.ativo) summary.append(element("span", "badge", "Etapa inativa"));
    summary.append(groupTotals("etapa", stage)); group.append(summary);
    const inner = element("div", "group-inner");
    for (const item of stage.itens) {
      const section = trackedDetails(`item-${item.id}`, `item-section${item.ativo ? "" : " row-inactive"}`);
      const heading = element("summary");
      heading.append(element("span", "group-title", item.descricao || "Item sem descrição"));
      if (item.rascunho) heading.append(element("span", "draft-badge", "Rascunho"));
      if (!item.ativo) heading.append(element("span", "badge", "Inativo"));
      heading.append(groupTotals("orcamento", item));
      section.append(heading, expenseTable(item.despesas, stage), addExpense(stage, item));
      inner.append(section);
    }
    const general = trackedDetails(`geral-${stage.id}`, "item-section");
    const heading = element("summary");
    heading.append(element("span", "group-title", "Área geral da etapa"), element("span", "group-subtitle", "Despesas sem item ativo"));
    general.append(heading, expenseTable(stage.despesas, stage), addExpense(stage)); inner.append(general);
    group.append(inner); return group;
  }

  function draggable(node, type, id, parentId) {
    node.draggable = true; node.dataset.orderType = type; node.dataset.orderId = id; node.dataset.orderParent = parentId;
    node.addEventListener("dragstart", event => {
      if (needsResolution() || event.target.closest?.("input,button,a")) { event.preventDefault(); return; }
      event.stopPropagation();
      event.dataTransfer.setData("application/ferezini-order", JSON.stringify({type, id, parentId}));
      event.dataTransfer.effectAllowed = "move";
      node.classList.add("dragging");
    });
    node.addEventListener("dragend", () => { node.classList.remove("dragging"); content.querySelectorAll(".drag-over").forEach(el => el.classList.remove("drag-over")); });
    node.addEventListener("dragover", event => { event.preventDefault(); event.stopPropagation(); node.classList.add("drag-over"); });
    node.addEventListener("dragleave", () => node.classList.remove("drag-over"));
    node.addEventListener("drop", async event => {
      event.preventDefault(); event.stopPropagation(); node.classList.remove("drag-over");
      let source;
      try { source = JSON.parse(event.dataTransfer.getData("application/ferezini-order")); } catch { return; }
      if (source.type !== type || source.parentId !== parentId || source.id === id) return;
      const ids = [...node.parentElement.children].filter(child => child.dataset.orderType === type).map(child => Number(child.dataset.orderId));
      ids.splice(ids.indexOf(source.id), 1); ids.splice(ids.indexOf(id), 0, source.id);
      await mutate("ordem/", {tipo: type, etapa: type === "orcamento" ? parentId : undefined, ids});
    });
  }

  function budgetStage(stage) {
    const group = trackedDetails(`orcamento-etapa-${stage.id}`, `group${stage.ativo ? "" : " inactive"}`);
    draggable(group, "etapa", stage.id, data.projeto.id);
    const summary = element("summary");
    const handle = element("span", "drag-handle", "⠿"); handle.title = "Arraste para reorganizar etapa";
    summary.append(handle);
    const titleInputCell = editableCell(stage, "etapa", "titulo", "Nome da etapa", "text");
    const titleInput = titleInputCell.firstChild;
    titleInput.style.width = "200px";
    titleInput.addEventListener("click", event => event.stopPropagation());
    summary.append(titleInput);
    if (!stage.ativo) summary.append(element("span", "badge", "Inativa"));
    summary.append(groupTotals("etapa", stage, ["orcado"]));
    const actions = element("div", "group-actions");
    actions.append(historyLink("etapa", stage.id), button(stage.ativo ? "Inativar" : "Reativar", "btn btn-quiet", () => changeState("etapa", stage)));
    if (stage.ativo) actions.append(button("Restaurar itens A–Z", "btn btn-quiet", () => mutate("ordem/", {tipo: "orcamento", etapa: stage.id, restaurar: true})), button("+ Item", "btn btn-outline", async () => {
      const result = await mutate("linhas/", {tipo: "orcamento", etapa: stage.id});
      if (result?.registro) content.querySelector(`input[data-type="orcamento"][data-id="${result.registro.id}"][data-field="descricao"]`)?.focus();
    }));
    summary.append(actions); group.append(summary);
    const description = element("div", "stage-description group-inner");
    const descriptionLabel = element("label", "muted", "Descrição da etapa");
    const descriptionCell = editableCell(stage, "etapa", "descricao", "Descrição da etapa", "text");
    description.append(descriptionLabel, descriptionCell.firstChild);
    group.append(description);
    const wrap = element("div", "table-wrap group-inner");
    const table = element("table", "table budget-table"); const thead = element("thead"); const head = element("tr");
    for (const label of ["", "Item / Descrição", "Quantidade", "Unidade", "Valor unitário", "Total previsto", "Situação", "Ações"]) head.append(element("th", "", label));
    thead.append(head); table.append(thead); const body = element("tbody");
    for (const item of stage.itens) {
      const tr = element("tr", item.ativo ? "" : "row-inactive"); draggable(tr, "orcamento", item.id, stage.id);
      const drag = element("td", "drag-handle", "⠿"); drag.title = "Arraste para reorganizar item"; tr.append(drag);
      tr.append(editableCell(item, "orcamento", "descricao", "Descrição", "text", !stage.ativo), editableCell(item, "orcamento", "quantidade", "Quantidade", "number", !stage.ativo), editableCell(item, "orcamento", "unidade", "Unidade", "text", !stage.ativo), editableCell(item, "orcamento", "valor_unitario", "Valor unitário", "number", !stage.ativo));
      const total = element("td", "number"); total.append(subtotalNode("orcamento", item, "total")); tr.append(total, stateCell(item, "orcamento"));
      const actionCell = element("td"); actionCell.append(actionsFor("orcamento", item, stage.ativo)); tr.append(actionCell); body.append(tr);
    }
    if (!stage.itens.length) { const tr = element("tr"); const td = element("td", "muted", "Adicione itens para começar a preencher o orçamento desta etapa."); td.colSpan = 8; tr.append(td); body.append(tr); }
    table.append(body); wrap.append(table); group.append(wrap); return group;
  }

  function feeGroup() {
    const group = trackedDetails("taxas", "group fees"); const summary = element("summary");
    summary.append(element("span", "group-title", "Taxas de Serviço"), element("span", "group-subtitle", "Valores confirmados nos lotes"));
    const totals = element("div", "group-totals");
    for (const [label, value] of [["Orçado", data.totais.taxas], ["Realizado", data.totais.taxas], ["Saldo", "0"]]) { const span = element("span"); span.append(element("small", "", label), element("strong", "", currency(value))); totals.append(span); }
    summary.append(totals); group.append(summary);
    if (data.taxas.length) {
      const wrap = element("div", "table-wrap"); const table = element("table", "table fee-table"); const head = element("thead"); const tr = element("tr");
      for (const label of ["Lote", "Confirmação", "Percentual", "Orçado", "Realizado", "Saldo"]) tr.append(element("th", "", label)); head.append(tr); table.append(head);
      const body = element("tbody");
      for (const fee of data.taxas) {
        const row = element("tr");
        const date = fee.data_envio ? new Intl.DateTimeFormat("pt-BR", {dateStyle: "short", timeZone: "America/Sao_Paulo"}).format(new Date(fee.data_envio)) : "—";
        for (const val of [`Lote #${fee.id}`, date, `${decimal.format(Number(fee.percentual_taxa))}%`, currency(fee.valor_taxa), currency(fee.valor_taxa), currency("0")]) row.append(element("td", "", val));
        body.append(row);
      }
      table.append(body); wrap.append(table); group.append(wrap);
    }
    group.append(element("div", "fee-note", data.taxas.length ? "Cada lote contribui uma única vez. As taxas são somadas igualmente ao orçado e ao realizado, preservando o saldo." : "Nenhum lote confirmado. As taxas aparecerão aqui após a confirmação do primeiro lote."));
    return group;
  }

  function normalized(value) { return String(value ?? "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase("pt-BR"); }

  function applyExpenseView() {
    for (const body of content.querySelectorAll("tbody[data-expense-group]")) {
      const rows = [...body.querySelectorAll("tr[data-expense-id]")];
      rows.sort((a, b) => {
        const first = record("despesa", a.dataset.expenseId), second = record("despesa", b.dataset.expenseId);
        const field = sort.direction === 0 ? "fornecedor" : sort.field;
        const comparison = field === "valor" ? compararDecimais(first[field], second[field]) : collator.compare(first[field] ?? "", second[field] ?? "");
        return (comparison || first.id - second.id) * (sort.direction === 2 ? -1 : 1);
      });
      for (const row of rows) {
        const obj = record("despesa", row.dataset.expenseId);
        row.hidden = [...filters].some(([field, value]) => {
          const raw = field === "data_nf" && obj[field] ? obj[field].split("-").reverse().join("/") : field === "valor" ? `${obj[field] ?? ""} ${currency(obj[field])}` : obj[field];
          return !normalized(raw).includes(normalized(value));
        });
        body.append(row);
      }
    }
    for (const node of content.querySelectorAll("[data-sort-field]")) {
      const active = sort.field === node.dataset.sortField && sort.direction !== 0;
      node.querySelector(".sort-mark").textContent = active ? sort.direction === 1 ? "↑" : "↓" : "";
      node.parentElement.setAttribute("aria-sort", active ? sort.direction === 1 ? "ascending" : "descending" : "none");
    }
    content.querySelectorAll("[data-filter-field]").forEach(node => node.classList.toggle("has-filter", filters.has(node.dataset.filterField)));
    const chips = document.getElementById("filter-chips"); chips.replaceChildren();
    for (const [field, value] of filters) {
      const label = expenseFields.find(([key]) => key === field)[1];
      const chip = button(`${label}: ${value} ×`, "filter-chip", () => { filters.delete(field); applyExpenseView(); });
      chip.setAttribute("aria-label", `Remover filtro ${label}: ${value}`); chips.append(chip);
    }
    document.getElementById("clear-filters").hidden = filters.size === 0;
  }

  function openFilter(field, label) {
    const dialog = document.getElementById("filter-dialog");
    const input = document.getElementById("filter-input");
    document.getElementById("filter-title").textContent = `Filtrar ${label}`;
    input.value = filters.get(field) || "";
    dialog.addEventListener("close", () => {
      if (dialog.returnValue === "confirm" && input.value.trim()) filters.set(field, input.value.trim());
      else if (dialog.returnValue === "clear" || dialog.returnValue === "confirm") filters.delete(field);
      applyExpenseView();
    }, {once: true});
    dialog.returnValue = "";
    dialog.showModal(); input.focus();
  }

  function render() {
    content.replaceChildren();
    document.querySelectorAll("[data-tab]").forEach(node => node.classList.toggle("active", node.dataset.tab === tab));
    document.getElementById("sheet-title").textContent = tab === "geral" ? "Visão geral" : "Orçamento da obra";
    document.getElementById("sheet-description").textContent = tab === "geral" ? "Do previsto ao realizado, por etapa da obra." : "Preencha as células. Arraste etapas e itens para reorganizar.";
    document.getElementById("expense-filters").hidden = tab !== "geral";
    if (tab === "geral") content.append(feeGroup());
    else if (data.etapas.length) {
      const actions = element("div", "actions mb-3");
      actions.append(button("Restaurar etapas A–Z", "btn btn-outline btn-sm", () => mutate("ordem/", {tipo: "etapa", restaurar: true})));
      content.append(actions);
    }
    const stages = element("div", "stages");
    for (const stage of data.etapas) stages.append(tab === "geral" ? generalStage(stage) : budgetStage(stage));
    content.append(stages);
    if (!data.etapas.length) {
      const empty = element("div", "card empty-state");
      empty.append(element("span", "", "▦"), element("h3", "", "Uma obra começa pelas etapas"), element("p", "", "Crie a primeira etapa para adicionar itens previstos e registrar despesas."), button("+ Criar primeira etapa", "btn btn-primary", newStage));
      content.append(empty);
    }
    updateTotals(); applyExpenseView();
  }

  async function newStage() {
    if (!await beforeRender()) return;
    const dialog = document.getElementById("stage-dialog"), input = document.getElementById("stage-input");
    input.value = "";
    dialog.addEventListener("close", async () => {
      if (dialog.returnValue === "confirm" && input.value.trim()) await mutate("linhas/", {tipo: "etapa", titulo: input.value.trim()});
    }, {once: true});
    dialog.returnValue = "";
    dialog.showModal(); input.focus();
  }

  document.querySelectorAll("[data-tab]").forEach(node => node.addEventListener("click", async event => {
    event.preventDefault();
    if (!await beforeRender()) return;
    tab = node.dataset.tab;
    const url = new URL(location.href); url.searchParams.set("aba", tab); history.replaceState(null, "", url);
    render();
  }));
  inactive.addEventListener("change", async () => {
    if (!await beforeRender()) { inactive.checked = !inactive.checked; return; }
    try { data = await enqueue(() => api("dados/")); render(); }
    catch (error) { inactive.checked = !inactive.checked; window.fereziniToast(error.message, true); }
  });
  document.getElementById("new-stage").addEventListener("click", newStage);
  document.getElementById("clear-filters").addEventListener("click", () => { filters.clear(); applyExpenseView(); });
  window.addEventListener("beforeunload", event => { if (needsResolution()) { event.preventDefault(); event.returnValue = ""; } });
  render();
})();
