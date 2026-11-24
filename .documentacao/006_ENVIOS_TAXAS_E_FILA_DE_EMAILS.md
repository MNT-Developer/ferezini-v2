# 006 — Envios, taxas e fila de e-mails

[Guia](001_GUIA_DA_DOCUMENTACAO.md) · [Serviços](../apps/envios/utils.py) · [Views](../apps/envios/views.py) · [Formulários](../apps/envios/forms.py).

## Seleção e confirmação

`painel` mostra notas de projeto ativo, em etapa ativa, ativas, completas, positivas e ainda sem lote. `preparar` monta a prévia; `confirmar` recebe a seleção e delega a `confirmar_lote`. Consultar o painel não confirma nem envia.

Subtotal = soma das despesas selecionadas. Taxa calculada = subtotal × percentual/100, com HALF_UP em centavos. Total = subtotal + taxa aplicada. Uma taxa diferente da calculada exige justificativa textual de até 4.000 caracteres. Backend rejeita float/bool, infinito, negativo, precisão excedida e valores acima da capacidade prevista.

O JavaScript recalcula sem recarregar. Há um só valor de taxa editável: ajuste revela justificativa; mudar flags refaz o cálculo e limpa ajuste/justificativa. Esse cálculo é uma prévia; o servidor revalida tudo ao confirmar.

### Transação

`confirmar_lote` valida acesso, modalidade, IDs únicos/positivos, versões de projeto/notas e elegibilidade. Bloqueia projeto → etapas → despesas. Uma chave UUID de confirmação repetida retorna o lote já confirmado se projeto e autor correspondem, sem criar duplicata.

Grava lote, vínculo das despesas com incremento de versão, LoteEnvioItem com snapshot/ordem/valor e auditoria correlacionada. Gerar apenas deixa e-mail não solicitado. Gerar e enviar exige contato ativo cadastrado e destinatários efetivos válidos, normalizados/deduplicados; cria tentativa inicial pendente. Qualquer falha desfaz a transação.

Importação cria lotes históricos por dia com taxa zero e sem tentativas. Novos envios de projeto importado usam a regra normal. Os detalhes de Excel estão no [008](008_IMPORTACAO_E_EXPORTACAO_EXCEL.md).

## Processamento assíncrono

Não há daemon/Celery. Cron chama [processar_emails.py](../.codex/scripts/processar_emails.py), que invoca o comando [processar_emails_pendentes](../apps/envios/management/commands/processar_emails_pendentes.py). O wrapper limita uma tentativa por execução por padrão; o comando direto tem padrão 50. Ambos encerram após o lote de trabalho.

1. Recuperar reservas interrompidas há mais de 15 minutos como INCERTO.
2. Buscar pendências vencidas em ordem de agenda/ID.
3. `reservar_tentativa` bloqueia lote/tentativa brevemente. Reserva UUID e marca envio; outro worker não toma a mesma tentativa.
4. Fora da transação, gerar PDF e preparar EmailMessage com destinatários em BCC e Message-ID estável por tentativa.
5. Abrir conexão; `renovar_reserva_para_smtp` confirma que a reserva ainda pertence ao worker antes de transmitir.
6. `TransporteSMTPRastreado` captura recusas parciais; `finalizar_tentativa` registra resultado e decide agenda.

## Resultados e reenvios

| Resultado | Efeito |
| --- | --- |
| SUCESSO | Lote ENVIADO, pendências canceladas; significa aceitação SMTP, não entrega/leitura |
| FALHA conhecida | Em tentativa automática elegível, agenda nova após três horas |
| INCERTO | Suspende automação; pode ter havido aceitação SMTP |
| Limite automático alcançado | FALHA_DEFINITIVA |

Existem quatro tentativas no ciclo automático: inicial + três reenvios. Falha de conexão antes de transmitir ou resposta SMTP negativa explícita pode ser repetida. Exceção após início da transmissão, aceitação parcial ou perda do worker pode ser incerta: não reenviar cegamente.

`solicitar_reenvio` reutiliza o lote e os snapshots, aceita destinatários próprios da tentativa, impede envio em andamento ou outra manual pendente e audita o pedido. Não cria lote nem novas notas. Tentativa manual não consome o contador automático; pendências automáticas são coordenadas pelo serviço. Não trocar manualmente o status no banco para liberar a fila.

Os destinatários confirmados não seguem edições posteriores dos contatos da obra. PDF regenerado consulta dados cadastrais atuais da obra, mas notas/valores históricos. Reservas, contadores, status e agenda são operacionais; taxas e snapshots permanecem imutáveis.

Views e formas de preparo, confirmação, download e reenvio estão no [catálogo 012](012_REFERENCIA_DE_FUNCOES.md). Instalação do Cron e recuperação operacional estão no [010](010_CONFIGURACAO_INSTALACAO_E_OPERACAO.md).
