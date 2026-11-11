# Ferezini — Gestão Financeira de Obras · v.0.0.2

> **Data:** 11/11/2026  
> **Finalidade:** registrar as melhorias e os ajustes realizados em relação à especificação inicial.  
> **Documento de origem:** [`./codex/v.0.0.1.md`](v.0.0.1.md), também preservado em [`codex/v.0.0.1.md`](v.0.0.1.md).  
> **Idioma:** português brasileiro (`pt-BR`).

Este documento complementa a especificação V1 e registra o comportamento implementado até esta revisão. As alterações de interface solicitadas posteriormente prevalecem nos pontos indicados abaixo. As demais regras da V1 continuam aplicáveis.

O identificador **v.0.0.2** identifica este documento de evolução. Ele não altera retrospectivamente o layout `V1` dos lotes, seus snapshots ou seus valores históricos.

## 1. Comparativo das melhorias

| Área | Especificação inicial | Comportamento atual |
| --- | --- | --- |
| Django Admin | Usuário customizado e permissões definidos, sem detalhamento do painel técnico | Admin habilitado, com cadastro e edição do usuário personalizado |
| Identificação dos usuários no admin | Seção administrativa não especificada | Seção **Usuários e funcionários**, contendo **Funcionários** |
| Configurações do usuário | Cinco permissões cumulativas | Permissões disponíveis tanto na criação quanto na edição pelo admin, com filtros e auditoria |
| Formulário do projeto | Campos do modelo e interface geral definidos | Layout com larguras e ordem específicas, adaptado também à edição |
| Rótulos do projeto | Cliente contratante e Descrição | **Cliente** e **Observação**, preservando os nomes dos campos no banco |
| Status do projeto | Três estados permitidos | Novos projetos começam em **Em andamento**; status removido dos formulários de criação e edição |
| Orçamento da etapa | Gestão dentro da aba Orçamento | Tela exclusiva para os itens previstos de cada etapa |
| Criação de etapa | Cadastro da etapa | Redirecionamento automático para sua tela exclusiva de orçamento |
| Adição de orçamento | Inclusão de linhas previstas | Botão **Adicionar orçamento** dentro de cada etapa |
| Acesso à tela exclusiva | Não detalhado | Botão **Abrir orçamentos**, exclusivo da aba Orçamento |
| Abertura dos agrupamentos | Hierarquia expansível, sem padrão de abertura definido | Todos fechados inicialmente na tela do projeto; etapa aberta na tela exclusiva |
| Área geral da etapa | Despesas sem item ativo | Nome alterado para **Demais Despesas**, com resumo próprio |
| Resumo de Demais Despesas | Totais gerais previstos, sem detalhamento visual desse agrupamento | Orçado, realizado e saldo apresentados e atualizados no agrupamento |
| Taxa no envio | Taxa calculada e valor aplicado apresentados separadamente | Um único campo **Taxa**, preenchido e recalculado automaticamente |
| Alteração das despesas selecionadas | Seleção e prévia de taxa | Recálculo imediato no navegador, sem recarregar a página |
| Justificativa da taxa | Obrigatória quando o valor aplicado difere do calculado | Campo aparece quando necessário e é limpo ao mudar a seleção |
| Percentuais | Precisão decimal no backend | Exibição padronizada com duas casas decimais |
| Precisão no navegador | Cálculo financeiro autoritativo no backend | Cálculos e comparações monetárias da interface também usam precisão decimal com strings e `BigInt` |

## 2. Django Admin e configuração de usuários

### 2.1. Acesso administrativo

- Habilitado `django.contrib.admin` nas configurações do projeto.
- Registrada a rota `/admin/`.
- Registrado o modelo personalizado `Usuario` com `UserAdmin`.
- Aplicadas as migrações do admin e disponibilizados seus arquivos estáticos.
- Personalizados o título e o cabeçalho para a identidade textual Ferezini.
- Renomeada a seção do aplicativo de **Accounts** para **Usuários e funcionários**.
- A listagem de funcionários está disponível em `/admin/accounts/usuario/`.

