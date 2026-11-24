# 001 — Guia da documentação

Base consolidada: **1.0.0**, em **24/11/2026**. A publicação encerra documentalmente a fase 0.x.x. Não modifica código, dependências, configuração, planilhas, banco ou implantação. Identificadores antigos eventualmente exibidos pelo aplicativo não foram reescritos.

O [README](../README.md) é o guia de uso. Esta pasta é a referência técnica atual. Os documentos 0.x.x em `.codex/versao/` continuam como histórico, inclusive quando descrevem escolhas posteriormente substituídas.

## Ordem de leitura

| Documento | Objetivo |
| --- | --- |
| [002 — Arquitetura e dependências](002_ARQUITETURA_E_DEPENDENCIAS.md) | Organização e bibliotecas |
| [003 — Modelos e regras](003_MODELOS_E_REGRAS_DE_DADOS.md) | Relações, validações e histórico |
| [004 — Autenticação e usuários](004_AUTENTICACAO_PERMISSOES_E_USUARIOS.md) | Senhas, acessos e equipe |
| [005 — Projetos e financeiro](005_PROJETOS_ETAPAS_ORCAMENTOS_E_DESPESAS.md) | Cadastro, navegação, células e totais |
| [006 — Envios e fila](006_ENVIOS_TAXAS_E_FILA_DE_EMAILS.md) | Lotes e processamento de e-mails |
| [007 — Relatórios e auditoria](007_RELATORIOS_PDF_E_AUDITORIA.md) | Fontes de dados e rastreabilidade |
| [008 — Excel](008_IMPORTACAO_E_EXPORTACAO_EXCEL.md) | Mapeamento e macros |
| [009 — Interface](009_INTERFACE_TEMPLATES_E_JAVASCRIPT.md) | Templates, JavaScript e eventos |
| [010 — Configuração e operação](010_CONFIGURACAO_INSTALACAO_E_OPERACAO.md) | Instalação, atualização e manutenção |
| [011 — Validação e limites](011_TESTES_VALIDACAO_E_LIMITACOES.md) | Evidências e pendências |
| [012 — Funções](012_REFERENCIA_DE_FUNCOES.md) | Finalidade de cada função própria |
| [013 — Versionamento](013_VERSIONAMENTO_E_CONSOLIDACAO.md) | Regra numérica e consolidação histórica |

Para mudar uma regra, leia seu fluxo, os modelos e o catálogo de funções. Os links ao código são relativos à raiz. Os comandos são instruções de operação posterior; não foram executados nesta consolidação.

## Vocabulário

| Termo | Significado |
| --- | --- |
| Projeto / obra | Cadastro raiz do acompanhamento |
| Etapa | Grupo de trabalho de uma obra |
| Orçamento / item | Linha prevista de quantidade e preço |
| Despesa / nota | Gasto real, com orçamento opcional |
| Rascunho | Registro ainda incompleto |
| Lote | Confirmação histórica de notas e taxa |
| Snapshot | Nota congelada na confirmação |
| Tentativa | Uma operação de envio por e-mail |
| Versão do registro | Inteiro de concorrência; diferente da versão do produto |

Consolidação não significa implantação remota ou homologação de execução das macros. Consulte os limites no documento 011.
