# Diagnóstico e correção do gerador de apostilas

## Causa mais provável

A versão anterior permitia até 48.000 tokens na apostila, não configurava timeout explícito no SDK e enviava PDFs completos ao processamento multimodal. Essa combinação pode manter o worker ocupado até o PythonAnywhere encerrá-lo. A plataforma documenta um limite de cinco minutos por requisição e recomenda considerar trabalho assíncrono quando a operação costuma ultrapassar 30 segundos.

Uma fila assíncrona tradicional exigiria armazenar temporariamente anexos, estado e resultado, contrariando a decisão deste projeto de não persistir conteúdo. A correção adotada mantém o fluxo síncrono e sem armazenamento.

## Mudanças aplicadas

1. Modelo da apostila alterado para `gemini-3.5-flash-lite`, otimizado para baixa latência e leitura de documentos.
2. Timeout do SDK limitado a 180 segundos, antes do encerramento do worker.
3. Retentativas internas desativadas para não prolongar silenciosamente a requisição.
4. Saída reduzida de 48.000 tokens para:
   - Breve: 4.500 tokens;
   - Regular: 8.000 tokens;
   - Ampliada: 12.000 tokens.
5. O prompt agora estabelece limites de palavras, seções e questões de revisão.
6. PDFs com texto selecionável são extraídos localmente e enviados como texto; PDFs digitalizados continuam sendo processados como PDF.
7. O conteúdo textual dos anexos da apostila é limitado a 160.000 caracteres, priorizando primeiro o plano obrigatório.
8. Erros e timeouts permanecem visíveis no formulário.
9. O log técnico registra fase e duração, sem nomes, campos ou conteúdo dos documentos.

## Atualização do `.env`

Os valores abaixo já são os padrões do código novo. Adicione-os ao `.env` para tornar a configuração explícita:

```dotenv
GEMINI_APOSTILA_MODEL=gemini-3.5-flash-lite
GEMINI_TIMEOUT_SECONDS=180
APOSTILA_MAX_INPUT_CHARS=160000
```

O responsável institucional adulto autorizado deve administrar essas configurações e a chave. Não altere o valor do timeout para mais de 240 segundos; o código também aplica esse limite preventivamente.

## Como confirmar o problema anterior

Na aba **Web** do PythonAnywhere, abra o **Server log** e procure por:

```text
HARAKIRI
```

Essa mensagem indica que um worker atingiu o limite da plataforma. Na versão corrigida, procure por linhas como:

```text
generation_completed type=apostila elapsed=42.7s
generation_failed type=apostila phase=gemini code=generation_error elapsed=180.1s
```

Essas linhas não contêm dados do professor ou dos documentos.

## Teste recomendado

1. Use a opção **Breve**.
2. Anexe somente o plano individual em DOCX, sem referências opcionais.
3. Gere a apostila e observe o tempo mostrado na interface.
4. Depois repita com um PDF textual.
5. Acrescente as referências opcionais uma de cada vez.

Se o teste básico passar, mas a geração falhar após determinada referência, o gargalo está naquele anexo. Prefira um trecho menor e diretamente relacionado à aula.

## Se ainda houver falha

Copie apenas as linhas técnicas `generation_failed` e as linhas `HARAKIRI` do Server log, removendo qualquer dado adicional antes de compartilhar. Verifique também:

- se o modelo `gemini-3.5-flash-lite` está disponível para o projeto institucional;
- se a quota da API foi atingida;
- se o plano é um PDF digitalizado muito grande;
- se há erro `502`, `503`, `504` ou `429` no log;
- se as dependências foram atualizadas após a implantação.

## Referências oficiais verificadas em 21/07/2026

- PythonAnywhere — trabalho assíncrono e limite de cinco minutos: https://help.pythonanywhere.com/pages/AsyncInWebApps/
- PythonAnywhere — erros 502/504 e `Harakiri`: https://help.pythonanywhere.com/pages/502BadGateway/
- Google — timeouts do SDK: https://ai.google.dev/gemini-api/docs/generate-content/flex-inference
- Google — Gemini 3.5 Flash-Lite: https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite
