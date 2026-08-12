# Diagnóstico e correção do gerador de avaliações

## O que causava a falha

A versão anterior reservava 48.000 tokens para qualquer avaliação, mesmo quando o professor solicitava poucas questões. Ela também podia enviar o texto integral de muitos planos e apostilas numa única chamada. O processamento podia ultrapassar o timeout configurado antes de produzir o DOCX.

Além disso, a mensagem de timeout era fixa e mencionava incorretamente a opção “Breve”, que pertence ao gerador de apostilas.

## Mudanças aplicadas

1. Modelo específico de baixa latência: `gemini-3.5-flash-lite`.
2. Orçamento calculado pelo total de questões:
   - mínimo: 4.000 tokens;
   - crescimento: aproximadamente 550 tokens por questão;
   - máximo: 18.000 tokens.
3. Limite de 30 questões por avaliação no ambiente síncrono do PythonAnywhere.
4. Até 12 anexos por geração de avaliação.
5. Orçamento textual total de 240.000 caracteres, dividido entre todos os anexos para representar tanto apostilas quanto planos.
6. PDFs textuais são extraídos localmente; PDFs digitalizados permanecem multimodais.
7. Prompt exige o número exato de questões, enunciados objetivos e justificativas concisas.
8. Mensagem de timeout específica para avaliação.

## Configuração

Os valores já são os padrões do código. O administrador institucional adulto autorizado pode registrá-los explicitamente no `.env`:

```dotenv
GEMINI_AVALIACAO_MODEL=gemini-3.5-flash-lite
GEMINI_TIMEOUT_SECONDS=180
AVALIACAO_MAX_INPUT_CHARS=240000
```

## Teste inicial recomendado

1. Gere uma avaliação com 5 questões.
2. Use somente uma apostila e o plano correspondente.
3. Prefira DOCX ou PDF com texto selecionável.
4. Depois aumente para 10 questões.
5. Acrescente os demais conteúdos em pequenos grupos.

Se uma combinação específica de arquivos voltar a atingir o timeout, reduza os anexos ao conteúdo efetivamente avaliado. Para mais de 30 questões, gere duas avaliações independentes; isso mantém cada requisição dentro do limite e facilita a revisão docente.

## Logs

No **Server log** do PythonAnywhere, procure somente as linhas técnicas:

```text
generation_completed type=avaliacao elapsed=58.4s
generation_failed type=avaliacao phase=gemini code=generation_error elapsed=180.1s
HARAKIRI
```

Não compartilhe campos, anexos, prompts ou respostas. As linhas acima são suficientes para identificar fase e tempo.
