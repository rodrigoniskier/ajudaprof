# Privacidade, LGPD e operação responsável

## Escopo deste projeto

O aplicativo foi projetado sem persistência de conteúdo no backend:

- não cria cadastro ou perfil;
- não usa banco de dados;
- não guarda formulários, anexos, respostas ou downloads;
- não adiciona analytics, publicidade ou pixels;
- recebe uploads em memória e gera DOCX/ZIP em memória;
- libera os objetos da requisição após a transmissão da resposta;
- não oferece histórico nem recuperação posterior.

“Sem persistência no aplicativo” não significa “sem tratamento por terceiros”. O navegador transmite dados ao PythonAnywhere; o servidor envia conteúdo necessário ao Google Gemini; os dois fornecedores podem manter registros técnicos ou tratar dados conforme seus próprios termos.

## Regra de conteúdo

O uso normal deve se limitar a documentos curriculares e materiais acadêmicos sem dados pessoais. Não envie:

- nomes, matrículas, notas ou trabalhos de estudantes;
- dados de crianças e adolescentes;
- dados de saúde ou outras categorias sensíveis;
- dados financeiros, credenciais ou documentos de identificação;
- segredos comerciais ou conteúdo protegido por sigilo;
- questões de avaliação ainda não aplicadas, quando a IES as classificar como confidenciais;
- obras ou trechos sem autorização de uso.

O serviço é destinado apenas ao uso profissional por docentes, gestores e administradores maiores de 18 anos. Conta, faturamento e chaves devem ficar sob responsabilidade institucional adulta e autorizada.

## Gemini pago e não pago

Conforme os termos oficiais consultados em 21/07/2026:

- em serviços não pagos, o Google informa que pode usar entradas e saídas para fornecer, melhorar e desenvolver produtos e tecnologias, com possibilidade de revisão humana; o próprio termo orienta a não enviar conteúdo pessoal, sensível ou confidencial;
- em serviços pagos, vinculados a projeto com faturamento ativo, o Google informa que não usa prompts e respostas para melhorar produtos, mas mantém registros limitados para segurança, prevenção de abuso e obrigações legais;
- a Gemini API e o Google AI Studio exigem usuário de 18 anos ou mais e são voltados a desenvolvimento profissional ou empresarial.

Por isso, a recomendação operacional é usar projeto institucional com faturamento ativo, limites de gasto e contrato/DPA analisado pela IES. Ainda assim, aplique minimização de dados.

O valor de `GEMINI_DATA_MODE` não altera o contrato do Google; ele apenas faz a interface exibir a situação declarada. Só configure `paid` se o faturamento estiver realmente ativo no projeto da chave.

## Papéis e decisões da IES

Antes da publicação, a instituição deve documentar:

1. controlador e canal do encarregado/DPO;
2. finalidade específica e usuários autorizados;
3. base legal aplicável ao tratamento residual de dados pessoais;
4. operadores/suboperadores e contratos;
5. transferência internacional;
6. retenção de logs da hospedagem e do provedor de IA;
7. avaliação de risco e plano de incidentes;
8. processo de exercício de direitos dos titulares;
9. política de uso de IA, propriedade intelectual e revisão humana;
10. procedimento de rotação/revogação da API key.

A página `/privacidade` contém texto inicial parametrizado por `INSTITUTION_NAME`, `PRIVACY_CONTACT_EMAIL` e `GEMINI_DATA_MODE`. Ela deve ser revisada pela assessoria jurídica e pelo encarregado antes do uso real.

## Medidas técnicas incluídas

- API key somente no backend, em `.env` fora do Git.
- HTTPS/HSTS, CSP, proteção contra framing, `nosniff`, política de permissões e referrer policy.
- CSRF assinado sem sessão/cookie de usuário.
- Rate limit transitório em memória usando HMAC do endereço de rede; o identificador não é persistido.
- Limites por arquivo e por requisição.
- Extensões permitidas e verificação de assinatura para PDF/PNG/JPEG.
- Proteção contra arquivos Office corrompidos ou com expansão excessiva.
- Sanitização de nomes de arquivos.
- Extração local de DOCX/XLSX/PPTX; PDF e imagens são enviados inline ao Gemini.
- Instruções de defesa contra prompt injection nos anexos.
- Resposta estruturada por schema Pydantic e validações adicionais de datas, quantidades e tipos.
- Sem registro deliberado de conteúdo de formulários, anexos, prompts ou respostas.
- Cabeçalho `Cache-Control: no-store` nos downloads.

## Limites técnicos honestos

- A memória do processo é administrada pelo Python; o aplicativo deixa de referenciar os buffers ao fim da requisição, mas não promete sobrescrita física instantânea de cada byte.
- O PythonAnywhere pode gerar registros técnicos próprios, fora do controle do código.
- O Google processa o conteúdo enviado e aplica seus termos, políticas e retenções.
- Modelos generativos podem errar, omitir, alucinar referências ou criar questões inadequadas.
- As defesas contra prompt injection reduzem risco, mas não garantem eliminação total.

Assim, nenhum documento deve ser adotado ou aplicado automaticamente. O docente deve verificar integralmente conteúdo, cargas horárias, datas, referências, acessibilidade, gabaritos, rubricas, legislação e conformidade institucional.

## Operação recomendada

- Restrinja o acesso à comunidade profissional autorizada, se a IES dispuser de camada de autenticação externa.
- Não use a quota gratuita com documentos institucionais confidenciais.
- Configure alertas de orçamento e quota no projeto Google Cloud.
- Gire a API key periodicamente e imediatamente após qualquer suspeita de exposição.
- Atualize dependências em ambiente de teste e rode `pytest -q` antes de publicar.
- Revise termos, modelo configurado e lista de domínios do PythonAnywhere periodicamente.
- Mantenha um canal para incidentes, dúvidas de privacidade e correção de documentos.

## Referências oficiais

- Termos adicionais da Gemini API: https://ai.google.dev/gemini-api/terms
- Segurança de API keys: https://ai.google.dev/gemini-api/docs/api-key
- Política de Privacidade do Google: https://policies.google.com/privacy
- Guia Flask do PythonAnywhere: https://help.pythonanywhere.com/pages/Flask/
- LGPD — Lei nº 13.709/2018: https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm

