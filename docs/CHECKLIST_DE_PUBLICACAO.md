# Checklist de publicação

## Institucional e jurídico

- [ ] A ferramenta será usada somente por profissionais maiores de 18 anos.
- [ ] Controlador, encarregado/DPO e canal de privacidade foram preenchidos.
- [ ] Política de privacidade e fluxo internacional foram revisados pela IES.
- [ ] Projeto Gemini, faturamento, DPA/contrato, quotas e orçamento foram aprovados.
- [ ] Regras de uso proíbem dados de estudantes, dados sensíveis e conteúdo sigiloso.
- [ ] Há procedimento de incidente, rotação de chave e atendimento a titulares.
- [ ] Revisão humana obrigatória está incorporada ao processo institucional.

## Configuração

- [ ] `.env` existe no servidor, não está no Git e tem permissão `600`.
- [ ] `SECRET_KEY` é longa, aleatória e diferente do exemplo.
- [ ] `GEMINI_API_KEY` foi inserida pelo administrador autorizado.
- [ ] `GEMINI_MODEL` foi conferido nos documentos oficiais.
- [ ] Modelos de apostila/avaliação, timeout e limites de entrada foram conferidos.
- [ ] `GEMINI_DATA_MODE` corresponde ao faturamento real do projeto.
- [ ] `USE_FAKE_GEMINI=false` em produção.
- [ ] Nome, unidade, site, endereço, rodapé e e-mail de privacidade foram preenchidos.
- [ ] `app/static/img/logo.png` contém a logo aprovada.

## PythonAnywhere

- [ ] Ambiente virtual e Web App usam a mesma versão do Python.
- [ ] Dependências foram instaladas com `pip install -r requirements.txt`.
- [ ] WSGI contém o caminho correto e carrega `.env` antes da aplicação.
- [ ] Não há chamada direta a `app.run()` no WSGI.
- [ ] `/static/` aponta para `app/static`.
- [ ] O site foi recarregado e `/health` retorna `status: ok`.
- [ ] Logs técnicos foram verificados sem dados de formulários ou anexos.

## Validação

- [ ] `python scripts/check_setup.py` passou.
- [ ] `python scripts/test_gemini.py` passou sem documentos reais.
- [ ] `pytest -q` passou integralmente.
- [ ] Cada um dos seis geradores foi testado com dados fictícios.
- [ ] DOCX/ZIP, logo, tabelas, datas, gabarito e rubricas foram revisados.
- [ ] O usuário vê os avisos de privacidade e revisão docente.
- [ ] O site funciona em tela pequena, teclado e navegador institucional.