### 2.2. Campos e configurações

O cadastro e a edição administrativa permitem configurar:

- Dados pessoais: usuário, nome, sobrenome e e-mail.
- Dados profissionais: telefone e cargo.
- Conta ativa e acesso técnico: membro da equipe, superusuário, grupos e permissões Django.
- As cinco permissões independentes do sistema:
  - Diretoria.
  - Gestão de funcionários.
  - Acesso geral.
  - Gestão de projetos.
  - Relatórios gerais.

A listagem ganhou filtros pelas permissões do sistema e busca também por telefone e cargo.

### 2.3. Proteções preservadas

- Funcionários não podem ser excluídos fisicamente pelo admin.
- Alterações administrativas são registradas na auditoria.
- A edição administrativa dos dados incrementa a versão do usuário.
- O conteúdo da senha e seu hash não são incluídos nos snapshots da auditoria central.
- O acesso técnico ao admin continua separado das permissões operacionais. Ser superusuário não concede automaticamente Diretoria ou acesso aos projetos na aplicação.
- Os registros financeiros continuam sendo gerenciados pelas telas e operações próprias da aplicação.

**Arquivos principais:** [`apps/accounts/admin.py`](../apps/accounts/admin.py), [`apps/accounts/apps.py`](../apps/accounts/apps.py), [`config/urls.py`](../config/urls.py) e [`config/settings/base.py`](../config/settings/base.py).

## 3. Formulário de criação e edição de projetos

### 3.1. Ordem e distribuição dos campos

O formulário foi reorganizado da seguinte maneira no desktop:

| Linha | Campo | Largura |
| --- | --- | --- |
| 1 | Nome da obra | Linha inteira |
| 2 | Cliente | Metade da linha |
| 2 | CPF/CNPJ | Metade da linha |
| 3 | Endereço da obra | Metade da linha, em textarea |
| 3 | E-mails de contato ativos | Metade da linha, em textarea |
| 4 | Taxa (%) | Um quarto da linha |
| 4 | Data de início | Um quarto da linha |
| 4 | Previsão de término | Um quarto da linha |
| 5 | Responsável técnico | Linha inteira |
| 6 | Observação | Linha inteira, em textarea |

O quarto espaço da linha 4 fica livre. Em telas pequenas, os campos são empilhados para manter a leitura e a edição adequadas.

### 3.2. Nomes apresentados na interface

- **Cliente contratante** passou a ser exibido como **Cliente**.
- **Descrição** passou a ser exibida como **Observação**.
- O campo de percentual passou a usar o rótulo **Taxa (%)**.
- Os campos persistidos continuam se chamando `cliente_contratante` e `descricao`; não houve renomeação dessas colunas.
- Endereço, e-mails e observação permanecem em textarea.

### 3.3. Status e datas de conclusão

- Novos projetos começam com `EM_ANDAMENTO`, apresentado como **Em andamento**.
- O campo `status` foi removido dos formulários de criação e edição.
- Enviar um campo `status` adicional nessas requisições não altera o estado do projeto.
- Editar os demais dados de um projeto preserva seu status atual.
- A data de conclusão também foi retirada desse formulário; o campo continua existindo no modelo.
- Os estados `EM_ANDAMENTO`, `CONCLUIDO` e `CANCELADO` foram preservados, sem criação de novos estados.

**Pendência:** a mudança de status por ações específicas foi indicada como o fluxo desejado. Os botões e endpoints dessas ações ainda não foram implementados nesta rodada.

**Arquivos principais:** [`apps/projetos/forms.py`](../apps/projetos/forms.py) e [`templates/projetos/form.html`](../templates/projetos/form.html).

## 4. Tela exclusiva de orçamento por etapa

### 4.1. Novo fluxo

