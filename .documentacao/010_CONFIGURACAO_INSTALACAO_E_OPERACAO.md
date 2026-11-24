# 010 — Configuração, instalação e operação

[Guia](001_GUIA_DA_DOCUMENTACAO.md) · Base: Linux/HostMídia/cPanel, Python Selector, Passenger, MySQL/MariaDB e Cron. Os comandos abaixo são instruções, não ações realizadas na consolidação 1.0.0.

## Configuração única

[config/settings.py](../config/settings.py) atende produção e desenvolvimento. `load_dotenv(..., override=False)` preserva variáveis do processo sobre `.env`. `.codex/test_settings.py` apenas isola testes, não é um segundo perfil de hospedagem. Não incluir credenciais reais na documentação ou em saídas de diagnóstico.

| Variável | Finalidade |
| --- | --- |
| DJANGO_SECRET_KEY | Segredo; produção exige ao menos 50 caracteres |
| DJANGO_DEBUG | Padrão false; true somente no desenvolvimento |
| DJANGO_ALLOWED_HOSTS | Lista explícita; produção recusa vazio/curinga |
| CSRF_TRUSTED_ORIGINS | Origens HTTPS autorizadas |
| DATABASE_URL | `mysql://USUARIO:SENHA_CODIFICADA@HOST:3306/BANCO` |
| EMAIL_BACKEND | SMTP em produção; console somente em desenvolvimento |
| EMAIL_HOST/PORT/USER/PASSWORD | Conexão SMTP; nomes completos no exemplo de ambiente |
| EMAIL_USE_TLS / EMAIL_USE_SSL | Escolher conforme provedor, sem ativar os dois |
| DEFAULT_FROM_EMAIL | Remetente autorizado |
| TRUST_PROXY_HTTPS | Só ativar se o provedor garantir o cabeçalho de proxy |

Os nomes exatos de credenciais SMTP são EMAIL_HOST_USER e EMAIL_HOST_PASSWORD. Copie [o exemplo privado sem segredos](../.codex/.env.example), não valores desta tabela. DATABASE_URL é obrigatória; backend diferente de MySQL ou URL sem banco é recusado. Caracteres especiais de usuário/senha precisam de codificação de URL. Variáveis DB_* foram substituídas.

Banco: charset utf8mb4, InnoDB, SQL strict, READ COMMITTED, conexões persistentes por 600 segundos, health checks e ssl_require=False. TLS adicional depende das opções da URL/serviço. HTTPS, cookies seguros, HSTS e checks de segurança são habilitados em produção. Passenger e wrappers de operação forçam debug falso.

STATIC_ROOT = staticfiles; WhiteNoise serve assets com hash. MEDIA_ROOT = media; o modelo XLSM deve existir em media/modelos/projeto.xlsm. Não há rota pública de mídia adicionada; exportação lê o modelo internamente. PDFs não precisam de diretório persistente.

## Preparação no cPanel

Confirme no plano Python 3.11+ (base prefere 3.12/3.13), Passenger/Python Selector, MySQL/MariaDB compatível com Django 5.2, bibliotecas de mysqlclient, Cron, SMTP e recursos suficientes. Os mínimos registrados na implementação são MySQL 8.0.11/MariaDB 10.5; não são recomendação de usar versões sem manutenção. A conta real continua sem homologação registrada.

Envie código para fora de public_html, incluindo `.codex` e `media/modelos/projeto.xlsm`. Não envie `.venv`, `.env` privado do Windows, caches ou staticfiles locais. `.documentacao` acompanha a referência técnica. No Setup Python App, use application root do projeto, URL na raiz de um subdomínio, startup `passenger_wsgi.py` e callable `application`.

Use o Python absoluto do virtualenv indicado pelo painel. O caminho abaixo é ilustrativo:

```sh
cd /home/USUARIO/frz-v2
/home/USUARIO/virtualenv/frz-v2/3.12/bin/python .codex/scripts/instalar.py
# Configure o .env privado com banco, domínio, HTTPS e SMTP reais.
/home/USUARIO/virtualenv/frz-v2/3.12/bin/python .codex/scripts/atualizar.py
/home/USUARIO/virtualenv/frz-v2/3.12/bin/python manage.py criar_gestor --username gestor
/home/USUARIO/virtualenv/frz-v2/3.12/bin/python manage.py createsuperuser
```

## O que cada ferramenta faz

| Ferramenta | Efeitos |
| --- | --- |
| [instalar.py](../.codex/scripts/instalar.py) | Exige Python/virtualenv e raiz fora de public_html; instala requirements; cria .env somente ausente com segredo e permissão privada; cria tmp |
| [verificar_ambiente.py](../.codex/scripts/verificar_ambiente.py) | Setup, checks deploy, conexão/banco/InnoDB e PDF real em memória; não envia email |
| [atualizar.py](../.codex/scripts/atualizar.py) | Verifica, executa migrate, collectstatic e toca tmp/restart.txt; interrompe na falha |
| [processar_emails.py](../.codex/scripts/processar_emails.py) | Wrapper de Cron com produção e limite padrão 1 |
| [testar.py](../.codex/scripts/testar.py) | Testes isolados SQLite ou banco MySQL temporário aleatório |
| [formatar_templates.py](../.codex/scripts/formatar_templates.py) | djlint fixado; reformat ou --check; normaliza LF no modo escrita |
| [preparar_modelo_xlsm.py](../.codex/scripts/preparar_modelo_xlsm.py) | Limpa cópia do modelo mantendo VBA; --substituir é explícito; não sobrescreve origem |

Falha no atualizador não desfaz migrações anteriores já concluídas. Confirme Restart no painel e teste login, admin, CSS, projeto, PDF e fluxo de e-mail autorizado. Os caminhos de execução precisam ser os mesmos para Passenger e Cron. O wrapper não cria outro ambiente virtual nem precisa de sudo.

## Cron e manutenção

Exemplo adaptável ao plano, com log privado:

```cron
* * * * * /home/USUARIO/virtualenv/frz-v2/3.12/bin/python /home/USUARIO/frz-v2/.codex/scripts/processar_emails.py --limite 1 >> /home/USUARIO/frz-v2/tmp/cron-email.log 2>&1
```

Frequência depende do plano; o prazo de três horas é mantido no banco. Reservas interrompidas são incertas e exigem conferência do SMTP antes de reenvio manual. Aceitação parcial também não permite repetir cegamente a mensagem inteira.

Para atualizar implementação futuramente: janela de manutenção, suspender novas escritas/Cron, aguardar envios em curso, backup, dependências, atualização, Restart, verificação e retorno do Cron. A consolidação 1.0.0 não requer esse ciclo de alteração técnica por si só.

Backup precisa incluir banco completo, código, modelo XLSM e .env protegido; preservar usuários, obras, snapshots, auditoria e tentativas. PDFs são regenerados, não há acervo permanente de PDF a copiar. Testar restauração isolada; retenção/responsáveis ainda precisam ser definidos. Logs Passenger/Cron ficam fora da área pública e precisam de rotação.

## Desenvolvimento local

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
# Copie .codex/.env.example se .env ainda não existir; configure banco local e DEBUG=true.
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

Mesmo manifesto/settings; MySQL no desenvolvimento. ReportLab dispensa WeasyPrint/Pango/caminhos DLL. `criar_gestor` e `createsuperuser` têm finalidades diferentes conforme o [004](004_AUTENTICACAO_PERMISSOES_E_USUARIOS.md).
