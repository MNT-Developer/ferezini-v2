# 013 — Versionamento e consolidação

[Guia](001_GUIA_DA_DOCUMENTACAO.md) · Marco documental: **1.0.0**, em **24/11/2026**.

## Regra definida para o projeto

Formato de três inteiros: **[NOVOS MÓDULOS].[NOVAS FUNÇÕES EM MÓDULOS EXISTENTES].[PEQUENOS AJUSTES E CORREÇÕES]**.

| Campo alterado | Situação | Exemplo a partir de 1.0.0 |
| --- | --- | --- |
| Primeiro | Novo módulo do sistema | 2.0.0 |
| Segundo | Nova função em módulo existente | 1.1.0 |
| Terceiro | Pequeno ajuste ou correção | 1.0.1 |

Ao incrementar um campo, os da direita voltam a zero. Para uma entrega com várias mudanças, usar a categoria de maior alcance. Essa é a convenção do projeto; não substituir o primeiro campo automaticamente pelo critério de incompatibilidade de outras convenções de versionamento.

O salto de 0.x.x para **1.0.0** é o marco explicitamente solicitado de encerramento do desenvolvimento e consolidação das entregas existentes. Não representa a criação de um módulo por código nesta operação. Versão do produto, `versao` de concorrência nos registros e `versao_layout` dos lotes são conceitos independentes.

Novos documentos de versão exigem solicitação explícita. Um trabalho de documentação não autoriza mudar constantes, telas, layouts persistidos, dependências, schema ou banco. Esta consolidação altera somente Markdown.

## Rastreabilidade das versões 0.x.x

| Histórico | Entregas / resultado vigente |
| --- | --- |
| [0.0.1](../.codex/versao/v.0.0.1.md) | Especificação inicial: módulos, planilha, integridade, auditoria, lotes e fila. Planos não implementados não são promovidos a funcionalidades |
| [0.0.2](../.codex/versao/v.0.0.2.md) | Admin, capa do projeto, orçamento exclusivo da etapa, grupos fechados, Demais Despesas, taxa única dinâmica e percentuais com duas casas |
| [0.0.3](../.codex/versao/v.0.0.3.md) | Ferramentas em .codex, configuração única, Linux/HostMídia/cPanel/Passenger e Cron; deixou de valer implantação paralela Hostinger/Windows produção |
| [0.0.4](../.codex/versao/v.0.0.4.md) | Linhas clicáveis, base da importação, moeda BR/huminize_extras, responsável FK, Administrativo, Gestão de Usuários, proteção da Diretoria e templates legíveis |
| [0.0.5](../.codex/versao/v.0.0.5.md) | Tamanho da obra, taxa como última linha, cabeçalho 75/25, rodapés, dados cadastrais na raiz e retirada de cópias no lote |
| [0.0.6](../.codex/versao/v.0.0.6.md) | Quatro cards finais e DATABASE_URL com dj-database-url |
| [0.0.7](../.codex/versao/v.0.0.7.md) | Login/senha sem caixa, mínimo seis e redefinição legada; ReportLab, ambiente sem DLL; importação Excel e lotes históricos sem taxa |
| [0.0.8](../.codex/versao/v.0.0.8.md) | Responsável automático, pastas/listagem com filtros e paginação 25; exportação XLSM com modelo e macros preservadas |

## Escolhas que prevalecem sobre documentos antigos

- ReportLab substitui WeasyPrint/Pango, inclusive o gerador dos PDFs.
- DATABASE_URL substitui variáveis DB_* e mantém conexão de 600 segundos.
- Dados cadastrais da obra vêm da raiz atual; notas/financeiro/destinatários confirmados continuam históricos.
- Taxa é editável na prévia com justificativa; importação histórica não acrescenta taxa.
- Formulário novo sem responsável atribui o cadastrante; não é uma migração de todos os antigos sem vínculo.
- Botão Importar deixou de ser apenas uma preparação visual e efetivamente importa.
- Exportação preserva macros e não significa que cada macro foi executada/homologada.
- Documentação técnica atual fica em `.documentacao`; versões/scripts/testes permanecem em `.codex`.

## Conteúdo da consolidação 1.0.0

README passa a explicar o produto e seu uso. A documentação técnica tem ordem de leitura, fluxos, regras, catálogo de funções, bibliotecas, configuração, testes e limitações. As oito versões antigas são preservadas como histórico; a nova [versão consolidada](../.codex/versao/v.1.0.0.md) remete à documentação atual.

As evidências funcionais herdadas são 215 testes Python/12 JavaScript e verificações locais. A validação específica desta consolidação é documental: referências, cobertura do catálogo, ordem/nomes, UTF-8 e comparação de integridade dos arquivos não Markdown. Não foram aplicadas migrações, alteradas credenciais, executado SMTP ou publicado o sistema.
