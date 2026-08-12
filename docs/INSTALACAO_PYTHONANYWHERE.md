# Instalação no PythonAnywhere

Este roteiro implanta o projeto Flask existente usando configuração manual e ambiente virtual, conforme o fluxo recomendado pelo PythonAnywhere.

## Responsabilidades antes de começar

- Um administrador institucional maior de 18 anos e autorizado deve criar e administrar a conta/projeto Gemini, faturamento, chave e limites de custo. Os termos atuais do serviço exigem 18 anos ou mais.
- A IES deve escolher o plano do PythonAnywhere, aprovar fornecedores e revisar o aviso de privacidade.
- Para documentos institucionais, use preferencialmente um projeto Gemini associado a faturamento ativo. Em quota não paga, não envie informações pessoais, sensíveis, confidenciais ou sigilosas.

## 1. Enviar e descompactar o projeto

Na área **Files** do PythonAnywhere, envie `Ajuda_Professores_PythonAnywhere.zip` para `/home/SEU_USUARIO/`. Depois abra um console Bash e execute, substituindo `SEU_USUARIO`:

```bash
cd /home/SEU_USUARIO
unzip Ajuda_Professores_PythonAnywhere.zip
cd /home/SEU_USUARIO/documenta_ia
```

Confira a estrutura:

```bash
pwd
find . -maxdepth 2 -type f | sort
```

## 2. Criar o ambiente virtual e instalar dependências

O Python da configuração manual e o do ambiente virtual devem ter a mesma versão. O exemplo usa Python 3.13, disponível no guia oficial consultado em 21/07/2026:

```bash
mkvirtualenv --python=/usr/bin/python3.13 documenta-ia
python -m pip install --upgrade pip
pip install -r /home/SEU_USUARIO/documenta_ia/requirements.txt
```

Em consoles futuros, reative o ambiente com:

```bash
workon documenta-ia
```

Se sua conta não oferecer Python 3.13, escolha uma versão disponível igual ou superior a 3.11 e selecione exatamente a mesma versão na aba **Web**.

## 3. Criar o segredo do Flask

Ainda no console com o ambiente ativo:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Copie o valor exibido. Ele será usado como `SECRET_KEY`; não o publique.

## 4. Inserir a API key do Gemini — etapa exata

Esta é a etapa em que a chave é inserida. A operação deve ser feita pelo administrador institucional adulto e autorizado.

Primeiro, crie o arquivo de configuração:

```bash
cd /home/SEU_USUARIO/documenta_ia
cp .env.example .env
nano .env
```

No editor, substitua estes valores:

```dotenv
SECRET_KEY=cole-a-chave-aleatoria-gerada-na-etapa-3
GEMINI_API_KEY=cole-a-chave-do-projeto-institucional-aqui
GEMINI_MODEL=gemini-3.5-flash
GEMINI_APOSTILA_MODEL=gemini-3.5-flash-lite
GEMINI_AVALIACAO_MODEL=gemini-3.5-flash-lite
GEMINI_TIMEOUT_SECONDS=180
APOSTILA_MAX_INPUT_CHARS=160000
AVALIACAO_MAX_INPUT_CHARS=240000
GEMINI_DATA_MODE=paid
USE_FAKE_GEMINI=false
```

Use `GEMINI_DATA_MODE=paid` somente quando o projeto Google Cloud associado à chave tiver faturamento ativo. Caso contrário, mantenha `unpaid`; a interface exibirá o alerta correspondente.

No `nano`, salve com `Ctrl+O`, confirme com `Enter` e saia com `Ctrl+X`. Restrinja o arquivo:

```bash
chmod 600 /home/SEU_USUARIO/documenta_ia/.env
```

Não cole a chave em `run.py`, no WSGI, no GitHub, no HTML ou no JavaScript. O Google recomenda segredo no backend/variável de ambiente e informa que chaves novas do AI Studio são do tipo de autorização. Se a instituição ainda usa uma chave padrão antiga, o administrador deve migrá-la antes do prazo indicado pelo Google.

## 5. Preencher identidade e contato de privacidade

No mesmo `.env`, ajuste:

```dotenv
INSTITUTION_NAME=Nome completo da IES
INSTITUTION_UNIT=Pró-Reitoria Acadêmica / Coordenação do Curso
INSTITUTION_WEBSITE=https://www.exemplo.edu.br
INSTITUTION_ADDRESS=Cidade — UF
INSTITUTION_FOOTER=Texto institucional do rodapé
PRIVACY_CONTACT_EMAIL=encarregado@exemplo.edu.br
```

