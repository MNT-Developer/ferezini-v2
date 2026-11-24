# 009 — Interface, templates e JavaScript

[Guia](001_GUIA_DA_DOCUMENTACAO.md) · [Templates](../templates/) · [JavaScript](../static/js/).

## Composição da interface

`base.html` define menu conforme permissões, mensagens, topbar, região principal, CSS local e blocos de scripts. CSRF protege operações de escrita. Dados da obra são incluídos com `json_script`, não concatenados em JavaScript executável. A visibilidade do menu não substitui autorização nas views/serviços.

| Templates | Responsabilidade |
| --- | --- |
| `registration/login`, `accounts/*` | Login, redefinição, usuários e confirmação de estado |
| `core/inicio`, `core/paginacao` | Cards, projetos e links que preservam filtros |
| `projetos/lista`, `_pastas_lista`, `_lista_filtrada`, `_tabela_lista` | Duas abas, pastas e tabela compartilhada |
| `projetos/form`, `_responsavel_tecnico`, `_responsavel_modal` | Capa e seletor de colaborador |
| `projetos/detalhe` | Geral/Orçamento, tela exclusiva por etapa e diálogos |
| `projetos/_importar_modal`, `importar` | Upload e nova tentativa após erros |
| `envios/*` | Seleção, prévia, confirmação, histórico, detalhe e reenvio |
| `relatorios/despesas`, `_tabela_periodo` | Consulta por período |
| `core/em_desenvolvimento` | Placeholder de Relatórios Gerais e Diretoria |

Templates de impressão antigos são históricos; PDF atual usa ReportLab. Templates ativos são UTF-8/LF, indentação de dois espaços e formatação djlint. `_acoes_lista` mantém Importar antes de Novo projeto. Na tabela, links continuam utilizáveis por teclado e clique na linha também abre o projeto.

## Módulos JavaScript

| Arquivo | Fluxo |
| --- | --- |
| [app.js](../static/js/app.js) | Menu lateral e avisos básicos da aplicação |
| [projetos-lista.js](../static/js/projetos-lista.js) | Clique na linha sem interceptar controles/seleção de texto; modal de importação e bloqueio de envio duplo |
| [responsavel-tecnico.js](../static/js/responsavel-tecnico.js) | Inicializa seletor, abre por clique/Enter, busca com cancelamento e descarta respostas antigas; seleção preenche FK/primeiro nome |
| [formatacao.js](../static/js/formatacao.js) | Partes decimais, moeda BR e comparação numérica usando BigInt |
| [envios.js](../static/js/envios.js) | Soma notas e calcula taxa em unidades inteiras; alteração manual exige motivo; mudar seleção limpa ajuste/motivo |
| [projeto.js](../static/js/projeto.js) | Estado da planilha, renderização, edição, erros, histórico, filtros e reordenação |

As funções nomeadas de cada módulo estão individualizadas no [catálogo 012](012_REFERENCIA_DE_FUNCOES.md). Os handlers anônimos são callbacks internos dos eventos descritos aqui; não são uma API externa.

## Autosave e concorrência no navegador

`editableCell` cria campos com estado de registro/versão. Edição torna a célula dirty; sair do campo aciona `saveCell`. `enqueue` serializa mutações. `api` inclui CSRF e interpreta erros; sucesso substitui o registro pelo valor canônico do servidor e atualiza totais.

Erro mantém valor e indicação visual, com caminhos de tentar novamente ou descartar. Conflito 409 exige resolver dados antes de nova renderização. Justificativa obrigatória abre o diálogo e repete a operação com o motivo. `beforeRender`/`needsResolution` evitam perder edições locais ao reconstruir a planilha.

`trackedDetails` preserva a abertura dos grupos durante interações; estado inicial é fechado. `generalStage` mostra itens e Demais Despesas; `budgetStage` mostra edição/reordenação dos itens e acesso à tela de orçamento. `feeGroup` representa taxas automáticas confirmadas. Não confundir seu conteúdo com uma despesa persistida.

`draggable` registra sequência de etapas/itens no endpoint de ordem. Filtros de coluna e ordenação de despesas atuam apenas na visão, não nos totais oficiais nem no banco. `normalized` remove diferenças de acentos/caixa na comparação visual. Comparação financeira usa `compararDecimais`, não conversão para Number.

## Precisão e segurança de apresentação

`decimalParts`, `unidades` e comparadores operam sobre strings decimais. BigInt conserva centavos além do limite seguro de Number e o arredondamento de meio centavo. JSON vindo do servidor preserva decimais como texto. Textos de fornecedores/colaboradores entram como conteúdo, não HTML executável.

Modal de importação envia multipart para o servidor; não executa macros no navegador. Os downloads PDF/XLSM são endpoints normais autenticados. Bibliotecas Bootstrap são locais; os fluxos não dependem de CDN.

Colagem de várias células do Excel não foi implementada. Colagem de uma célula é nativa do campo. Estilos e breakpoints usam a base existente; não há alteração visual nesta consolidação documental.