1. O usuário cria uma etapa na tela do projeto.
2. Após a confirmação do cadastro pelo servidor, a aplicação abre a tela exclusiva do orçamento dessa etapa.
3. A etapa inicia expandida nessa tela, pronta para inclusão de itens.
4. O botão **Adicionar orçamento**, dentro da etapa, cria uma linha de orçamento em rascunho.
5. O foco é direcionado para a descrição da nova linha.
6. O usuário preenche as células com o autosave já existente.

Abrir a tela exclusiva não cria itens vazios automaticamente. A linha só é criada quando o usuário solicita **Adicionar orçamento**.

### 4.2. Acesso posterior

- A aba **Orçamento** apresenta **Abrir orçamentos** em cada etapa.
- Esse botão abre a mesma tela exclusiva usada após criar a etapa.
- O botão foi removido da aba **Geral**, conforme solicitado.
- A tela exclusiva possui um link de retorno à aba Orçamento da obra.
- A rota é `/projetos/<projeto_id>/etapas/<etapa_id>/orcamento/`.
- A tela exige autenticação e permissão operacional.
- Uma etapa de outro projeto não pode ser acessada pela combinação incorreta dos identificadores na URL.

### 4.3. Funcionalidades mantidas

- Salvamento por célula, versão e tratamento de conflito.
- Rascunhos progressivos.
- Justificativas condicionais e auditoria.
- Inativação e reativação segundo as regras existentes.
- Reordenação dos itens e restauração A–Z.
- Consulta de registros inativos, com edição bloqueada.
- Proteção contra navegar com células pendentes ou com erro.

**Arquivos principais:** [`apps/projetos/views.py`](../apps/projetos/views.py), [`apps/projetos/urls.py`](../apps/projetos/urls.py), [`templates/projetos/detalhe.html`](../templates/projetos/detalhe.html) e [`static/js/projeto.js`](../static/js/projeto.js).

## 5. Agrupamentos fechados por padrão

- Os agrupamentos da tela do projeto iniciam **fechados**.
- O padrão se aplica às etapas, aos itens, a Demais Despesas e ao grupo virtual Taxas de Serviço.
- O usuário pode abrir os agrupamentos que deseja consultar.
- O estado de abertura escolhido é mantido durante as atualizações da tela na mesma sessão da página.
- A tela exclusiva de orçamento da etapa é a exceção: a etapa inicia aberta para preenchimento.
- Ao adicionar uma linha de orçamento, sua etapa é aberta para permitir a edição do novo item.

## 6. Demais Despesas e seu resumo

### 6.1. Identificação

A antiga **Área geral da etapa** foi renomeada para **Demais Despesas** na aba Geral.

Esse agrupamento continua recebendo:

- Despesas sem vínculo com uma linha de orçamento.
- Despesas vinculadas a um item de orçamento inativo.

O deslocamento é apenas visual: os vínculos das despesas com seus itens são preservados.

### 6.2. Cálculo e apresentação

Demais Despesas agora apresenta o mesmo formato de resumo dos itens:

| Indicador | Regra |
| --- | --- |
| Orçado | Zero, pois o agrupamento não representa uma linha de orçamento ativa |
| Realizado | Soma das despesas ativas com valor informado nesse agrupamento, desde que a etapa esteja ativa |
| Saldo | Orçado menos realizado; pode ser negativo |

- Despesas em rascunho com valor válido entram no realizado, conforme a regra original.
- Despesas inativas não entram no cálculo, mesmo quando estão visíveis para consulta.
- Reativar um item devolve suas despesas ao agrupamento do item e atualiza Demais Despesas.
- Os valores são calculados no backend e retornados também nas respostas do autosave.
- O resumo é atualizado após salvar as células, sem exigir recarga completa.
- Os filtros de apresentação não recalculam o resumo nem os totais oficiais.
- As despesas não são duplicadas nos totais da etapa ou do projeto.

