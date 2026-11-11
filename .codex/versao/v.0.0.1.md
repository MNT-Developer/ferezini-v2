# Ferezini — Gestão Financeira de Obras

> **Nota de infraestrutura:** documento histórico. A implantação atual é Linux/HostMídia/cPanel, descrita em [v.0.0.3](v.0.0.3.md); instruções antigas Windows/Linux foram substituídas.

> **Especificação de implementação V1 para Codex**  
> **Destino no repositório:** `.codex/versao/v.0.0.1.md`  
> **Idioma do produto, mensagens, testes de interface e documentação:** português brasileiro (`pt-BR`).  
> **Objetivo:** implementar uma primeira versão funcional de um sistema Django para controlar orçamentos, despesas e envios de despesas por obra, com visual clean e execução multiplataforma (Windows e Linux).

## 0. Instruções de execução para o Codex

1. Examine a estrutura existente antes de criar ou alterar arquivos. Preserve código, dados, configurações e migrações existentes. Se já houver banco com dados, planeje migrações de dados sem perdas; caso o projeto ainda não tenha sido iniciado, modele diretamente a estrutura final.
2. Implemente a primeira versão **V1**, na ordem deste documento, com migrações, testes e telas utilizáveis. **Não alterar o número de versão** até que a implementação inicial seja concluída.
3. Não implementar relatórios estratégicos “Relatórios Gerais” e “Diretoria”: criar rotas, menu autorizado e página “Em desenvolvimento”.
4. As regras financeiras, permissões, transações, auditoria e cálculos são validados no backend. Não confiar apenas no JavaScript; nunca contornar validação/auditoria com atualizações indiscriminadas.
5. Não transformar decisões não aprovadas em requisitos definitivos. Documentar defaults provisórios da seção 18 em `.codex/docs/decisoes_pendentes.md`.
6. Não introduzir React, Vue, Docker, Redis, Celery ou API externa obrigatória. Usar Django Templates + JavaScript.
7. Consultar documentação oficial das dependências e verificar versões compatíveis de Django, MySQL/MariaDB, AG Grid, WeasyPrint, Waitress e Gunicorn. Fixar e documentar versões.
8. Não versionar segredos. Criar `.env.example`, scripts Windows/Linux, README e testes.
9. Executar testes e checks disponíveis; se faltar infraestrutura, reportar o bloqueio honestamente.
10. Adotar os padrões de código da seção 19: Zen of Python, views somente com funções de view, `utils.py` por app quando necessário e coleção `utils/` global para funções genéricas. Evitar abstrações e rodeios.

## 1. Escopo funcional da V1

Implementar:

- Login/logout, funcionários e cinco permissões cumulativas.
- Projetos/obras e seus e-mails de contato (zero a N), com **percentual padrão de taxa de serviço**.
- **Etapas** diretamente vinculadas aos projetos; cada etapa possui **linhas de `Orcamento`** e **`Despesa`**. Não existe `ItemOrcamento` nem modelo intermediário de orçamento agrupador.
- Despesas vinculadas obrigatoriamente a uma etapa e opcionalmente a uma linha `Orcamento` da mesma etapa.
- Tela **Geral** com hierarquia etapa → item (linha `Orcamento`) → despesa; área geral da etapa para despesas sem linha de orçamento ativa; **agrupamento virtual Taxas de Serviço sempre em primeiro**.
- Salvamento automático por célula, rascunho progressivo, justificativas condicionais, auditoria, inativação lógica e reativação com observação.
- Etapas e itens inicialmente em ordem alfabética, podendo ser reorganizados por arrastar e soltar, com persistência. Despesas inicialmente por fornecedor A–Z, ordenação dinâmica pelo cabeçalho e filtros por coluna **sem alterar subtotais oficiais**.
- Lotes com despesas selecionadas, **taxa calculada sobre todas as despesas escolhidas**, ajuste justificado somente antes da confirmação, visualização e geração PDF em memória e e-mails opcionais.
- Histórico, snapshots, reenvios automáticos e manuais; relatório de despesas por período pela data do lote.
- Identidade Ferezini, interface clean, Windows e Linux.

Não implementar nesta versão: relatórios estratégicos gerais e diretoria (somente placeholder), dashboards estratégicos avançados, persistência de PDFs, Celery/Redis, integrações fiscais externas.

## 2. Stack e execução multiplataforma

