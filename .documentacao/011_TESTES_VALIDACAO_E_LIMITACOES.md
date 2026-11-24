# 011 — Testes, validação e limitações

[Guia](001_GUIA_DA_DOCUMENTACAO.md) · Base consolidada 1.0.0 em 24/11/2026.

## Evidência herdada

A última validação funcional da v.0.0.8 registrou **215 testes Python com MySQL temporário e PDFs reais** e **12 testes JavaScript**, além de checks Django, ausência de novas migrações, formatação dos 34 templates e diff de whitespace. São evidências da implementação anterior, não uma execução repetida nesta consolidação documental.

Foram conferidos visualmente telas desktop/móvel e relatórios. O XLSM sintético abriu no Excel com dez abas e VBA reconhecidos, macros/eventos desabilitados e links sem atualização. Recálculo confirmou orçado R$ 470,00 e realizado R$ 650,60. Macros/desenhos foram comparados byte a byte com o modelo. O arquivo teste.xlsm da importação resultou em duas etapas, quatro orçamentos, duas notas e lote R$ 853.000,00 sem taxa automática.

## Mapa dos testes

| Fonte | Cobertura |
| --- | --- |
| `apps/accounts/test_*` e `tests.py` | Login, senhas, migração, usuários, Diretoria, admin e privilégios |
| `apps/projetos/tests.py` | Modelagem, cálculos, escrita, validação, auditoria e concorrência |
| `test_responsavel.py` | Seleção, atribuição, edição, autorização e migração |
| `test_lista.py` | Pastas, filtros, paginação, legado e acesso |
| `test_importacao.py` | Três formatos, fórmulas salvas, células, rollback e idempotência |
| `test_exportacao.py` | Mapeamento inverso, notas adicionais, caches, taxas e preservação XLSM |
| `apps/envios/tests.py`, `test_migracoes.py` | Lotes, idempotência, snapshots, fila/SMTP e remoção das cópias cadastrais |
| `apps/relatorios/tests.py` | Período, fuso, soma de taxas e dados atuais da raiz |
| `apps/core/tests.py`, `test_pdf.py` | Cards, acesso e PDF efetivo |
| `.codex/tests_deploy.py` | Settings, entrypoint, instalador, estáticos e produção |
| `.codex/tests/*.test.cjs` | Precisão decimal, taxa dinâmica e modal de colaborador |

Testes/fixtures e métodos `test_*` verificam comportamento; não são APIs operacionais do sistema. O catálogo 012 cobre funções próprias de runtime/manutenção, não replica o catálogo de cada asserção da suíte.

## Como executar futuramente

```powershell
.\.venv\Scripts\python.exe .codex/scripts/testar.py
.\.venv\Scripts\python.exe .codex/scripts/testar.py --mysql --pdf-real
node --test .codex/tests/formatacao.test.cjs .codex/tests/envios.test.cjs .codex/tests/responsavel-tecnico.test.cjs
.\.venv\Scripts\python.exe .codex/scripts/formatar_templates.py --check
```

O modo padrão usa SQLite em memória; não prova bloqueios MySQL. O runner MySQL gera nome aleatório, verifica inexistência e remove somente o banco temporário criado. É necessária conta de testes com privilégios adequados; não apontar para banco de produção. Emails de teste usam backend em memória. xlwt opcional gera fixture XLS, que é pulada se a ferramenta não estiver instalada. Outros skips dependem do backend e da presença do arquivo de exemplo.

## Limites preservados

- Relatórios Gerais e Diretoria têm páginas placeholder, não relatórios estratégicos implementados.
- Colagem multicélula não existe; tabela HTML/JS substituiu a opção inicialmente considerada de AG Grid.
- Status do projeto existe no modelo/listas, mas não está no formulário da capa e não há fluxo completo de ações de conclusão/cancelamento exposto nas views atuais.
- Homologação/publicação na conta HostMídia, limites de CageFS/Passenger/Cron, SSL e SMTP reais continuam pendentes. Validação Windows/local não comprova a conta remota.
- Retenção/periodicidade/responsáveis e ensaio operacional de backup/restauração precisam de definição da organização.
- Não foi estabelecido teto comercial para o percentual de taxa; o código exige valor não negativo dentro da precisão do campo. A consolidação não cria uma política comercial nova.
- Aceitação SMTP não prova entrega/leitura; resultado parcial/incerto exige avaliação antes de reenviar.
- Exportação Excel não é backup integral. Campos sem representação, nome livre e vínculos por descrição têm os limites do [008](008_IMPORTACAO_E_EXPORTACAO_EXCEL.md). A execução das macros não foi homologada, inclusive macros antigas que referem aba inexistente.
- Cores/marca de interface não foram declaradas identidade visual oficial. Templates antigos de PDF não comandam o gerador atual.

Nenhuma dessas pendências foi resolvida por alterar o número para 1.0.0. A [consolidação](013_VERSIONAMENTO_E_CONSOLIDACAO.md) distingue histórico, estado implementado e validação documental.
