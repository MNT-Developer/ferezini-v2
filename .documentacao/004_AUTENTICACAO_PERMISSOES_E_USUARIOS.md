# 004 — Autenticação, permissões e usuários

[Guia](001_GUIA_DA_DOCUMENTACAO.md) · [Código accounts](../apps/accounts/).

## Login e redefinição

`entrar`, em `/entrar/`, usa LoginForm e autenticação Django. O manager procura username sem diferenciar caixa e recusa cadastros ambíguos. O destino `next` precisa ser local e compatível com o esquema. `sair` exige POST e encerra a sessão.

O hasher normaliza a senha com casefold antes de PBKDF2/SHA-256 com salt. O único validador de força exige seis caracteres. Senhas não são gravadas em texto puro.

`accounts.0004` marcou hashes antigos para redefinição. Enquanto a pendência existe, `check_password` valida a grafia original do hash legado. Após login, o middleware bloqueia outras rotas exceto redefinição e logout. A view de redefinição usa SetPasswordForm; o serviço revalida, salva a senha, aumenta a versão e audita sem registrar o conteúdo. A sessão atual é atualizada.

`set_password` libera a exigência ao definir senha nova; `save` inclui a flag em atualizações parciais de password. Gestor autorizado, Admin ou changepassword também podem redefinir. Alterar somente outros dados não resolve a pendência. Rotas exatas estão em [accounts/urls.py](../apps/accounts/urls.py).

## Matriz operacional

Usuário deve estar autenticado e ativo. Qualquer uma das flags listadas habilita a área.

| Área | Permissões aceitas |
| --- | --- |
| Projetos | Diretoria, Administrativo, Acesso geral ou Gestão de projetos |
| Gestão de Usuários | Diretoria, Gestão de funcionários ou superusuário |
| Relatórios Gerais | Diretoria, Acesso geral ou Relatórios gerais; tela de escopo futuro |
| Diretoria | Diretoria; tela de escopo futuro |
| Trocar responsável vinculado | Acesso a projetos e Diretoria ou Administrativo |

`is_staff`/`is_superuser` são privilégios técnicos e não concedem automaticamente as seis flags operacionais. As exceções para gestão de usuários/Diretoria são explícitas; não se aplicam automaticamente a projetos. `criar_gestor` concede acesso operacional; `createsuperuser`, acesso técnico. O context processor expõe permissões ao template, mas o servidor também verifica as operações.

## Cadastro e gestão

1. A listagem operacional exclui superusuários e filtra contas da Diretoria segundo o operador.
2. Pesquisa por termos em username/nome/sobrenome/email, filtro ativo/inativo, ordem por nome e paginação de 25.
3. FuncionarioForm exige senha na criação; senha vazia na edição mantém a atual. A versão segue em campo oculto.
4. `salvar_funcionario` bloqueia operador e alvo por ID crescente, relê privilégios, valida alvo/versão/concessão, salva campos permitidos e audita atomicamente.
5. `alterar_estado_usuario` valida booleano, versão e mudança real; inativa/reativa sem excluir vínculos.

Somente Diretoria ou superusuário pode gerenciar contas da Diretoria e conceder essa flag. Para outros gestores, o campo é removido e POST forjado é rejeitado também no serviço. A lista operacional não permite conceder is_staff/is_superuser.

Layout: usuário/nome/sobrenome em terços; email/telefone/cargo em terços; senha inteira; flags em quartos. A seleção de responsável mostra ativos não superusuários: dez iniciais alfabéticos, pesquisa por nome/sobrenome sem limite de dez; clicar na linha preenche ID e primeiro nome nos campos de leitura 3/9.

Na criação de projeto sem seleção, o serviço atribui ao cadastrante, inclusive superusuário com acesso operacional. Em cadastro antigo sem vínculo, primeiro responsável pode ser atribuído por quem acessa projetos; depois, trocar/remover exige Diretoria/Administrativo. Bloqueio e versão impedem sobrescrever o primeiro vínculo com formulário antigo.

## Django Admin

UsuarioAdmin filtra queryset e campos de Diretoria, verifica alvo e permissões em visualização/edição, protege a troca de senha e registra auditoria. Usuários devem ser inativados, não excluídos. Grupos e permissões nativas continuam no Admin; o acesso operacional não é equivalente ao acesso técnico.

Cada método, view, formulário, middleware e serviço está no [catálogo 012](012_REFERENCIA_DE_FUNCOES.md). Evidências de migração e controles estão no [011](011_TESTES_VALIDACAO_E_LIMITACOES.md).
