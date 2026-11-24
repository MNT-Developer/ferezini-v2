# 007 — Relatórios, PDF e auditoria

[Guia](001_GUIA_DA_DOCUMENTACAO.md) · [Relatórios](../apps/relatorios/) · [PDF](../utils/pdf.py) · [Auditoria](../apps/auditoria/).

## Fonte de verdade

| Conteúdo | Fonte |
| --- | --- |
| Nome/cliente/endereço/tamanho da obra | Projeto atual, consultado novamente ao gerar PDF |
| Nota, fornecedor, item/etapa, valor confirmado | LoteEnvioItem.dados_snapshot e valor_snapshot |
| Percentual/taxa aplicada/total do lote | Lote confirmado |
| Destinatários | Lote e tentativa histórica |
| Financeiro atual na tela da obra/Excel | Cadastros atuais ativos, conforme regras dos respectivos serviços |

A edição justificada de uma despesa não reescreve seu snapshot. A remoção das cópias cadastrais na migração envios.0002 preservou notas e destinatários. Dados atuais de projeto e histórico financeiro não devem ser confundidos.

## Relatório de lote

`envios.pdf` verifica acesso e obtém o lote no projeto. `gerar_pdf_lote` recarrega a raiz e chama `gerar_relatorio_pdf` com itens históricos, total, taxa e confirmação. Lote importado passa `exibir_taxa=False`. Downloads e anexos usam o mesmo gerador em memória.

## Relatório por período

`relatorios.despesas` valida PeriodoForm. `limites_periodo` converte início à meia-noite e fim ao início do dia seguinte, em America/Sao_Paulo. O intervalo é início inclusivo/fim exclusivo; não depende da emissão ou vencimento da nota.

`despesas_por_periodo` consulta lotes confirmados no período, itens e valores congelados. Soma cada taxa uma vez por lote, evitando multiplicação por quantidade de itens. `gerar_pdf_periodo` recarrega a obra atual antes da renderização. Só lotes importados ocultam a linha de taxa automática; em período misto, considera as taxas dos normais. Período vazio é válido.

## Layout vigente

ReportLab produz A4 paisagem com fontes Vera do pacote, margens reduzidas, cabeçalho, título e grade 2×2 sem título de coluna: Cliente/Tamanho na primeira linha, Endereço/Valor na segunda; larguras 75%/25%. Valor já inclui a taxa.

As notas mantêm cabeçalho repetido e linhas inteiras entre páginas. Quando aplicável, Taxa de Serviço é a última linha da tabela, na coluna Fornecedor, sem preenchimento de fundo. Lote usa Confirmação à esquerda do rodapé; período usa seu intervalo. Página X de Y fica à direita. A coluna monetária foi ampliada para valores grandes.

O gerador escapa texto inserido em parágrafos; não busca imagens/fontes remotas, não usa conversor externo e não persiste o PDF. `gerar_pdf_teste` valida a instalação. Templates antigos `*_impressao.html` são referência histórica: o PDF efetivo é definido em utils/pdf.py.

## Auditoria

`registrar` recebe usuário, objeto, ação, anteriores/novos, justificativa e correlação. Resolve o projeto por relações conhecidas e grava HistoricoAlteracao. Serviços o chamam na mesma transação da alteração. Importação e confirmação de lote usam correlação para agrupar registros relacionados.

O histórico é imutável pelo modelo/queryset. Senhas são representadas por uma descrição de mudança, nunca seu conteúdo ou hash na auditoria. A tela de histórico do projeto permite filtro de entidade/ID e paginação de 100 registros; dados detalhados ficam em estruturas antes/depois.

Funções auxiliares de valores/documentos: `monetario` arredonda em centavos; `formatar_numero_br` fornece milhares/ponto e decimal/vírgula com duas casas; `numero_br` expõe esse comportamento na biblioteca Django **huminize_extras**, registrada também nos settings. `validar_documento` valida CPF/CNPJ; `chave_alfabetica` normaliza ordenação sem acentos. Seus contratos individuais constam do [012](012_REFERENCIA_DE_FUNCOES.md).