Exemplo: uma etapa com R$ 1.000,00 orçados, R$ 300,00 realizados em um item e R$ 200,00 em Demais Despesas apresenta:

- **Demais Despesas:** orçado R$ 0,00; realizado R$ 200,00; saldo −R$ 200,00.
- **Etapa:** orçado R$ 1.000,00; realizado R$ 500,00; saldo R$ 500,00.

**Arquivos principais:** [`apps/projetos/utils.py`](../apps/projetos/utils.py) e [`static/js/projeto.js`](../static/js/projeto.js).

## 7. Taxa única e recálculo imediato no envio de despesas

### 7.1. Apresentação simplificada

- A tela apresenta um único campo monetário **Taxa (R$)**.
- O campo já é preenchido com o cálculo correspondente às despesas inicialmente selecionadas.
- A taxa considera todas as despesas marcadas, independentemente da etapa ou do item.
- São apresentados o subtotal das despesas selecionadas e o total com taxa.
- A conferência e o relatório do lote passaram a exibir uma única linha de taxa, eliminando a apresentação duplicada de taxa calculada e aplicada.

Os campos históricos `valor_taxa_calculado` e `valor_taxa` continuam no backend para manter a rastreabilidade dos ajustes. A simplificação é da interface, sem perda dos dados de auditoria.

### 7.2. Comportamento por ação

| Ação do usuário | Resultado |
| --- | --- |
| Abrir a tela | Despesas elegíveis pré-selecionadas e taxa preenchida automaticamente |
| Marcar ou desmarcar uma despesa | Recalcular subtotal, taxa e total sem recarregar a página |
| Selecionar ou desmarcar todas | Aplicar o mesmo recálculo para a seleção completa |
| Informar taxa diferente da calculada | Exibir a justificativa e torná-la obrigatória |
| Retornar ao valor calculado | Ocultar a justificativa e limpar seu conteúdo |
| Mudar a seleção após ajustar a taxa | Descartar o ajuste, restaurar a taxa calculada e limpar a justificativa |
| Deixar nenhuma despesa selecionada | Exibir valores zerados e desabilitar a conferência |
| Receber erro de validação do servidor | Preservar o ajuste e o motivo para correção, até a próxima mudança de seleção |

### 7.3. Precisão e validação

- O navegador usa strings decimais e `BigInt` para o cálculo monetário.
- O arredondamento da taxa segue `ROUND_HALF_UP` para duas casas, em concordância com o backend.
- O backend continua recalculando e validando a seleção, a taxa e a justificativa.
- A validação não depende apenas de JavaScript.
- Após a confirmação, o lote permanece imutável, inclusive sua taxa.

**Arquivos principais:** [`apps/envios/forms.py`](../apps/envios/forms.py), [`static/js/envios.js`](../static/js/envios.js), [`templates/envios/painel.html`](../templates/envios/painel.html), [`templates/envios/confirmar.html`](../templates/envios/confirmar.html) e [`templates/envios/_itens_lote.html`](../templates/envios/_itens_lote.html).

## 8. Percentuais com duas casas decimais

- Padronizada a apresentação de percentuais com duas casas, por exemplo **10,00%** e **10,50%**.
- Aplicado ao campo de taxa do projeto, ao envio de despesas, à conferência, ao relatório do lote e à listagem de taxas na tela Geral.
- O campo numérico do projeto apresenta duas casas e incremento de `0,01`.
- Os percentuais persistidos e os snapshots históricos mantêm sua estrutura decimal existente; não houve migração de precisão dos modelos.
- Não foi estabelecido um novo limite comercial máximo para a taxa.

## 9. Implementação da base V1 e decisões técnicas

Os itens desta seção concretizam requisitos da especificação inicial ou registram escolhas técnicas feitas durante sua implementação. Não representam novas solicitações funcionais posteriores à V1.

### 9.1. Base funcional implementada

