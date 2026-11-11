# Projeto FRZ v2 — Arquivos de apoio

Esta pasta centraliza especificações, versões, dependências e ferramentas de instalação/configuração. A implantação atual usa **Linux, HostMídia e cPanel com Python Selector/Passenger**.

```text
.codex/
    .env.example
    README.md
    scripts/
        instalar.py
        verificar_ambiente.py
        atualizar.py
        processar_emails.py
        cron_exemplo.txt
        testar.py
    test_settings.py
    tests_deploy.py
    tests/
        formatacao.test.cjs
        envios.test.cjs
    docs/
        hostmidia.md
        dependencias.md
        decisoes_pendentes.md
        validacao.md
        historico-lock-windows-py313.txt
    versao/
        v.0.0.1.md
        v.0.0.2.md
        v.0.0.3.md
```

- [Implantação HostMídia/cPanel](docs/hostmidia.md).
- [Mudanças v.0.0.3](versao/v.0.0.3.md).
- [Especificação inicial](versao/v.0.0.1.md) e [melhorias v.0.0.2](versao/v.0.0.2.md).
- [Dependências](docs/dependencias.md), [decisões pendentes](docs/decisoes_pendentes.md) e [validação inicial](docs/validacao.md).
- [Guia resumido do projeto](../README.md).

Código Django, templates, estáticos e utilitários continuam nas pastas da aplicação. O `.env` real permanece na raiz, privado e ignorado pelo Git. [`passenger_wsgi.py`](../passenger_wsgi.py) também fica na raiz porque é a entrada usada pelo servidor para executar o projeto.

Há um único manifesto de dependências e um único módulo Django: `config.settings`. `test_settings.py` isola banco, SMTP, HTTPS e armazenamento de estáticos nos testes; não é uma configuração alternativa de hospedagem. O lock Windows é apenas evidência histórica.

Arquivos `v.*.md` ficam em `versao/`. A partir deles, links ao código usam `../../` e à documentação usam `../docs/`.