Troque a logo, se necessário, mantendo o formato PNG e o caminho:

```text
/home/SEU_USUARIO/documenta_ia/app/static/img/logo.png
```

## 6. Validar configuração e conexão

O primeiro comando não mostra a chave. O segundo faz uma chamada mínima ao Gemini, sem anexos reais:

```bash
cd /home/SEU_USUARIO/documenta_ia
workon documenta-ia
python scripts/check_setup.py
python scripts/test_gemini.py
pytest -q
```

O esperado é:

```text
Configuração básica válida.
Conexão com a API Gemini confirmada. Modelo: gemini-3.5-flash
```

## 7. Criar o Web App

Na aba **Web** do PythonAnywhere:

1. Clique em **Add a new web app**.
2. Escolha o domínio apresentado pela plataforma.
3. Escolha **Manual configuration**.
4. Selecione Python 3.13, ou a mesma versão usada no ambiente virtual.
5. Em **Virtualenv**, informe:

```text
/home/SEU_USUARIO/.virtualenvs/documenta-ia
```

## 8. Configurar o arquivo WSGI

Na aba **Web**, abra o link do arquivo WSGI, apague o conteúdo de exemplo e use:

```python
import os
import sys

from dotenv import load_dotenv


PROJECT_HOME = "/home/SEU_USUARIO/documenta_ia"

if PROJECT_HOME not in sys.path:
    sys.path.insert(0, PROJECT_HOME)

load_dotenv(os.path.join(PROJECT_HOME, ".env"))

from app import create_app


application = create_app()
```

Substitua `SEU_USUARIO`, salve e não adicione `app.run()` ao WSGI. O mesmo conteúdo está em `wsgi_pythonanywhere.py.example`.

## 9. Mapear arquivos estáticos

Na seção **Static files** da aba **Web**, adicione:

```text
URL:       /static/
Directory: /home/SEU_USUARIO/documenta_ia/app/static
```

Isso permite que o servidor entregue CSS, JavaScript e logo diretamente.

## 10. Recarregar e testar

Clique em **Reload** na aba **Web**. Depois acesse:

```text
https://SEU_USUARIO.pythonanywhere.com/
https://SEU_USUARIO.pythonanywhere.com/health
```

O endpoint de saúde deve responder:

```json
{"service":"ajuda-professores","status":"ok"}
```

Faça uma geração controlada com documentos públicos ou dados fictícios. Confira download, logo, campos, revisão docente e aviso de privacidade antes de abrir o acesso institucional.

## 11. Atualizações futuras

Após enviar uma nova versão dos arquivos:

```bash
cd /home/SEU_USUARIO/documenta_ia
workon documenta-ia
pip install -r requirements.txt
pytest -q
```

Depois clique em **Reload** na aba **Web**. Preserve o `.env` e a logo institucional se forem configurações locais.

## Solução de problemas

### Erro 502 ou 504

- Confira o **Error log** na aba **Web**.
- Confirme que o WSGI aponta para `/home/SEU_USUARIO/documenta_ia`.
- Confirme a versão do Python e o virtualenv.
- Não execute `app.run()` dentro do WSGI.

### “API key ainda não foi configurada”

```bash
cd /home/SEU_USUARIO/documenta_ia
chmod 600 .env
python scripts/check_setup.py
```

Depois verifique se o WSGI chama `load_dotenv` antes de importar `create_app` e recarregue o site.

### Erro de autorização, modelo ou faturamento

Peça ao administrador institucional da conta Google para verificar:

- se a chave pertence ao projeto correto;
- se a Gemini API está habilitada;
- se a chave é atual e autorizada;
- se o projeto tem faturamento ativo quando `GEMINI_DATA_MODE=paid`;
- se há quota e alertas de orçamento configurados.

### Erro de conexão em conta gratuita do PythonAnywhere

Em 21/07/2026, a lista pública do PythonAnywhere contém `.googleapis.com`; contas pagas têm acesso externo irrestrito. Se a política mudar, consulte a lista oficial e os logs de erro antes de alterar o código.

## Referências oficiais verificadas em 21/07/2026

- PythonAnywhere — Flask: https://help.pythonanywhere.com/pages/Flask/
- PythonAnywhere — lista de domínios: https://www.pythonanywhere.com/whitelist/
- Google — uso e proteção de API keys: https://ai.google.dev/gemini-api/docs/api-key
- Google — modelo Gemini 3.5 Flash: https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash
- Google — termos da Gemini API: https://ai.google.dev/gemini-api/terms
