# Decisões pendentes da V1

Os defaults abaixo são provisórios, conforme a seção 18 da especificação. Não representam novas decisões do usuário.

1. Relatório de período usa os snapshots originais dos lotes; valores atuais continuam consultáveis na obra e na auditoria.
2. PDF de período usa data do lote, etapa, item, fornecedor, NF, data NF e valor; PDF do lote inclui percentual e taxa aplicada. Colunas finais aguardam aprovação.
3. Gerar e enviar exige ao menos um e-mail ativo cadastrado no projeto, além de permitir destinatários temporários. Reenvios permitem destinatários originais/temporários.
4. Reativação de despesa mantém lote e snapshot; não volta a pendente.
5. Histórico e auditoria são preservados sem exclusão. Retenção, responsáveis e periodicidade de backups precisam ser definidos antes da produção.
6. Marca textual Ferezini e tema neutro configurável: a URL do logo não pôde ser acessada na implementação. Cores não são declaradas oficiais.
7. Há três reenvios automáticos além do inicial, separados por três horas após cada falha confirmada. Resultado incerto suspende automação.
8. Filtros mantêm etapas e itens visíveis e ocultam somente despesas; totais oficiais não mudam.
9. Docstrings em operações relevantes e comentários somente para escolhas não óbvias.
10. Taxa aceita percentual não negativo, dentro da capacidade técnica do DecimalField; não foi imposto teto comercial arbitrário.

## Escolhas técnicas da implementação

A preferência por AG Grid Community foi avaliada. Sua hierarquia exige composição adicional e colagem avançada tem limitações de licença. A V1 usa tabelas HTML acessíveis, Bootstrap 5 e JavaScript local, com filtros, ordenação, células editáveis e arrastar/soltar sem recursos Enterprise. Colagem multicélula do Excel não foi implementada; a colagem de uma célula usa o comportamento nativo do navegador.

Na v.0.0.3, SQLite fica restrito aos testes isolados em memoria. Desenvolvimento local e producao usam MySQL/MariaDB com o mesmo modulo config.settings.
