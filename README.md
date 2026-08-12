# Ajuda-Professores

Aplicativo Flask desenvolvido por Prof. Rodrigo Niskier [Medicina - UNIPÊ] para gerar documentos acadêmicos institucionais em DOCX com a API Gemini. O projeto foi preparado para implantação no PythonAnywhere, sem cadastro, banco de dados ou histórico de conteúdo.

## Geradores disponíveis

Cada fluxo funciona de modo independente em uma aba própria:

1. ementa do componente curricular, com PPC e DCNs obrigatórios;
2. plano de ensino, com tópicos dinâmicos e anexos orientadores opcionais;
3. cronograma de aulas, com múltiplos dias/horários, tópicos dinâmicos e calendário acadêmico opcional;
4. planos de aulas individuais, a partir de cronograma, DCNs e ementa;
5. apostila de uma aula, a partir do plano individual;
6. avaliação parametrizada, com quantidade, tipos, Taxonomia de Bloom, dificuldade, gabarito e rubricas.

Os padrões visuais e estruturais foram derivados dos três modelos institucionais fornecidos. A imagem em `app/static/img/logo.png` é usada na interface e nos documentos gerados.

## Comece por aqui

- Implantação completa: [`docs/INSTALACAO_PYTHONANYWHERE.md`](docs/INSTALACAO_PYTHONANYWHERE.md)
- Privacidade, LGPD e operação: [`docs/PRIVACIDADE_LGPD_E_OPERACAO.md`](docs/PRIVACIDADE_LGPD_E_OPERACAO.md)
- Checklist antes da publicação: [`docs/CHECKLIST_DE_PUBLICACAO.md`](docs/CHECKLIST_DE_PUBLICACAO.md)
- Diagnóstico do gerador de apostilas: [`docs/DIAGNOSTICO_APOSTILAS.md`](docs/DIAGNOSTICO_APOSTILAS.md)
- Diagnóstico do gerador de avaliações: [`docs/DIAGNOSTICO_AVALIACOES.md`](docs/DIAGNOSTICO_AVALIACOES.md)

## Onde inserir a API key

A chave não entra no código, HTML ou JavaScript. Durante a instalação no servidor, copie `.env.example` para `.env` e peça ao administrador institucional adulto e autorizado para preencher:

```dotenv
GEMINI_API_KEY=valor-fornecido-pelo-administrador
```

O arquivo WSGI carrega `.env` antes de iniciar o Flask. O arquivo está ignorado pelo Git e deve receber permissão restrita (`chmod 600 .env`). Os termos atuais do Gemini exigem usuário maior de 18 anos para administrar a API; o aplicativo também foi identificado como ferramenta profissional para maiores de 18 anos.

## Execução local para desenvolvimento

Requer Python 3.11 ou superior.

```bash
cd documenta_ia
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

Para testar a interface sem chamar o Gemini, edite `.env` e use:

```dotenv
USE_FAKE_GEMINI=true
```

Depois execute:

```bash
python run.py
```

Abra `http://127.0.0.1:5000`. Nunca use dados reais com `USE_FAKE_GEMINI=true`; esse modo serve somente para desenvolvimento.

## Testes

```bash
python scripts/verificar_atualizacao.py
pytest -q
python scripts/smoke_generate.py --output generated_demo
```

O primeiro comando confirma que os arquivos críticos pertencem ao mesmo pacote. O segundo testa rotas, validações, requisitos de anexos, downloads e processamento em memória. O terceiro produz amostras DOCX determinísticas sem consumir a API.

Depois de configurar a chave real no `.env`, teste a conectividade sem anexar documentos:

```bash
python scripts/test_gemini.py
```

## Arquitetura e privacidade por padrão

- Não há ORM, banco de dados, conta, cookie de sessão, analytics ou histórico.
- Uploads são recebidos em `BytesIO`; o projeto não cria arquivos temporários por requisição.
- DOCX e ZIP são produzidos em memória e transmitidos diretamente ao navegador.
- As referências aos buffers são liberadas ao fim da resposta. Não existe recuperação posterior pelo aplicativo.
- A API key fica somente no backend.
- Há limite global de requisição, limite por arquivo, formatos permitidos, proteção contra expansão excessiva de Office, CSRF assinado, rate limit transitório e cabeçalhos de segurança.
- Campos, prompts, anexos e respostas não são registrados deliberadamente nos logs da aplicação.
- A saída estruturada do Gemini é validada antes da criação do documento.
- O documento sempre indica que revisão docente e aprovação institucional são obrigatórias.

Isso evita persistência pela aplicação, mas não elimina o tratamento feito pelo provedor de hospedagem e pelo Google. Leia o guia de privacidade antes da publicação. Para uso institucional, recomenda-se um projeto Gemini com faturamento ativo e análise formal da IES.

## Desempenho das apostilas

O fluxo de apostilas usa `gemini-3.5-flash-lite`, timeout explícito de 180 segundos, limites de saída proporcionais à extensão escolhida e extração local de PDFs textuais. Isso evita que uma única chamada se aproxime do limite de cinco minutos do worker do PythonAnywhere. Em caso de falha, a interface mantém uma mensagem visível no próprio formulário e o log registra somente tipo, fase e duração — nunca o conteúdo dos anexos.

O fluxo de avaliações aplica a mesma estratégia, com orçamento de saída proporcional ao número de questões, máximo de 30 questões por geração e divisão equilibrada do contexto entre apostilas e planos. Assim, nenhum primeiro anexo ocupa sozinho todo o limite de entrada.

## Estrutura principal

```text
documenta_ia/
├── app/
│   ├── services/          # Gemini, schemas, anexos, validação e DOCX
│   ├── static/            # CSS, JavaScript e logo institucional
│   ├── templates/         # interface e política de privacidade
│   ├── __init__.py        # fábrica Flask e tratamento de erros
│   ├── config.py          # variáveis de ambiente
│   ├── routes.py          # seis endpoints independentes
│   └── security.py        # memória, CSRF, rate limit e cabeçalhos
├── docs/                  # implantação, LGPD e checklist
├── scripts/               # teste da API e geração de amostras
├── tests/                 # suíte automatizada
├── .env.example
├── requirements.txt
├── run.py
└── wsgi_pythonanywhere.py.example
```

## Personalização

Substitua `app/static/img/logo.png` por outra imagem PNG mantendo o mesmo nome. Preencha no `.env`:

```dotenv
INSTITUTION_NAME=Nome da IES
INSTITUTION_UNIT=Unidade ou coordenação
INSTITUTION_WEBSITE=https://www.exemplo.edu.br
INSTITUTION_ADDRESS=Cidade — UF
INSTITUTION_FOOTER=Texto institucional do rodapé
PRIVACY_CONTACT_EMAIL=encarregado@exemplo.edu.br
```

## Limitação importante

O texto da página de privacidade é uma base técnica, não um parecer jurídico. O controlador, o encarregado/DPO e a assessoria jurídica da IES devem validar finalidades, base legal, contratos, transferência internacional, registros técnicos e avisos aos usuários antes da publicação.