- Projeto Django com configurações separadas de desenvolvimento, produção e testes.
- Usuário customizado, autenticação, navegação por permissões e gestão de funcionários.
- Projetos, contatos, etapas, linhas de orçamento e despesas na modelagem definida pela V1.
- Interface hierárquica, filtros, ordenação, autosave, rascunhos e controle de versão.
- Regras de inativação lógica, reativação e justificativas.
- Auditoria central com antes/depois, operador e contexto da operação.
- Lotes com taxa, snapshots, confirmação transacional e proteção contra duplicidade.
- HTML e PDF gerados sob demanda, sem persistência dos PDFs.
- Fila de e-mails, tentativas, reenvios manuais e automáticos.
- Relatório por período com datas inclusivas dos lotes e valores históricos.
- Relatórios Gerais e Diretoria mantidos como páginas protegidas **Em desenvolvimento**.

### 9.2. Interface e dependências

- A preferência inicial por AG Grid Community foi avaliada; foram utilizadas tabelas HTML com JavaScript local e Bootstrap.
- Bootstrap foi disponibilizado localmente, com sua licença, sem depender de CDN durante o uso.
- A interface usa marca textual Ferezini e tema configurável, sem declarar cores como oficiais.
- O logo de referência não pôde ser acessado durante a implementação inicial.
- Colagem multicélula do Excel continua não implementada; a colagem de uma célula usa o navegador.

### 9.3. Integridade e concorrência

- Bloqueios transacionais coordenam edições, inativação de etapa e confirmação de lotes.
- Conflitos de versão impedem sobrescrita silenciosa.
- Atualizações e criações indiscriminadas em massa dos registros de negócio são bloqueadas para não contornar validação e auditoria.
- Snapshots e campos imutáveis dos lotes possuem proteção também contra atualizações por aliases de chaves estrangeiras.
- O lote original de uma despesa confirmada não pode ser removido ou transferido.
- A confirmação usa identificador de idempotência e uma prévia assinada com prazo de validade.
- Foram tratados valores não finitos, identificadores inválidos e limites de datas dos relatórios.
- A edição de funcionários preserva os campos técnicos atuais do registro bloqueado, evitando sobrescrita por um formulário desatualizado.

### 9.4. Segurança do processamento de e-mails

- SMTP não é chamado durante a requisição de confirmação do lote.
- Há reserva exclusiva e persistente por tentativa.
- A reserva é revalidada antes da transmissão, inclusive após a geração do PDF.
- Reservas interrompidas são tratadas como resultado incerto, sem repetição automática cega.
- Uma reserva renovada não é invalidada indevidamente pela recuperação de reservas expiradas.
- Recusas parciais de destinatários são registradas; o sistema não repete automaticamente para quem pode já ter sido aceito.
- Reenvio manual bem-sucedido cancela pendências automáticas.
- Falha de reenvio manual preserva o envio inicial ou automático ainda pendente.
- As três repetições automáticas continuam sendo adicionais à tentativa inicial, com intervalo de três horas após falha confirmada.

### 9.5. Instalação e operação

- Scripts de instalação e inicialização para Windows e Linux.
- Integração documentada com Waitress/NSSM e Task Scheduler no Windows; Gunicorn/systemd ou cron no Linux.
- Instalador opcional de bibliotecas PDF isoladas na `.venv`, usando pacote oficial WeasyPrint 70.0 e verificação SHA256.
- Detecção das DLLs locais na configuração Django e cache de fontes na `.venv`.
- Orientações para HTTPS, configuração de SMTP, backup e restauração do banco e dos snapshots.
- Dependências diretas fixadas e registro do ambiente Windows validado.
- `.env.example` sem segredos e arquivos locais de configuração ignorados pelo controle de versão.
- Comando `criar_gestor` para criar o primeiro acesso operacional e `createsuperuser` para o acesso técnico ao admin.
- Validação de CPF e CNPJ, incluindo CNPJ alfanumérico.
- MySQL/MariaDB como configuração padrão; SQLite apenas como opção explícita de desenvolvimento/testes, bloqueado em produção.