| Camada | Tecnologia |
|---|---|
| Backend | Python + Django, WSGI |
| Banco | **MySQL ou MariaDB**, tabelas InnoDB, `utf8mb4`, SQL strict, isolamento `READ COMMITTED` quando suportado |
| ORM | Django ORM e migrações |
| Frontend | Django Templates + Bootstrap 5 + CSS da identidade Ferezini + JavaScript Fetch API |
| Planilha | Preferência por **AG Grid Community**; não usar recursos exclusivos da licença Enterprise sem alternativa gratuita |
| PDF | HTML/CSS de impressão + WeasyPrint, gerado em memória |
| E-mail | Backend SMTP do Django; bytes do PDF gerados em memória |
| Agendamento | Django Management Command compartilhado, Task Scheduler no Windows e systemd timer/cron no Linux |
| Servidor Windows | **Waitress** atrás de proxy HTTPS |
| Servidor Linux | **Gunicorn** atrás de proxy HTTPS |
| Desenvolvimento | `python manage.py runserver` nos dois SO |

Os servidores web/proxies e agendadores são componentes de implantação, não devem alterar a lógica da aplicação. Use `pathlib`, variáveis de ambiente, timezone `America/Sao_Paulo`, idioma `pt-br`, `Decimal`/`DecimalField` para finanças, datas timezone-aware e templates seguros contra XSS.

Estrutura sugerida (ajuste às convenções existentes, se houver):

```text
config/{settings.py,urls.py,wsgi.py,asgi.py}
apps/{core,accounts,projetos,orcamentos,despesas,envios,auditoria,relatorios}/
templates/ static/ tests/ utils/
.codex/
    scripts/
    versao/v.*.md
    docs/
    requirements/
.env.example manage.py README.md
```

Organização: views somente com handlers HTTP; funções auxiliares específicas em `apps/<app>/utils.py` e funções genéricas na coleção `utils/*.py` da raiz. Separar serviços transacionais quando tecnicamente justificado; evitar camadas artificiais. Configurações separadas para desenvolvimento e produção. Criar um usuário Django customizado **antes da migração inicial**. Não usar `runserver` em produção.

## 3. Funcionários, autenticação e permissões

Modelo de usuário próprio baseado em `AbstractUser`, com autenticação Django, campos pessoais básicos e flags:

- `permissao_diretoria = BooleanField(default=False)` — todas as funções operacionais/financeiras, relatórios gerais e relatórios exclusivos da diretoria, **exceto gestão de funcionários**, a menos que essa permissão também esteja ativa.
- `permissao_gestao_funcionario = BooleanField(default=False)` — cadastro/edição/inativação de funcionários e administração das permissões.
- `permissao_acesso_geral = BooleanField(default=False)` — todos os projetos, orçamentos, despesas, lotes e relatórios operacionais/gerais; **sem** relatórios exclusivos da diretoria ou gestão de funcionários.
- `permissao_gestao_projetos = BooleanField(default=False)` — **todos os projetos**, não por vínculo individual; acesso operacional completo dentro deles, inclusive relatórios internos dos projetos; não concede Diretoria, Relatórios Gerais globais ou Gestão Funcionário por si só.
- `permissao_relatorios_gerais = BooleanField(default=False)` — acesso ao menu de Relatórios Gerais (placeholder nesta V1), sem conceder edição de projetos.

As flags são cumulativas e independentes. As funções de autorização devem ficar centralizadas, aplicadas na navegação, views, serviços, endpoints Fetch, PDFs e reenvios. `is_staff`/`is_superuser` são privilégios técnicos do Django e **não equivalem** a Diretoria. Esconder botão não substitui verificação no servidor.

## 4. Projeto, percentual de taxa e e-mails

`Projeto`: `id`, `nome`, `descricao`, `cliente_contratante`, `cpf_cnpj`, `endereco_obra`, `responsavel_tecnico`, `data_inicio`, `previsao_termino`, `data_conclusao`, `status`, **`taxa_servico` (DecimalField percentual, default 0)**, `criado_em`, `criado_por` e controles técnicos de auditoria/versão. CPF/CNPJ normalizado sem máscara e validado quando informado. O percentual pode ser editado no projeto, sem alterar lotes anteriores. Validar percentual não negativo; limites administrativos adicionais não foram decididos.

Status: **somente** `EM_ANDAMENTO`, `CONCLUIDO`, `CANCELADO`. Não incluir “Planejamento”.

`ProjetoEmail`: `id`, `projeto` FK, `email` EmailField, `ativo=True`, `criado_em`. Permitir **0 a N** e-mails e evitar duplicação case-insensitive por projeto; endereços inativos não são selecionados por padrão.

## 5. Etapas e linhas de orçamento (`Orcamento`)

**Modelagem definitiva:** `Projeto → Etapa → (Orcamento, Despesa)`. `Etapa` substitui a antiga categoria; `Orcamento` substitui `ItemOrcamento` e representa **uma linha de item previsto**, não um agrupador. Na interface Geral, o `Orcamento` aparece como **“Item”**.

`Etapa`: `id`, `projeto` FK obrigatória, `titulo`, `descricao` opcional, `ativo=True`, `ordem`/indicador de ordenação manual quando necessário, `criado_em`, `criado_por`, versão e auditoria. Exemplos: Fundamento, Elétrica, Hidráulica. A etapa é o agrupamento de orçamento e despesas; seu total orçado é a soma dos `Orcamento` elegíveis.

`Orcamento`: `id`, **`etapa` FK obrigatória**, `descricao` (nome do item), `quantidade` DecimalField nullable, `unidade` opcional, `valor_unitario` DecimalField nullable, `rascunho=True`, `ativo=True`, `ordem`/indicador de ordenação quando necessário, `versao`, `criado_em`, `criado_por` e auditoria. **Não criar modelo `ItemOrcamento`**.

Cada linha é criada imediatamente como rascunho no banco e preenchida por células. `rascunho=False` somente se descrição não vazia, quantidade informada e valor unitário informado. Quantidade/valor unitário **0 são válidos**; negativos proibidos. `NULL` significa não informado. Unidade opcional. Total orçado da linha = quantidade × valor unitário, calculado e não editável. Somente linhas completas e efetivamente ativas entram nos totais orçados.

**Alteração:** se a linha de orçamento já teve qualquer despesa associada, ativa ou inativa, qualquer edição de dados de negócio exige justificativa e histórico. Caso nunca tenha tido, edição sem justificativa. Pode ficar saldo negativo. Linha inativa não pode ser editada até reativação.

**Ordenação das etapas e linhas de orçamento:** exibição inicial alfabética PT-BR (A–Z). Usuário pode arrastar e soltar etapas no próprio projeto e linhas `Orcamento` dentro da própria etapa; persistir nova sequência automaticamente em transação. Após personalização, preservar ordem manual; novas linhas entram ao final. Prever opção **Restaurar A–Z** que remove a personalização. A área virtual Taxas de Serviço é fixa no topo e não é arrastável. Ordenação jamais altera FKs ou cálculos.

## 6. Despesas e integridade dos relacionamentos

`Despesa`: `id`, **`etapa` FK obrigatória**, **`orcamento` FK opcional** para a linha orçada daquela etapa, `lote_envio` FK opcional/default `NULL`, `descricao` opcional, `fornecedor`, `cpf_cnpj_fornecedor` opcional, `numero_nf` opcional, `data_nf` opcional, `valor` DecimalField nullable, `observacao` opcional, `rascunho=True`, `ativo=True`, `versao`, `criado_em`, `criado_por` e auditoria.

**Não duplicar `projeto` nem `data_envio` na despesa**. Projeto = `despesa.etapa.projeto`. Data de envio = `despesa.lote_envio.data_envio` quando existir.

Validar no backend:

1. Se `despesa.orcamento_id` não for `NULL`, exigir **`despesa.orcamento.etapa_id == despesa.etapa_id`**.
2. Se houver lote, exigir **`despesa.lote_envio.projeto_id == despesa.etapa.projeto_id`**.
3. Proibir edição direta de `lote_envio` pela planilha; preservar FKs quando um item fica inativo.
4. Não cadastrar despesas em etapa inativa; não editar registros inativos.

`rascunho=False` somente quando **fornecedor não vazio e valor > 0**; NF, descrição, data NF e CPF/CNPJ são opcionais. Campo calculado no backend, sem edição manual. Despesas ativas com valor monetário válido entram no realizado **mesmo em rascunho**, mas rascunhos não podem integrar lotes. Valores negativos proibidos; zero permitido em rascunho, porém não elegível para envio.

Despesa com `lote_envio=NULL`: edição livre para usuário autorizado, com auditoria técnica. Despesa com lote: edição de campos de negócio apenas com justificativa, mantendo o lote e o snapshot original intactos. Inativa: requer reativação para editar.

## 7. Inativação, reativação e status efetivo

**Nunca fazer `DELETE` físico** dos registros de negócio. Inativação altera `ativo=False`, sem perder vínculos. Por padrão exibir apenas ativos; oferecer checkbox **“Exibir itens excluídos”**. Inativos são visualmente distintos, consultáveis e não editáveis; reativação sempre requer observação e auditoria.

| Registro | Condição | Justificativa para inativar |
|---|---|---|
| `Despesa` | Qualquer situação | **Sempre obrigatória** |
| `Orcamento` (linha/item) | Nunca teve despesa associada | Não obrigatória |
| `Orcamento` (linha/item) | Já teve despesa, ativa ou inativa | **Obrigatória** |
| `Etapa` | Não há nenhuma despesa ativa nela | **Sempre obrigatória** |
| `Etapa` | Há uma ou mais despesas ativas, com ou sem item associado | **Inativação proibida** |

Ao inativar uma etapa, **não modificar `ativo` de suas linhas `Orcamento`**: orçamento efetivamente ativo = `etapa.ativo AND orcamento.ativo`. Etapa inativa bloqueia operações e reativação de filhos até que a própria etapa seja reativada. Na reativação, linhas retomam seus estados individuais originais. Toda inativação/reativação de etapa exige justificativa/explicação.

Ao inativar uma linha `Orcamento`, as despesas a ela vinculadas **mantêm `orcamento_id` e seu próprio status**. Despesas ativas dessa linha passam a aparecer na **área geral da mesma etapa**, sem alterar FKs. Se a linha for reativada, reaparecem sob ela. Ao inativar uma despesa, a linha prevista continua disponível para receber novas despesas. Não criar lançamentos vazios artificiais no banco.

Total orçado = soma das linhas `Orcamento` completas, com `ativo=True` e etapa ativa. Total realizado = soma das despesas ativas com valor válido nas etapas ativas, **mesmo que a linha `Orcamento` vinculada esteja inativa**. Nunca duplicar despesas nos subtotais. Saldos negativos permitidos.

## 8. Auditoria obrigatória

Criar entidade central `HistoricoAlteracao` (ou equivalente robusta): entidade/tipo, ID, projeto de contexto quando aplicável, ação, usuário, timestamp timezone-aware, campos e valores anteriores/novos, justificativa/observação, correlacionador da operação. Histórico somente leitura para usuários; preservar sequência cronológica e identidade do operador.

- Edições normais antes do envio: registrar auditoria técnica (sem exigir justificativa).
- Edição de despesa já incluída em lote: justificativa obrigatória.
- Edição de item orçado que já teve despesa: justificativa obrigatória.
- Exclusões e reativações: seguir tabela da seção 7.
- Alterar registro e escrever auditoria **na mesma transação**.

## 9. Interface, navegação e planilha Geral

Produto em PT-BR, visual clean e corporativo, fundo claro, bordas suaves, tipografia legível, marca Ferezini. Logo de referência: `http://ferezini.com.br/assets/images/ferezini-hor-404x145.png`. Se indisponível, usar texto provisório e tema CSS configurável; não inventar cores oficiais.

Menu lateral recolhível: Início, Projetos, Funcionários, Relatórios Gerais, Diretoria, Sair; exibir segundo permissões. Relatórios Gerais e Diretoria são páginas protegidas **“Em desenvolvimento”**, sem implementação funcional. Tela inicial com indicadores operacionais autorizados e lista de projetos; listagem com busca/status/orçado/realizado/saldo.

Página do projeto: dados da obra, quatro indicadores (orçado, realizado, saldo, execução), quatro abas **Geral, Orçamento, Envio de Despesas, Relatório de Despesa**. Gerenciar **etapas** e suas linhas `Orcamento` na aba Orçamento.

**Geral:** hierarquia expansível **Taxas de Serviço (grupo virtual fixo primeiro) → demais Etapas → Item (`Orcamento`) → Despesas**; despesas sem `orcamento` ou ligadas a `Orcamento` inativo aparecem na **área geral da etapa**. Mostrar linhas orçadas sem despesas e oferecer ação para incluir despesa sem criar despesa vazia no banco. Subtotais por item e por etapa; total do projeto. Grupo virtual Taxas traz uma linha por lote confirmado, sem ser `Etapa` nem `Despesa` artificial: **orçado = realizado = taxa aplicada**, saldo **sempre zero**.

**Ordenação e filtros de despesas:** por padrão fornecedor A–Z em cada agrupamento. Clique no nome de coluna alterna crescente → decrescente → ordem padrão (adequar a datas e números). Ao passar o mouse no cabeçalho, mostrar ícone pequeno de filtro; clique abre caixa para pesquisar naquela coluna. Em touchscreen o ícone deve ser acessível sem hover. Permitir filtros simultâneos, remover um ou todos. **Filtros ocultam apenas linhas de despesas para apresentação e jamais recalculam orçado, realizado, saldo, subtotais de etapas/itens ou indicadores do projeto.** Não mover despesa entre itens/etapas por ordenação. Comportamento de etapas sem resultados filtrados ainda pendente (seção 18).

**Orçamento:** gestão das etapas e das linhas `Orcamento`, rascunhos, edição por célula, inativação/reativação, reordenação manual e histórico.

**Envio de Despesas:** abas Pendentes e Histórico de Lotes; seleção por checkbox pré-marcada, prévia de taxa, e-mails, PDF e histórico das tentativas.

**Relatório de Despesa:** período inclusivo pelo lote, HTML e PDF.

Interface responsiva; priorizar planilhas em desktop e permitir consulta adequada em mobile.

## 10. Planilhas: autosave por célula e rascunho

- Criar nova linha → `POST` gera registro em banco imediatamente, com `rascunho=True`, `ativo=True` e identificador persistente.
- Ao terminar edição de célula (Enter/Tab/blur), enviar requisição Fetch (`PATCH` ou endpoint equivalente) com ID, campo permitido, novo valor, versão e justificativa **quando aplicável**.
- Validar no backend permissão, campo editável, status efetivo, tipos/limites, vínculos e versão. Salvar + auditar atomicamente. Responder com valor canônico, `rascunho`, versão atual e totais afetados.
- Exibir indicadores discretos de editando/salvando/salvo/erro. Não mostrar “salvo” antes do ACK do servidor. Em falha de rede ou validação, preservar a edição e permitir retry ou reversão explícita.
- Evitar sobrescrita silenciosa em concorrência: `versao` com atualização otimista, retorno de conflito e opção de recarregar.
- Campos automáticos (IDs, vínculo do lote, auditoria, datas, somatórios, `ativo`, `rascunho`) nunca editáveis diretamente.
- Justificativas por modal. Ao cancelar, restaurar valor confirmado.
- Copiar/colar do Excel é desejável; **não depender de funcionalidade Enterprise**. Se a colagem múltipla não estiver disponível na Community, criar alternativa aberta ou documentar claramente a limitação. Validar edição em lote de maneira atômica caso implementada.

## 11. Lotes de envio e taxa de serviço

`LoteEnvioDespesa`: `id`, `projeto` FK, `data_envio` (`DateTimeField` na confirmação), `enviado_por`, `modalidade` (`GERAR`/`GERAR_ENVIAR`), status do e-mail, timestamps, tentativas/próximo horário/último erro, versão do layout; **`valor_despesas`, `percentual_taxa`, `valor_taxa_calculado`, `valor_taxa`, `justificativa_taxa`, `valor_total`** com precisão Decimal. **Não armazenar PDF**.

`Despesa.lote_envio` é FK opcional e o vínculo oficial de pertencimento; uma despesa não entra em dois lotes.

Fluxo:

1. No projeto, listar apenas despesas com `ativo=True`, `rascunho=False`, `lote_envio IS NULL` e **`etapa.ativo=True`**; marcar todas por padrão.
2. Permitir desmarcar qualquer despesa e exigir ao menos uma selecionada. Exibir fornecedor, etapa, referência opcional ao item e valores.
3. **Calcular a taxa sobre a soma de TODAS as despesas selecionadas**, sem exceções por etapa ou item: `valor_taxa_calculado = (valor_despesas * percentual_taxa / 100)` arredondado monetariamente (`Decimal`, `ROUND_HALF_UP`, duas casas). Percentual é **copiado de `Projeto.taxa_servico`** ao preparar/confirmar o lote; alterações posteriores do projeto não afetam lotes confirmados.
4. Na preparação, permitir alterar **somente o valor aplicado `valor_taxa`** em relação ao cálculo, exigindo **justificativa obrigatória** quando diferente. Não alterar retrospectivamente o percentual padrão do projeto. Exibir resumo: despesas, percentual, taxa calculada, taxa aplicada, total do lote = despesas + taxa aplicada.
5. Modalidade padrão: “Gerar relatório”; opcional “Gerar e enviar por e-mail”. Confirmar sob transação: revalidar permissões, elegibilidade, vínculo projeto-etapa, seleção e taxa; criar lote, associar despesas, armazenar valores da taxa e snapshots imutáveis das despesas, com data/colaborador únicos para o lote.
6. **Após confirmação, valores e percentual da taxa do lote são imutáveis, mesmo com justificativa.** Reenvios usam os valores históricos; correção posterior de despesa não recalcula o lote nem sua taxa.
7. PDFs gerados em memória sob demanda; falhas técnicas não podem gerar lotes parciais ou duplicados. Se o e-mail foi solicitado, executar após commit. Despesas desmarcadas permanecem pendentes.

`LoteEnvioItem`: `lote`, `despesa`, `dados_snapshot` JSON, `valor_snapshot`, ordenação estável. Snapshot inclui dados do projeto, **etapa**, referência/item `Orcamento` quando existente, valores e dados fiscais aplicáveis. Não alterar snapshots quando despesa for corrigida/inativada.

`ProjetoEmail`: zero a N e-mails. No envio, cadastrados ativos pré-selecionados com checkbox; pode desmarcar e acrescentar destinatários temporários (não cadastrá-los no projeto), validando e deduplicando. Exigir pelo menos um destinatário efetivo. Preservar destinatários do lote/tentativa, preferir CCO. Modo sem e-mail ativo cadastrado permanece decisão provisória da seção 18.

Reenvio manual de **qualquer lote**, inclusive já enviado, com destinatários originais e/ou temporários, sem justificativa e sem novo lote, sem alterar taxa, despesas ou snapshots.

