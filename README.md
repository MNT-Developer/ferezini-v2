# Ferezini — Gestão Financeira de Obras

O Ferezini organiza o acompanhamento financeiro de obras: o que foi previsto, o que já foi gasto e quais despesas ainda precisam ser apresentadas ao cliente. Cada projeto reúne seus dados, responsáveis, etapas, orçamentos, notas e relatórios em um só lugar.

A **versão 1.0.0** consolida as funcionalidades construídas durante a fase de desenvolvimento.

## Para que serve

- Cadastrar obras, clientes, contatos e responsáveis técnicos.
- Planejar custos por etapa e acompanhar as despesas de cada orçamento.
- Comparar valores orçados e realizados e consultar o saldo da obra.
- Preparar relatórios de despesas, aplicar a taxa de serviço e solicitar envio por e-mail.
- Consultar envios anteriores e o histórico de alterações.
- Trazer um acompanhamento do Excel ou exportar a obra para a planilha com macros.
- Gerenciar usuários e acessos conforme a função de cada pessoa.

## Primeiro acesso

Abra o endereço do sistema informado pela organização e entre com o usuário e a senha fornecidos. Usuário e senha não diferenciam maiúsculas de minúsculas. Novas senhas precisam ter pelo menos seis caracteres.

Se aparecer uma solicitação de redefinição, cadastre a nova senha para continuar. Caso não consiga entrar, procure o responsável pela gestão dos usuários.

O menu apresenta as áreas permitidas para seu perfil. A página Início mostra os projetos e quatro indicadores: total cadastrado, projetos em andamento, quantidade e valor das notas aguardando envio.

## Cadastrar e encontrar uma obra

1. Acesse **Projetos → Novo projeto**.
2. Preencha nome da obra e os dados disponíveis de cliente, endereço, tamanho, taxa e contatos.
3. Selecione o responsável técnico ou deixe em branco para atribuir a obra a você.
4. Clique em **Salvar projeto**. Novas obras começam em andamento.

Em **Por responsável**, abra a pasta de uma pessoa e escolha **Em Andamento** ou **Finalizadas**. Finalizadas reúne projetos concluídos e cancelados. Obras antigas sem responsável aparecem em **Sem responsável**.

Em **Todos os projetos**, consulte a lista geral. As tabelas mostram 25 projetos por página e permitem filtrar por título e cliente. Clique na linha de uma obra para abri-la.

Quem tem acesso a projetos pode fazer o primeiro vínculo de uma obra antiga sem responsável. Depois de vincular, sua substituição ou remoção exige acesso de Diretoria ou Administrativo.

## Planejar e registrar os gastos

Crie as etapas do trabalho na obra. Ao criar uma etapa, sua tela de orçamento é aberta para incluir os itens previstos, com descrição, quantidade, unidade e preço. O acesso posterior fica na aba **Orçamento**.

Na aba **Geral**, abra os agrupamentos para consultar ou lançar despesas. Cada nota pode pertencer a um orçamento ou ficar diretamente na etapa, em **Demais Despesas**. Informe os dados disponíveis: fornecedor, nota ou pedido, emissão, vencimento, valor e observação.

As células são salvas ao sair do campo. Confira as mensagens de salvamento e resolva os erros antes de sair da tela. Registros incompletos podem permanecer como rascunho; notas precisam de fornecedor e valor positivo para entrar no envio.

Alterações em despesas já confirmadas ou em orçamentos que têm despesas exigem justificativa. Inativar preserva o histórico; reativar uma nota já enviada não a torna disponível para outro envio.

## Preparar e enviar despesas

1. Abra **Envio de Despesas** dentro da obra.
2. Selecione as notas. Taxa e total são recalculados conforme a seleção.
3. Se alterar a taxa sugerida, informe a justificativa. Mudar novamente a seleção recalcula e limpa o ajuste anterior.
4. Escolha gerar o relatório ou gerar e solicitar envio por e-mail. Para enviar, a obra precisa de ao menos um contato ativo e destinatários selecionados.
5. Confira a prévia e confirme.

A confirmação cria um lote: um grupo de notas com valores e data registrados. Baixe novamente o relatório no histórico dos envios. O e-mail é processado pela rotina da organização; acompanhe sua situação no sistema. A aceitação pelo serviço de e-mail não garante entrega na caixa de entrada ou leitura.

Se o resultado for incerto, confira com o responsável antes de solicitar outro envio. Reenviar reutiliza o lote e não duplica as notas.

## Consultar relatórios e histórico

O **Relatório de Despesa** da obra consulta um período e permite baixar o PDF dos lotes confirmados nessas datas. O histórico identifica quem alterou um registro e a justificativa informada.

A identificação da obra nos relatórios acompanha seu cadastro atual. Notas e valores confirmados no lote permanecem históricos.

## Usar o acompanhamento em Excel

**Importar:** em Início ou Projetos, clique em **Importar** e escolha `.xlsm`, `.xlsx` ou `.xls` com as abas **Painel**, **Serviços e Custos** e **Projeto**. A importação cria uma obra, atribui você como responsável e organiza etapas, orçamentos, despesas e envios históricos. Reenviar um arquivo idêntico já importado abre a obra existente. Confira os avisos ao concluir.

Envios históricos importados não recebem taxa adicional; novos envios calculam a taxa normalmente. Quando for solicitado, recalcule e salve a planilha no Excel antes de tentar importar novamente.

**Exportar:** no detalhe da obra, clique em **Exportar XLSM**. A primeira despesa fica na linha do orçamento e as demais nas linhas abaixo. O arquivo mantém as macros e os botões do modelo de acompanhamento do sistema; não é uma cópia de qualquer planilha enviada anteriormente.

Use descrições distintas para os orçamentos da mesma etapa se precisar exportar e reimportar. A planilha não substitui uma cópia completa dos registros do sistema. Os campos atendidos e limites do modelo estão na documentação de referência.

## Gerenciar a equipe

Em **Gestão de Usuários**, pessoas autorizadas podem cadastrar, editar, inativar e reativar usuários. A lista permite pesquisar, filtrar a situação e navegar em páginas de 25 registros. Deixe Nova senha em branco na edição para manter a senha atual.

Somente a Diretoria ou um administrador técnico autorizado pode gerenciar contas da Diretoria ou conceder esse acesso. Contas de administrador técnico são gerenciadas separadamente da lista operacional.

## Abrangência e documentação

**Relatórios Gerais** e **Diretoria** ainda exibem telas de funcionalidades em desenvolvimento. Os fluxos disponíveis são o acompanhamento por obra, seus relatórios de despesas e a gestão de usuários descritos neste guia.

A documentação de referência começa no [guia de documentação](.documentacao/001_GUIA_DA_DOCUMENTACAO.md), com regras, fluxos e orientações para a equipe que mantém o sistema.
