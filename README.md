# ai-operational

Agente que ajuda o usuário a operar o SaaS da Solaria (fornecedores, demandantes e administradores de empresa). Ele indica a tela certa do web-app para o que o usuário quer fazer e, quando o usuário pede, propõe uma ação (hoje, cadastrar uma oferta de placa) com uma mensagem que explica o que será feito. A ação só é executada no `api-core`, com o JWT do próprio usuário, depois do aceite dele; se ele recusar, nada é gravado. É chamado pelo `ai-assistant` por A2A, onde a proposta pendente vira o estado `input_required`.

<p>

[![License](https://img.shields.io/github/license/Solierrr/ai-operational)](https://github.com/Solierrr/ai-operational/blob/main/LICENSE)
[![GitHub Last Commit](https://img.shields.io/github/last-commit/Solierrr/ai-operational)](https://github.com/Solierrr/ai-operational/commits)
[![GitHub Issues](https://img.shields.io/github/issues/Solierrr/ai-operational)](https://github.com/Solierrr/ai-operational/issues)
[![GitHub Pull Requests](https://img.shields.io/github/issues-pr/Solierrr/ai-operational)](https://github.com/Solierrr/ai-operational/pulls)
[![Release](https://img.shields.io/github/v/release/Solierrr/ai-operational)](https://github.com/Solierrr/ai-operational/releases)

</p>

<p>
  <a href="https://github.com/syvixor/skills-icons">
    <img src="https://skills.syvixor.com/api/icons?i=python,fastapi,langchain,mongodb,redis,docker" height="48" alt="Stack">
  </a>
</p>

## Aprofunde-se no Projeto!

- [ARCHITECTURE.md](./ARCHITECTURE.md)
- [RUNNING.md](./RUNNING.md)

## Contribuindo

- Escreva commits em Conventional Commits, em inglês e minúsculas (`feat:`, `fix:` etc.).
- Todo PR deve usar o `.github/pull_request_template.md` deste repositório.
