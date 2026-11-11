# Implantação Linux — HostMídia / cPanel

Base da v.0.0.3: hospedagem Linux com **Setup Python App (Python Selector), Passenger, MySQL/MariaDB e Cron**. A aplicação mantém um único módulo `config.settings` e um único manifesto em [requirements.txt](../../requirements.txt).

A [HostMídia anuncia Python e cPanel](https://www.hostmidia.com.br/hospedagem-de-sites/). Essa informação não confirma as versões e bibliotecas nativas do plano contratado. Esta revisão prepara o repositório; não houve acesso nem publicação em uma conta HostMídia.

## 1. Compatibilidade do plano

Confirme no painel/suporte:

- **Setup Python App**, com Python **3.11+**, preferencialmente 3.12/3.13, e execução WSGI pelo Passenger.
- Terminal/SSH ou mecanismo equivalente para executar os comandos no virtualenv selecionado pelo painel.
- MySQL **8.0.11+** ou MariaDB **10.5+**, com **InnoDB** e `utf8mb4`. São mínimos do Django 5.2; prefira versões ainda mantidas pelo fornecedor. [Compatibilidade oficial](https://docs.djangoproject.com/en/5.2/ref/databases/#mysql-notes).
- Instalação de `mysqlclient` no virtualenv. No Linux, pode exigir compilador, `pkg-config` e bibliotecas/headers MySQL/MariaDB fornecidos pelo provedor. [Instruções do projeto](https://pypi.org/project/mysqlclient/).
- **Pango 1.44+**, bibliotecas do WeasyPrint e fontes disponíveis ao processo Python, além de cache gravável. `pip install` sozinho não fornece todas as bibliotecas nativas. [Requisitos WeasyPrint](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html).
- Cron habilitado, frequência mínima permitida, limites de memória/CPU/tempo dos processos e SMTP/autenticação autorizados para a conta.

Se Pango ou as bibliotecas de `mysqlclient` estiverem ausentes, solicite sua disponibilidade ao provedor. A hospedagem compartilhada não permite presumir acesso `sudo` para instalá-las. O script `verificar_ambiente.py` acusa incompatibilidades; não substitui o PDF nem mascara falhas.

## 2. Diretórios e cadastro da aplicação

Use um subdomínio dedicado, por exemplo `obras.seudominio.com`, com a aplicação na raiz da URL. A publicação em um subcaminho, como `/frz`, exige configuração adicional e não é a base deste guia.

Exemplo de diretórios:

```text
/home/USUARIO/frz-v2/                     # código e passenger_wsgi.py; fora de public_html
    .codex/                              # enviar também esta pasta oculta
    .env                                 # privado, criado/configurado no servidor
    .cache/                              # cache de fontes, ignorado pelo Git
    staticfiles/                         # collectstatic; somente assets públicos
    tmp/                                 # reinício Passenger e logs operacionais privados
/home/USUARIO/virtualenv/frz-v2/3.12/      # exemplo; caminho real vem do painel
```

Não envie `.venv`, `.env`, caches ou `staticfiles` do Windows. Envie o código e `.codex`; instale as dependências no Linux usando o Python indicado pelo cPanel. O código e o `.env` ficam fora do diretório público do domínio.

No **cPanel → Software → Setup Python App → Create Application**, preencha:

| Campo | Valor de referência |
| --- | --- |
| Python version | 3.12 ou 3.13, conforme disponibilidade; mínimo da base: 3.11 |
| Application root | `frz-v2`, relativo ao diretório home da conta |
| Application URL | `obras.seudominio.com`, raiz `/` |
| Application startup file | `passenger_wsgi.py` |
| Application Entry point | `application` |
| Passenger log file | Caminho privado permitido pelo painel, fora de `public_html` |

Os campos e o registro são descritos pelo [cPanel](https://support.cpanel.net/hc/en-us/articles/360057849753-How-to-register-an-application-with-Python-Selector). Se o painel usar Application Manager em vez de Python Selector, confirme com o provedor a seleção do interpretador e o cadastro WSGI equivalente; não presuma a existência de ambas as ferramentas.

Se o painel gerar um `passenger_wsgi.py` de exemplo, use o arquivo do repositório após criar a aplicação. Ele localiza o projeto pelo próprio caminho, força `config.settings`/debug desativado e exporta `application`. O interpretador continua sendo o selecionado pelo painel.

## 3. Instalar no virtualenv do cPanel

Copie do painel o comando para ativar o ambiente virtual. Use o **executável absoluto** desse mesmo ambiente em todos os comandos abaixo; o caminho é ilustrativo:

```sh
cd /home/USUARIO/frz-v2
/home/USUARIO/virtualenv/frz-v2/3.12/bin/python .codex/scripts/instalar.py
```

O instalador usa `sys.executable`, não cria outro virtualenv e não precisa de `sudo`. Instala o manifesto e cria `.env` **somente se ausente**, com segredo aleatório, permissão `0600` no Linux e sem mostrar o segredo na saída. Também cria `.cache` e `tmp` privados. Um `.env` existente é preservado.

## 4. Banco, domínio e SMTP

Crie banco e usuário no assistente MySQL do cPanel e associe o usuário ao banco com os privilégios necessários às migrações. Use os nomes completos, incluindo o prefixo da conta, por exemplo `USUARIO_frz`. Para uma instalação existente, faça backup antes de qualquer migração; não recrie o banco.

Edite o `.env` criado na raiz a partir de [`.env.example`](../.env.example):

- `DJANGO_DEBUG=false` e segredo exclusivo de pelo menos 50 caracteres, já gerado pelo instalador.
- `DJANGO_ALLOWED_HOSTS=obras.seudominio.com`, sem protocolo, caminho ou curinga.
- `CSRF_TRUSTED_ORIGINS=https://obras.seudominio.com`.
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST` e `DB_PORT` conforme o cPanel. `localhost` é exemplo, não garantia do endereço do serviço.
- `DB_CONN_MAX_AGE=0`, padrão que fecha conexões ao final de cada requisição, adequado como ponto de partida para os limites da hospedagem compartilhada.
- Backend SMTP e credenciais de uma conta autorizada. Porta 587 com TLS ou 465 com SSL conforme orientação do provedor; não habilite ambos.
- `DEFAULT_FROM_EMAIL` com remetente autorizado. Aceitação SMTP não comprova entrega/leitura.

O padrão de cache é `.cache` dentro da raiz privada. `XDG_CACHE_HOME` permite outro caminho gravável se o provedor exigir. PDFs continuam gerados somente em memória.

O Passenger e o Cron precisam receber os mesmos valores. Prefira o `.env` privado, compartilhado pelos dois. Variáveis do processo têm precedência sobre o arquivo; evite manter valores diferentes também no painel. O entrypoint WSGI e os wrappers de operação sempre forçam debug desativado e o módulo único.

Configure DNS e SSL do domínio no painel. Deixe `TRUST_PROXY_HTTPS=false` quando Passenger transmitir o esquema HTTPS corretamente. Se houver loop de redirecionamento, confirme com o suporte como HTTPS chega ao WSGI. Só habilite a confiança em `X-Forwarded-Proto` se o provedor garantir que seu proxy sobrescreve esse cabeçalho. Não desative HTTPS ou ative debug para contornar o problema.

## 5. Validar, migrar e coletar estáticos

Após configurar o `.env`:

```sh
cd /home/USUARIO/frz-v2
/home/USUARIO/virtualenv/frz-v2/3.12/bin/python .codex/scripts/atualizar.py
/home/USUARIO/virtualenv/frz-v2/3.12/bin/python manage.py criar_gestor --username gestor
/home/USUARIO/virtualenv/frz-v2/3.12/bin/python manage.py createsuperuser
```

`atualizar.py` executa, nesta ordem:

1. `verificar_ambiente.py`: checks de produção, conexão e versão compatível de banco via Django, InnoDB, escrita no cache e um PDF real somente em memória. Não envia e-mails.
2. `migrate --noinput`.
3. `collectstatic --noinput`, com compressão e manifesto de nomes com hash.
4. Criação/atualização de `tmp/restart.txt` para solicitar reinício ao Passenger. Confirme pelo botão **Restart** do painel.

Qualquer comando com falha interrompe a sequência; migrações já concluídas não são desfeitas automaticamente. O validador também pode ser executado isoladamente, com o mesmo Python, antes de uma atualização.

O WhiteNoise serve `staticfiles` através do WSGI, incluindo CSS/JS do aplicativo e do admin. Não precisa de configuração Nginx nem de copiar assets para `public_html`. Depois de alterar estáticos, execute novamente `collectstatic` e reinicie Passenger. [Integração Django/WhiteNoise](https://whitenoise.readthedocs.io/en/stable/django.html).

Teste `https://obras.seudominio.com/entrar/` e `/admin/`, estilos, autenticação, projeto, PDF e envio controlado a destinatário autorizado. `criar_gestor` concede permissões operacionais; `createsuperuser` concede acesso técnico independente das cinco flags de negócio.

## 6. Cron para a fila de e-mails

Em **cPanel → Cron Jobs**, use o Python absoluto do virtualenv e o wrapper [processar_emails.py](../scripts/processar_emails.py):

```cron
* * * * * /home/USUARIO/virtualenv/frz-v2/3.12/bin/python /home/USUARIO/frz-v2/.codex/scripts/processar_emails.py --limite 1 >> /home/USUARIO/frz-v2/tmp/cron-email.log 2>&1
```

No formulário do cPanel, os cinco campos de tempo são separados; em **Command**, informe apenas o trecho que começa pelo executável. Adapte caminhos e frequência às permissões do plano. O [exemplo](../scripts/cron_exemplo.txt) fica junto dos scripts. Se só for permitido executar a cada cinco minutos, use `*/5 * * * *`; a busca das pendências terá essa resolução, sem alterar o prazo de três horas gravado no banco.

O wrapper força produção e processa **até uma tentativa por execução** por padrão. A fila e os bloqueios persistentes existentes evitam que execuções concorrentes enviem a mesma tentativa. Não há daemon; o processo termina após o trabalho. Ajuste o limite somente após verificar consumo e restrições do plano. O [cPanel recomenda considerar duração e sobreposição das tarefas](https://docs.cpanel.net/cpanel/advanced/cron-jobs/).

Três reenvios automáticos, além do inicial, continuam separados por três horas após falhas confirmadas. Resultado incerto ou parcial continua exigindo tratamento existente. O Cron apenas processa trabalhos vencidos; não redefine as regras de envio.

## 7. Atualização, logs e backup

Reserve uma janela de manutenção, suspenda novas edições e o Cron, e aguarde os envios em andamento terminarem. Faça backup do banco antes de atualizar código/dependências ou aplicar migrações. Execute `instalar.py` para atualizar dependências sem sobrescrever `.env`, seguido de `atualizar.py`. Confira a aplicação após Restart e então reative o Cron.

Consulte o log Passenger configurado no painel e `tmp/cron-email.log`. Logs ficam fora do diretório público; defina rotação/retenção conforme os recursos da conta. Produção rejeita backend de e-mail console/arquivo para que anexos não sejam despejados nos logs.

O backup deve incluir banco completo, código e `.env` protegido. Preserve usuários, permissões, obras, despesas, lotes, snapshots, auditoria e tentativas de envio. Use backup do cPanel/HostMídia ou exportação transacional e mantenha cópia protegida fora da conta; teste restauração em banco isolado. Não há PDFs persistidos para copiar. Retenção e responsáveis continuam pendentes.

## 8. Desenvolvimento e testes

Windows continua como estação de desenvolvimento, com o mesmo manifesto e `config.settings`; no `.env` local, use `DJANGO_DEBUG=true`, hosts locais e banco próprio. Pango local segue a documentação WeasyPrint; `WEASYPRINT_DLL_DIRECTORIES` pode ser necessário no Windows. Não envie essa variável com caminhos Windows ao servidor Linux.

```powershell
.\.venv\Scripts\python.exe .codex/scripts/testar.py
.\.venv\Scripts\python.exe .codex/scripts/testar.py --mysql --pdf-real
node --test .codex/tests/formatacao.test.cjs .codex/tests/envios.test.cjs
```

No Linux, use o Python do virtualenv correspondente. Os testes não enviam e-mails reais. Sem `--mysql`, SQLite em memória isola a suíte. Com a opção, o runner cria e remove banco temporário aleatório, previamente verificado como inexistente, com conta de testes que permita CREATE/DROP; não execute a suíte no banco de produção da hospedagem.

A execução local não homologa Passenger, CageFS, limites de recursos, SSL, Cron ou SMTP da conta HostMídia. Esses itens precisam ser conferidos no plano contratado.