## 10. Validação desta revisão

Na consolidação deste documento, foram executados:

| Verificação | Resultado |
| --- | --- |
| Suíte Django com MySQL e geração real de PDF habilitados | **86 testes passaram, sem testes ignorados** |
| Suíte JavaScript de formatação, cálculo de taxa e interação com a seleção | **7 testes passaram** |
| Checks do Django durante a suíte | Sem problemas identificados |

Os testes MySQL utilizaram um banco temporário de nome exclusivo, verificado como inexistente antes da execução e removido ao final. Não foram usados dados reais como fixtures e não houve envio de e-mails reais.

Além da cobertura original, foram adicionadas verificações para:

- Admin, identificação dos funcionários, permissões e bloqueio de exclusão.
- Cadastro e edição de configurações do usuário com auditoria.
- Status padrão e preservação do status na edição do projeto.
- Tela exclusiva da etapa, autorização, vínculo com o projeto e ausência de criação automática de itens vazios.
- Taxa inicial da seleção e justificativa obrigatória no servidor.
- Recálculo por checkbox, seleção de todas, limpeza do ajuste e preservação após erro.
- Precisão monetária acima dos limites de `Number` e arredondamento decimal.
- Resumo de Demais Despesas, rascunhos, itens inativos, reativação e atualização pelo autosave sem duplicar totais.

O relatório [`docs/validacao.md`](../docs/validacao.md) preserva a evidência da validação inicial de 74 testes Django e três JavaScript. Os números desta seção correspondem à suíte ampliada desta revisão.

## 11. Pendências e limites preservados

- Implementar o fluxo de ações específicas para concluir ou cancelar projetos, conforme indicação posterior do usuário.
- Homologar visualmente as telas, incluindo mobile, foco, arrastar/soltar e filtros: a ferramenta de navegador estava indisponível na validação automatizada inicial.
- Conferir a aparência dos PDFs; a geração real em memória e o retorno HTTP foram testados, mas a revisão visual permanece pendente.
- Homologar Linux/Gunicorn, MariaDB, SMTP real, proxy HTTPS, NSSM/Task Scheduler e systemd nos ambientes de destino.
- Definir a identidade visual oficial e disponibilizar o logo aprovado.
- Definir política de backup, retenção e responsáveis, além de eventual limite comercial do percentual.
- Manter registradas as decisões provisórias da seção 18 da V1 em [`docs/decisoes_pendentes.md`](../docs/decisoes_pendentes.md): snapshots no relatório por período, colunas finais dos PDFs, exigência de contato ativo no primeiro envio, reativação com preservação do lote e demais defaults ainda não aprovados em definitivo.
- Relatórios estratégicos e colagem multicélula não foram acrescentados nesta revisão.

## 12. Regras que continuam inalteradas

- Modelagem `Projeto → Etapa → (Orcamento, Despesa)`, sem `ItemOrcamento`.
- Despesa vinculada obrigatoriamente à etapa e opcionalmente a um item da mesma etapa.
- Ausência de `projeto` e `data_envio` duplicados na despesa.
- Cinco permissões independentes e cumulativas, validadas no backend.
- Cálculos monetários com Decimal, sem uso de float no backend financeiro.
- Inativação lógica e preservação dos vínculos e históricos.
- Snapshots e taxas de lotes confirmados imutáveis.
- Taxas virtuais somadas igualmente ao orçado e ao realizado, sem mudar o saldo.
- PDFs exclusivamente em memória, sem armazenamento permanente.
- Ausência de dependências obrigatórias de React, Vue, Docker, Redis, Celery ou APIs externas para o uso da aplicação.

O guia operacional atualizado permanece no [`README.md`](../README.md), e as versões técnicas estão em [`docs/dependencias.md`](../docs/dependencias.md).