**Categoria visual Taxas de Serviço:** não é tabela `Etapa` nem `Despesa`. É o agrupamento virtual sempre no topo da tela Geral. Cada lote confirmado contribui exatamente uma vez com **orçado = realizado = `valor_taxa`** e desvio zero. Nos totais do projeto, somar taxas igualmente ao orçamento e ao realizado, **sem mudar o saldo financeiro**. Se não houver lotes, a categoria pode aparecer com valor zero, sem lançamento artificial.

## 12. Processamento e reenvio automático de e-mails

- Primeiro envio solicitado: após confirmação do lote, sem bloquear a requisição web por SMTP demorado. Registre trabalho pendente de maneira persistente no MySQL/MariaDB.
- Se houver falha confirmada: agendar reenvio automático **3 horas após a falha**, com **até 3 reenvios automáticos além do envio inicial** (4 tentativas automáticas no total). Depois disso, somente reenvio manual.
- Sucesso cancela tentativas automáticas futuras. Reenvio manual bem-sucedido cancela agendamento automático pendente; tentativas manuais não zeram contador de retries automáticos.
- Histórico `LoteEnvioTentativa`: lote, tipo (`INICIAL`, `AUTOMATICA`, `MANUAL`), timestamps, resultado, erro, destinatários efetivos, usuário solicitante para manual e identificador de tentativa.
- Estado sugerido: `NAO_SOLICITADO`, `PENDENTE`, `ENVIANDO`, `REENVIO_AGENDADO`, `ENVIADO`, `FALHA_DEFINITIVA`, com estado de resultado **incerto** para timeout/queda durante a transmissão.
- Não disparar dois e-mails simultâneos para mesmo lote; reservar a tarefa via transação MySQL/InnoDB e controle de concorrência. Não manter transação do banco aberta durante chamadas SMTP.
- Diante de resultado incerto, **não reenviar cegamente**; registrar para investigação/ação segura, minimizando duplicidades.
- Implementar management command `python manage.py processar_emails_pendentes` independente do sistema operacional, reentrante e seguro contra múltiplas execuções. Incluir scripts para Task Scheduler (Windows) e systemd timer ou cron (Linux), por exemplo verificando pendências a cada minuto; quem determina 3 horas é `proxima_tentativa` gravada no banco.
- Considerar “enviado” quando o SMTP aceitar a mensagem, **não** quando o destinatário ler/receber.

## 13. Relatórios — HTML e PDF sob demanda, sem salvar arquivos

Nenhum PDF persistido em disco, banco ou armazenamento externo. Usar dados estruturados → Django Templates HTML/CSS → visualização no navegador ou PDF via WeasyPrint em memória; anexos e reenvios também gerados em memória. Identidade Ferezini, cabeçalho, data, paginação e totais.

**Relatório de Envio:** um lote, reconstruído dos snapshots imutáveis. Mostrar despesas, subtotal `valor_despesas`, percentual copiado, taxa **aplicada** (inclusive ajustes justificados antes da confirmação) e `valor_total`. Se o layout evoluir, PDFs regenerados podem diferir em bytes/aparência; não prometer preservação binária exata.

**Relatório de Despesas por Período:** filtro inclusivo pela data de confirmação `Despesa.lote_envio.data_envio`, no fuso `America/Sao_Paulo` e limitado ao projeto via `Despesa.etapa.projeto`; visualização HTML e download PDF sem modificar registros. Valor histórico (snapshot) versus atual ainda pendente; default provisório: snapshot do lote. Colunas PDF também pendentes, default: data do lote, etapa, item (se houver), fornecedor, NF, data NF, valor, subtotal e total. **Não duplicar a taxa ou o orçado ao listar múltiplas despesas de um mesmo item.** Definir claramente nos relatórios que mostram taxas se o total é com/sem taxa.

Downloads exigem autenticação e autorização; sem URLs públicas de arquivos. Não confundir data de envio do lote com tentativas SMTP.

## 14. Integridade, consistência e desempenho

- FKs financeiras com `on_delete=PROTECT` ou estratégia equivalente. Não executar exclusão física de dados de negócio.
- Em `Despesa`, validar `orcamento.etapa_id == despesa.etapa_id` quando houver `orcamento` e `lote_envio.projeto_id == despesa.etapa.projeto_id` quando houver lote.
- Transações `transaction.atomic()` em envios, snapshots, ajustes de ordem, auditoria e mudanças compostas; nunca manter transação aberta durante SMTP ou geração demorada de PDF.
- Controle de concorrência otimista (`versao`) na edição e bloqueio transacional na associação de despesas a lotes; testar em MySQL/MariaDB compatível.
- Decimal, sem float monetário. Arredondamento de taxa `ROUND_HALF_UP` duas casas. Taxa do lote confirmada imutável.
- `select_related`/`prefetch_related` para percorrer Projeto → Etapa → Orcamento/Despesa e Lote; evitar N+1. Índices em FKs, `ativo`, `rascunho`, `lote_envio`, datas de lote e ordenações conforme necessidade.
- Filtros e ordenações **somente visuais** não alteram FKs, totais, snapshots nem auditoria financeira. Buscar totais oficiais sem filtros da grade.
- Histórico, lotes e snapshots preservados; validar backend para todas as ações e requisições diretas.

