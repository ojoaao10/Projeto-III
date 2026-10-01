# SA UniGoiás 3.0 — Projeto III / IV

Plataforma acadêmica com servidor Python, SQLite, quatro perfis, cadastros, ofertas por semestre, notas ponderadas, frequência por aula, alertas, materiais, intervenções, relatórios, auditoria e backup.

## Iniciar

Extraia o ZIP. Na pasta SA_UniGoias, execute:

```sh
python3 server.py --demo
```

No Windows, use `python server.py --demo`. Abra **http://127.0.0.1:8000**.

Usuários: `admin`, `coord`, `prof`, `manuel`, `ana`, `lucas`. Senha comum da base fictícia: **Demo@2026!**.

Necessário: Python 3.10+ e navegador moderno. Sem dependências externas para rodar. Não abra index.html diretamente. A aplicação funciona offline. Os dados são criados na primeira execução e permanecem no banco entre reinícios.

## Entregáveis

- `server.py` e `schema.sql`: API, regras e banco relacional.
- `static/`: interface responsiva.
- `docs/Dossie_Projeto_III.pdf`: documentação consolidada para a banca.
- `docs/Requisitos_e_Casos_de_Uso.md`: requisitos, regras e detalhamento rastreável.
- `docs/Casos_de_Uso.svg`, `docs/DER.svg`, `docs/DER_Seguranca.svg`: diagramas vetoriais.
- `docs/Dicionario_de_Dados.md`: todas as tabelas, campos e restrições.
- `docs/Manual_e_Apresentacao.md`: instalação, operações, backup e roteiro.
- `docs/Testes_e_Resultados.md`: evidências e limitações.
- `tests/`: testes reproduzíveis. Execute `python3 -m unittest discover -s tests -v`.
- `docs/originais/`: documentos recebidos, preservados para comparação.

## Antes de apresentar

Leia o manual, rode os testes e gere um backup. Execute todos os perfis no notebook da apresentação. Esta entrega não representa homologação para produção: disponibilidade, carga, infraestrutura, HTTPS e avaliação com usuários são gates da etapa IV. O vídeo antigo foi preservado em `VIDEO_ORIGINAL`; ele mostra a versão anterior, não esta entrega.

O banco e backups de teste não acompanham o ZIP. As credenciais fictícias são geradas por `--demo`. A edição não migra automaticamente localStorage: faltam dados no modelo antigo para reconstruir as aulas por disciplina.
