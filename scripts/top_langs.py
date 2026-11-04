#!/usr/bin/env python3
"""Gera profile/top-langs.svg somando as linguagens dos repositórios (inclusive forks escolhidos).

Usa a API do GitHub com o token em GH_TOKEN (precisa de acesso aos repositórios privados).
Só stdlib — roda direto no runner do GitHub Actions.
"""
import json
import os
import sys
import urllib.request
from html import escape

USER = "Kaike-png"
OUTPUT = "profile/top-langs.svg"
LANGS_COUNT = 8

# Forks que contam (por padrão forks são ignorados).
INCLUDE_FORKS = {"SsagCore", "SsagVb", "AppSsagDesktop", "wacrm"}

# Repositórios que nunca contam (estudo, cópias, template).
EXCLUDE_REPOS = {
    "Kaike-png",
    "Cafeteria-Serenatto",
    "AluraBooks",
    "Treinando_HTML-CSS",
    "portifolio",
    "DomynixERP",
    "SSAG-VB-web",
}

# Linguagens ignoradas em todos os repositórios (markup/estilo/bibliotecas copiadas).
IGNORE_LANGS = {"HTML", "CSS", "SCSS", "Less", "Handlebars", "Dockerfile"}

# Linguagens ignoradas só em repositórios específicos (ex.: JS de bibliotecas no projeto).
IGNORE_LANGS_PER_REPO = {
    "SsagCore": {"JavaScript"},
    "SsagVb": {"JavaScript"},
}

# Cores do GitHub Linguist.
COLORS = {
    "C#": "#178600",
    "Visual Basic .NET": "#945db7",
    "ASP.NET": "#9400ff",
    "Classic ASP": "#6a40fd",
    "TypeScript": "#3178c6",
    "JavaScript": "#f1e05a",
    "Python": "#3572A5",
    "PLpgSQL": "#336790",
    "TSQL": "#e38c00",
    "Shell": "#89e051",
    "PowerShell": "#012456",
    "Svelte": "#ff3e00",
    "Go": "#00ADD8",
    "Rust": "#dea584",
    "Java": "#b07219",
    "PHP": "#4F5D95",
}

# Tema tokyonight (mesmo do card de stats).
THEME = {"bg": "#1a1b27", "title": "#70a5fd", "text": "#38bdae"}


def api(path, token):
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def list_repos(token):
    repos, page = [], 1
    while True:
        batch = api(f"/user/repos?affiliation=owner&per_page=100&page={page}", token)
        repos += batch
        if len(batch) < 100:
            return repos
        page += 1


def collect(token):
    totals = {}
    for repo in list_repos(token):
        name = repo["name"]
        if repo["owner"]["login"] != USER or name in EXCLUDE_REPOS or repo.get("archived"):
            continue
        if repo["fork"] and name not in INCLUDE_FORKS:
            continue
        skip = IGNORE_LANGS | IGNORE_LANGS_PER_REPO.get(name, set())
        langs = api(f"/repos/{USER}/{name}/languages", token)
        used = {k: v for k, v in langs.items() if k not in skip}
        if os.environ.get("VERBOSE"):  # logs do Actions são públicos: não expor repos privados
            print(f"{name}: " + ", ".join(f"{k}={v // 1024}K" for k, v in used.items()), file=sys.stderr)
        for lang, size in used.items():
            totals[lang] = totals.get(lang, 0) + size
    return totals


def render(totals):
    ranked = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:LANGS_COUNT]
    total = sum(v for _, v in ranked) or 1
    items = [(lang, size * 100 / total) for lang, size in ranked]

    width, bar_w, pad = 300, 250, 25
    rows = (len(items) + 1) // 2
    height = 90 + rows * 25

    # Barra de progresso segmentada.
    bar, x = [], 0.0
    for lang, pct in items:
        w = bar_w * pct / 100
        bar.append(
            f'<rect x="{x:.2f}" y="0" width="{w:.2f}" height="8" fill="{COLORS.get(lang, "#858585")}"/>'
        )
        x += w

    # Legenda em duas colunas.
    legend = []
    for i, (lang, pct) in enumerate(items):
        col, row = i % 2, i // 2
        lx, ly = col * 150, row * 25
        color = COLORS.get(lang, "#858585")
        legend.append(
            f'<g transform="translate({lx},{ly})">'
            f'<circle cx="5" cy="6" r="5" fill="{color}"/>'
            f'<text x="15" y="10" class="lang">{escape(lang)} {pct:.2f}%</text></g>'
        )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" fill="none" role="img" aria-labelledby="titleId">
  <title id="titleId">Most Used Languages</title>
  <style>
    .header {{ font: 600 18px 'Segoe UI', Ubuntu, Sans-Serif; fill: {THEME['title']}; }}
    .lang {{ font: 400 11px 'Segoe UI', Ubuntu, Sans-Serif; fill: {THEME['text']}; }}
  </style>
  <rect x="0.5" y="0.5" rx="4.5" width="{width - 1}" height="{height - 1}" fill="{THEME['bg']}"/>
  <text x="{pad}" y="35" class="header">Most Used Languages</text>
  <svg x="{pad}" y="55">
    <mask id="rounded"><rect x="0" y="0" width="{bar_w}" height="8" rx="5" fill="white"/></mask>
    <g mask="url(#rounded)">{''.join(bar)}</g>
  </svg>
  <g transform="translate({pad},80)">{''.join(legend)}</g>
</svg>
"""


def main():
    token = os.environ.get("GH_TOKEN")
    if not token:
        sys.exit("GH_TOKEN não definido")
    totals = collect(token)
    if not totals:
        sys.exit("Nenhuma linguagem encontrada — token sem acesso aos repositórios?")
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(render(totals))
    print(f"OK: {OUTPUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