## 15. Testes obrigatórios e critérios de aceite

Criar testes automatizados para:

1. Permissões cumulativas/independentes, Diretoria sem Gestão Funcionário, Gestão Projetos acessando todos, APIs e PDFs protegidos.
2. Projetos com 0 a N e-mails; e-mails duplicados/inativos; `taxa_servico` com default 0 e alteração sem efeito retroativo em lotes.
3. Modelagem **Projeto → Etapa → Orcamento e Despesa**; não existe `ItemOrcamento` nem `Despesa.projeto` nem `Despesa.data_envio`.
4. Despesa opcionalmente ligada a `Orcamento` da mesma etapa; rejeitar item de outra etapa e lote de outro projeto.
5. Rascunho criado imediatamente; autosave por célula; versão/conflitos; item completo com quantidade ou unitário zero; despesa completa apenas com fornecedor e valor > 0.
6. Rascunho com valor financeiro válido entra no realizado, mas não em lote; linhas de orçamento em rascunho não entram no orçado.
7. Alteração de orçamento com histórico de qualquer despesa exige justificativa; edição de despesa pós-lote exige justificativa; inativos bloqueados.
8. Inativação de etapa com qualquer despesa ativa é proibida; com todas inativas é permitida com justificativa, preserva status individual; reativação com observação.
9. Inativação de linha `Orcamento` mantém vínculo `Despesa.orcamento` e desloca despesa ativa apenas visualmente para área geral; reativação restaura posição; sem duplicar somas.
10. Etapas/itens inicialmente A–Z, reordenação manual por arrastar/salvar, restauração A–Z, nova linha ao fim da ordem manual; grupo Taxas sempre primeiro.
11. Despesas por fornecedor A–Z por padrão, cabeçalhos com alternância de ordenação e filtros individuais; **filtrar não recalcula totais** nem movimenta registros entre grupos.
12. Taxa: todas as despesas selecionadas são base; percentual capturado do projeto; fórmula Decimal; ajuste pré-confirmação exige justificativa; **proibir edição após confirmar**; taxa visual como primeiro grupo, **orçado=realizado**, saldo=0, sem despesa artificial nem duplicação no total.
13. Envio com todos os elegíveis marcados; desmarcados excluídos do lote; lote com snapshots/autor/data; concorrência não duplica envio.
14. Snapshot imutável e PDF reconstruído em memória, incluindo taxa; nenhuma geração salva arquivo.
15. Reenvio automático após falha confirmada (3 horas, 3 retries além do inicial), manual para qualquer lote, tentativas concorrentes bloqueadas e incertezas tratadas.
16. Relatório por período com filtro inclusivo da data do lote e limite por projeto; placeholders de Relatórios Gerais e Diretoria.
17. Inativação sempre lógica; condições de justificativa/reativação; auditoria completa.
18. Execução Windows/Waitress e Linux/Gunicorn, management command agendado, MySQL/MariaDB e WeasyPrint; documentação e checks de segurança.

## 16. Ordem de implementação

