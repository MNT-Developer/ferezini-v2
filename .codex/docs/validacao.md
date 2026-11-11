# Validação da V1

> Registro historico da validacao inicial Windows. A implantacao vigente e descrita em [hostmidia.md](hostmidia.md) e [v.0.0.3](../versao/v.0.0.3.md).

Executada em 11/11/2026, Windows 11, Python 3.13.7, Django 5.2.19 e MySQL 8.0.41.

- **74 testes Django passaram no MySQL, sem testes ignorados**, com `TEST_MYSQL=true` e `TEST_PDF_REAL=true`. Cada execução criou e removeu um banco temporário de nome aleatório, previamente verificado como inexistente; os dados do banco configurado não foram usados como fixtures.
- Os testes incluem concorrência real para edição de versão, inativação de etapa versus criação de despesa e confirmação simultânea de lotes. Também cobrem permissões cumulativas, validações, rascunhos, integridade, inativação lógica, auditoria, ordem, taxas, snapshots, idempotência, relatório inclusivo e fila de e-mails.
- PDFs reais de lote e período foram gerados **somente em memória**. As bibliotecas oficiais do pacote WeasyPrint 70.0 foram extraídas na `.venv`, com Pango 1.58.2; o SHA256 foi verificado. O instalador Windows dessa validação foi descontinuado na v.0.0.3; o guia atual usa bibliotecas do Linux.
- SMTP foi simulado: sucesso, falha confirmada, quatro tentativas automáticas, reenvio manual, recusa parcial, timeout e reserva expirada/renovada. Nenhum e-mail real foi enviado.
- **3 testes JavaScript passaram** com Node: formatação monetária exata acima da precisão de Number, arredondamento e ordenação decimal.
- `manage.py check`, `check --deploy` com configuração temporária de produção, `makemigrations --check --dry-run`, `pip check`, sintaxe JavaScript e análise de sintaxe dos scripts PowerShell passaram.
- Waitress iniciou no Windows e respondeu HTTP 200 à tela de login com token CSRF. Os templates foram compilados e as páginas principais exercitadas via Django Client.
- As migrações foram aplicadas ao banco configurado no `.env`, após confirmar que ele não tinha tabelas. Não foram cadastrados usuários com senhas fixas ou dados demonstrativos no banco da aplicação.

## Limites da verificação

O host de automação do navegador e o acesso nativo estavam indisponíveis. Portanto, não houve inspeção visual no navegador nem validação interativa real de arrastar/soltar, foco/teclado, filtros ou layout mobile. Essas partes tiveram revisão de código, validação de contratos e verificação de templates; recomenda-se a conferência visual antes da homologação.

Linux/Gunicorn, MariaDB, proxy HTTPS, SMTP real, NSSM/Task Scheduler e systemd foram configurados/documentados, mas não executados neste ambiente Windows. Não foi verificada a aparência visual dos PDFs; geração em memória e retorno HTTP foram exercitados.

Para reproduzir, use os comandos do README. O ambiente Python validado está registrado em `.codex/docs/historico-lock-windows-py313.txt`; `.env` e `.venv` estão ignorados pelo controle de versão.