1. Configuração Django + MySQL/MariaDB, custom user, permissões, layout, coleção `utils/` e padrão de código; testes.
2. Projeto/ProjetoEmail/**taxa_servico** e **Etapa**; tela de projeto com quatro abas; testes.
3. Modelar **Orcamento como linha orçada da Etapa**, planilha rascunho/autosave, A–Z e arrastar/soltar, auditoria e testes.
4. Modelar **Despesa ligada à Etapa e opcionalmente a Orcamento**; tela Geral hierárquica, despesas de linhas inativas, filtros sem recalcular totais, testes.
5. Lotes com seleção por checkbox, cálculo/ajuste justificado da taxa, snapshot, PDF em memória e e-mails.
6. Management command independente de sistema operacional, tentativas automáticas/manuais e histórico de envios.
7. Relatório por período, páginas “Em desenvolvimento”, revisão de identidade, testes integrados, documentação Windows/Linux e instruções de produção.

Cada etapa deve deixar a aplicação executável, migrada, testável e utilizável; não entregar somente estrutura vazia.

## 17. Critérios de entrega

Entregar código funcional, migrations, testes, configuração por ambiente, `.env.example`, lista de dependências, scripts Windows/Linux, comandos de startup, processamento de e-mails, orientação para servidor HTTPS, documentação de backup **do banco e snapshots históricos** (não de PDFs), instruções de instalação do WeasyPrint em ambas as plataformas e README objetivo.

Requisitos finais: nenhuma dependência de Docker/Celery/Redis; não gravar PDFs no disco/banco; autorização verificada no backend; nenhuma exclusão física de registros de negócio; usabilidade semelhante a planilha; integridade de projeto/etapa/orçamento/despesas/lotes e taxa; histórico e reenvios auditáveis. Usar teste SMTP fake ou backend de console no desenvolvimento, sem enviar e-mails reais nos testes.

## 18. Pendências não decididas — defaults provisórios para V1

**Não tratar estes defaults como decisões do usuário**; documentar e permitir revisão:

1. **Relatório de Despesas por Período:** usar dados originais dos snapshots ou atuais das despesas. Default provisório: snapshots.
2. **Colunas finais de PDFs:** ainda não aprovadas em definitivo. Default: data do lote, etapa, item, fornecedor, NF, data NF, valor, subtotal e totais; incluir taxa no relatório do lote.
3. **Modo “Gerar e enviar” sem e-mail cadastrado:** apesar de destinatários temporários permitidos, não foi aprovada habilitação com zero e-mails ativos. Default conservador: exigir um e-mail ativo cadastrado para habilitar o modo, permitindo adicionar temporários.
4. **Despesa reativada que já pertence a lote:** manter vínculo e snapshot, não torná-la novamente pendente; permitir auditoria entre valores atuais e históricos.
5. **Backups e retenção de logs/auditoria:** definir política futura. Preservar registros históricos e não oferecer exclusão física.
6. **Identidade Ferezini:** se logo inacessível, não deduzir paleta, manter CSS tematizável e marca textual provisória.
7. **Reenvios automáticos:** 3 reenvios **além** do inicial, 4 possíveis tentativas automáticas totais, conforme interpretação anterior.
8. **Filtro que não encontra despesas em uma etapa:** ainda não escolhida a política de manter/ocultar/recolher. Default prudente: manter etapas e linhas orçadas visíveis, filtrar apenas despesas, com totais preservados.
9. **Padrão de docstrings e comentários:** definir futuramente; default: comentários somente para explicar escolhas não óbvias e docstrings em operações relevantes.
10. **Percentual máximo permitido para taxa de serviço:** ainda não estabelecido. Validar percentual não negativo; não impor limite comercial arbitrário, documentar necessidade de definição antes da produção.

## 19. Padrões obrigatórios de código — Zen of Python e utilitários

Seguir PEP 8, PEP 20 (Zen of Python) e as convenções nativas do Django. Prioridades: **bonito, explícito, simples, legível, plano em vez de aninhado, erros não silenciosos**. Evitar “rodeios”: nenhum wrapper trivial, camada vazia, função intermediária redundante, sobreengenharia ou consulta repetida sem necessidade. Código direto **não** significa omitir verificações, auditoria, segurança, desempenho ou clareza.

**Organização obrigatória:**

```text
utils/                         # coleção global de utilitários reutilizáveis
    __init__.py
    datas.py
    documentos.py
    formatacao.py
    arquivos.py                # somente quando necessário
apps/
    projetos/utils.py         # auxiliares específicos deste app, se necessários
    orcamentos/utils.py       # auxiliares específicos deste app, se necessários
    despesas/utils.py         # auxiliares específicos deste app, se necessários
    envios/utils.py           # auxiliares específicos deste app, se necessários
```

- `views.py`: **somente funções/classes de view**, pontos de entrada HTTP e orquestração curta; proibir helpers independentes definidos em `views.py`.
- `apps/<app>/utils.py`: funções auxiliares nichadas/específicas do próprio app. Não duplicar em `utils/` global.
- `utils/*.py` na raiz: funções **genuinamente genéricas** úteis em diferentes apps; organizar cada arquivo por finalidade. Não colocar regras de negócio de etapa, orçamento, despesa, lote e taxa na coleção global.
- `models.py`: estrutura, relacionamentos, invariantes naturais de cada entidade. `services/` só quando operações transacionais/fluxos importantes justificarem essa divisão; evite fazer tudo passar por camadas desnecessárias.
- Não introduzir funções auxiliares apenas para encapsular uma expressão simples uma única vez. Preferir nomes autoexplicativos, retorno antecipado, poucas condições aninhadas, queries otimizadas (`select_related`, `prefetch_related`), tratamento específico de exceções e testes das regras críticas.
- Não engolir erros (`except Exception: pass`) nem fazer logs com dados sensíveis. Não trocar legibilidade por código excessivamente condensado; a solução mais simples **correta** prevalece sobre abstração cosmética.

**Exemplo de localização:** `calcular_taxa_servico()` específico do app de envios → `apps/envios/utils.py`; normalização de CPF/CNPJ reutilizada por projeto e fornecedor → `utils/documentos.py`; uma view responsável por retornar HTTP → `apps/<app>/views.py`.
