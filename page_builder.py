"""
page_builder.py — Gerador da página web interativa do Boletim DOU

FIX v2 — Corte de conteúdo:
  O bug anterior: max-height calculado por JS + overflow:hidden cortava
  conteúdo quando um órgão era expandido dentro de uma seção já aberta.
  
  A correção: após a transição de abertura terminar (transitionend),
  setar max-height: none. Assim o conteúdo NUNCA é cortado, não importa
  quantos sub-elementos sejam expandidos depois. Para fechar, primeiro
  restaurar o max-height fixo, forçar reflow, depois animar para 0.
"""

import html as html_mod
import logging
from datetime import datetime
from typing import Optional

import config

logger = logging.getLogger(__name__)

DIAS = [
    "Segunda-feira", "Terça-feira", "Quarta-feira",
    "Quinta-feira", "Sexta-feira", "Sábado", "Domingo",
]
MESES = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]


def _esc(text: str) -> str:
    return html_mod.escape(text) if text else ""


class PageBuilder:
    """Gera a página HTML interativa do boletim."""

    def build(self, dados: dict) -> Optional[str]:
        if not dados.get("secoes") or dados.get("total_publicacoes", 0) == 0:
            return None

        data_regular = dados["data_regular"]
        data_extra = dados.get("data_extra")
        total = dados["total_publicacoes"]

        try:
            dt = datetime.strptime(data_regular, "%d/%m/%Y")
            data_ext = f"{DIAS[dt.weekday()]}, {dt.day} de {MESES[dt.month - 1]} de {dt.year}"
        except Exception:
            data_ext = data_regular

        secoes_html = self._build_secoes(dados["secoes"])
        resumo_html = self._build_resumo(dados["secoes"])
        extra_banner = ""
        if data_extra and any("Extra" in k for k in dados["secoes"]):
            extra_banner = f"""
            <div class="extra-banner">
                <span>⚡</span> Inclui Edições Extras de {_esc(data_extra)}
            </div>"""

        return self._template(
            data_ext=data_ext,
            data_regular=data_regular,
            total=total,
            resumo=resumo_html,
            extra_banner=extra_banner,
            secoes=secoes_html,
        )

    def _build_resumo(self, secoes: dict) -> str:
        items = []
        for nome, orgaos in secoes.items():
            cnt = sum(len(p) for p in orgaos.values())
            is_extra = "Extra" in nome
            dot_class = "dot-extra" if is_extra else "dot-regular"
            items.append(
                f'<div class="resumo-item">'
                f'<span class="resumo-dot {dot_class}"></span>'
                f'<span class="resumo-nome">{_esc(nome)}</span>'
                f'<span class="resumo-count">{cnt}</span>'
                f'</div>'
            )
        return "\n".join(items)

    def _build_secoes(self, secoes: dict) -> str:
        parts = []
        idx = 0
        for nome_secao, orgaos in secoes.items():
            parts.append(self._build_secao(nome_secao, orgaos, idx))
            idx += 1
        return "\n".join(parts)

    def _build_secao(self, nome: str, orgaos: dict, idx: int) -> str:
        is_extra = "Extra" in nome
        cls = "secao-extra" if is_extra else "secao-regular"
        total_secao = sum(len(p) for p in orgaos.values())

        orgaos_html = "\n".join(
            self._build_orgao(n, pubs) for n, pubs in orgaos.items()
        )

        return f"""
        <div class="secao {cls}" data-secao="{_esc(nome)}">
            <div class="secao-header" onclick="toggleSecao(this)" role="button" tabindex="0">
                <div class="secao-titulo-wrap">
                    <span class="secao-chevron">▸</span>
                    <h2 class="secao-titulo">{_esc(nome)}</h2>
                    <span class="secao-badge">{total_secao}</span>
                    <span class="secao-hint">clique para expandir</span>
                </div>
            </div>
            <div class="secao-conteudo collapsed">
                {orgaos_html}
            </div>
        </div>"""

    def _build_orgao(self, nome: str, pubs: list) -> str:
        pubs_html = "\n".join(self._build_pub(p) for p in pubs)
        return f"""
        <div class="orgao" data-orgao="{_esc(nome)}">
            <div class="orgao-header" onclick="toggleOrgao(this)" role="button" tabindex="0">
                <span class="orgao-chevron">▸</span>
                <span class="orgao-nome">{_esc(nome)}</span>
                <span class="orgao-count">{len(pubs)}</span>
            </div>
            <div class="orgao-pubs orgao-collapsed">
                {pubs_html}
            </div>
        </div>"""

    def _build_pub(self, pub: dict) -> str:
        titulo = _esc(pub.get("titulo", "Sem título"))
        ementa = _esc(pub.get("ementa", "")[:500])
        tipo = _esc(pub.get("tipo_ato", ""))
        sub = _esc(pub.get("sub_orgao", ""))
        url = _esc(pub.get("url", ""))

        tipo_html = f'<span class="pub-tipo">{tipo}</span>' if tipo else ""
        sub_html = f'<span class="pub-sub">↳ {sub}</span>' if sub else ""
        ementa_html = f'<p class="pub-ementa">{ementa}</p>' if ementa else ""
        link_html = f'<a href="{url}" target="_blank" rel="noopener" class="pub-link">Ler íntegra →</a>' if url else ""

        return f"""
        <div class="pub" data-search="{titulo.lower()} {ementa.lower()} {tipo.lower()} {sub.lower()}">
            {tipo_html}
            {sub_html}
            <a href="{url}" target="_blank" rel="noopener" class="pub-titulo">{titulo}</a>
            {ementa_html}
            {link_html}
        </div>"""

    def _template(self, **kw) -> str:
        return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Boletim DOU — {_esc(kw['data_regular'])}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:wght@400;600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root {{
  --navy: #0F172A;
  --blue: #1E3A5F;
  --blue-light: #F0F7FF;
  --red: #B91C1C;
  --red-light: #FEF2F2;
  --gray-50: #F8FAFC;
  --gray-100: #F1F5F9;
  --gray-200: #E2E8F0;
  --gray-400: #94A3B8;
  --gray-500: #64748B;
  --gray-700: #334155;
  --gray-900: #0F172A;
  --font-serif: 'Source Serif 4', Georgia, serif;
  --font-sans: 'Inter', -apple-system, system-ui, sans-serif;
  --max-w: 860px;
}}

* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{
  font-family: var(--font-sans);
  background: var(--gray-100);
  color: var(--gray-900);
  line-height: 1.6;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}}

.header {{
  background: var(--navy);
  padding: 28px 24px 22px;
  flex-shrink: 0;
}}
.header-inner {{
  max-width: var(--max-w);
  margin: 0 auto;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}}
.header h1 {{
  font-family: var(--font-serif);
  font-size: 26px;
  font-weight: 700;
  color: #fff;
  letter-spacing: -0.3px;
}}
.header .subtitle {{
  font-size: 11px;
  color: var(--gray-400);
  letter-spacing: 1.5px;
  text-transform: uppercase;
  margin-top: 4px;
}}
.header .total-badge {{
  background: var(--blue);
  color: #E2E8F0;
  font-size: 13px;
  font-weight: 600;
  padding: 5px 14px;
  border-radius: 4px;
  white-space: nowrap;
}}

.data-bar {{
  background: #fff;
  border-bottom: 1px solid var(--gray-200);
  padding: 14px 24px;
  flex-shrink: 0;
}}
.data-bar-inner {{
  max-width: var(--max-w);
  margin: 0 auto;
}}
.data-bar h2 {{
  font-family: var(--font-serif);
  font-size: 16px;
  font-weight: 600;
  color: var(--gray-700);
}}
.data-bar .hora {{
  font-size: 11px;
  color: var(--gray-400);
  margin-top: 2px;
}}

.container {{
  max-width: var(--max-w);
  margin: 0 auto;
  padding: 20px 24px 60px;
  width: 100%;
  flex: 1;
}}

.search-wrap {{
  position: relative;
  margin-bottom: 20px;
}}
.search-wrap input {{
  width: 100%;
  padding: 12px 16px 12px 42px;
  border: 2px solid var(--gray-200);
  border-radius: 8px;
  font-size: 14px;
  font-family: var(--font-sans);
  background: #fff;
  transition: border-color 0.2s;
  outline: none;
}}
.search-wrap input:focus {{
  border-color: var(--blue);
}}
.search-wrap input::placeholder {{
  color: var(--gray-400);
}}
.search-wrap .search-icon {{
  position: absolute;
  left: 14px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--gray-400);
  font-size: 16px;
  pointer-events: none;
}}
.search-info {{
  font-size: 12px;
  color: var(--gray-500);
  margin: -12px 0 16px;
  display: none;
}}
.search-info.visible {{ display: block; }}

.resumo {{
  background: #fff;
  border-radius: 8px;
  padding: 16px 20px;
  margin-bottom: 16px;
  border: 1px solid var(--gray-200);
}}
.resumo-label {{
  font-size: 10px;
  font-weight: 700;
  color: var(--gray-400);
  text-transform: uppercase;
  letter-spacing: 1.5px;
  margin-bottom: 10px;
}}
.resumo-item {{
  display: flex;
  align-items: center;
  padding: 3px 0;
}}
.resumo-dot {{
  width: 7px; height: 7px;
  border-radius: 50%;
  margin-right: 10px;
  flex-shrink: 0;
}}
.dot-regular {{ background: var(--blue); }}
.dot-extra {{ background: var(--red); }}
.resumo-nome {{
  font-size: 13px;
  color: var(--gray-700);
  flex: 1;
}}
.resumo-count {{
  font-size: 13px;
  font-weight: 700;
  color: var(--gray-900);
}}

.extra-banner {{
  background: var(--red-light);
  border-left: 3px solid var(--red);
  padding: 10px 16px;
  margin-bottom: 20px;
  border-radius: 0 6px 6px 0;
  font-size: 12px;
  font-weight: 600;
  color: #991B1B;
}}

.secao {{
  background: #fff;
  border-radius: 8px;
  margin-bottom: 12px;
  border: 1px solid var(--gray-200);
  overflow: hidden;
  transition: box-shadow 0.2s;
}}
.secao:hover {{
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}}
.secao-header {{
  padding: 14px 20px;
  cursor: pointer;
  user-select: none;
  display: flex;
  align-items: center;
  transition: background 0.15s;
}}
.secao-header:hover {{
  background: var(--gray-50);
}}
.secao-regular .secao-header {{
  border-left: 4px solid var(--blue);
}}
.secao-extra .secao-header {{
  border-left: 4px solid var(--red);
}}
.secao-titulo-wrap {{
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
}}
.secao-chevron {{
  font-size: 14px;
  color: var(--gray-400);
  transition: transform 0.25s;
  flex-shrink: 0;
}}
.secao.open .secao-chevron {{
  transform: rotate(90deg);
}}
.secao-titulo {{
  font-family: var(--font-serif);
  font-size: 15px;
  font-weight: 700;
  color: var(--gray-900);
  flex: 1;
  letter-spacing: 0.3px;
}}
.secao-extra .secao-titulo {{ color: var(--red); }}
.secao-badge {{
  background: var(--gray-100);
  color: var(--gray-700);
  font-size: 12px;
  font-weight: 700;
  padding: 2px 10px;
  border-radius: 12px;
  flex-shrink: 0;
}}
.secao-hint {{
  font-size: 10px;
  color: var(--gray-400);
  font-style: italic;
  margin-left: 8px;
  transition: opacity 0.2s;
}}
.secao.open .secao-hint {{
  opacity: 0;
}}

/* SECAO-CONTEUDO: transição controlada por JS.
   Quando aberto: max-height animado → depois max-height:none (via JS).
   Quando fechado: max-height:scrollHeight → max-height:0 (via JS). */
.secao-conteudo {{
  max-height: 0;
  overflow: hidden;
  transition: max-height 0.35s ease;
}}

.orgao {{
  padding: 0 20px;
}}
.orgao-header {{
  display: flex;
  align-items: center;
  cursor: pointer;
  user-select: none;
  transition: background 0.15s;
  background: var(--gray-100);
  border-bottom: 1px solid var(--gray-200);
  border-radius: 4px;
  padding: 8px 6px;
  margin: 0 -6px;
}}
.orgao-header:hover {{
  background: var(--gray-200);
}}
.orgao-chevron {{
  font-size: 11px;
  color: var(--gray-400);
  transition: transform 0.25s;
  flex-shrink: 0;
  margin-right: 8px;
}}
.orgao.open .orgao-chevron {{
  transform: rotate(90deg);
}}
.orgao-nome {{
  font-family: var(--font-serif);
  font-size: 13.5px;
  color: var(--gray-700);
  font-weight: 600;
  flex: 1;
}}
.orgao-count {{
  font-size: 12px;
  color: var(--gray-500);
  background: var(--gray-100);
  padding: 1px 8px;
  border-radius: 10px;
  font-weight: 600;
}}

/* ORGAO-PUBS: mesma lógica de max-height → none */
.orgao-pubs {{
  max-height: 0;
  overflow: hidden;
  transition: max-height 0.3s ease;
}}

.pub {{
  padding: 12px 0;
  border-bottom: 1px solid var(--gray-100);
}}
.pub:last-child {{ border-bottom: none; }}
.pub.hidden {{ display: none; }}
.pub-tipo {{
  display: inline-block;
  background: var(--gray-100);
  color: var(--gray-700);
  font-size: 10px;
  font-weight: 600;
  padding: 2px 7px;
  border-radius: 3px;
  text-transform: uppercase;
  letter-spacing: 0.4px;
  margin-bottom: 4px;
}}
.pub-sub {{
  display: block;
  font-size: 11px;
  color: var(--gray-400);
  font-style: italic;
  margin-bottom: 2px;
}}
.pub-titulo {{
  display: block;
  font-family: var(--font-serif);
  font-size: 14px;
  font-weight: 700;
  color: var(--gray-900);
  text-decoration: none;
  line-height: 1.35;
  margin-bottom: 4px;
  transition: color 0.15s;
}}
.pub-titulo:hover {{ color: var(--blue); }}
.pub-ementa {{
  font-size: 12.5px;
  color: var(--gray-500);
  line-height: 1.55;
  margin-bottom: 6px;
}}
.pub-link {{
  font-size: 11px;
  color: #2563EB;
  text-decoration: none;
  font-weight: 500;
  letter-spacing: 0.2px;
}}
.pub-link:hover {{ text-decoration: underline; }}

mark {{
  background: #FEF08A;
  color: inherit;
  padding: 0 1px;
  border-radius: 2px;
}}

/* ═══ BREADCRUMB FIXO (scroll tracker) ═══ */
.scroll-tracker {{
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 100;
  background: rgba(15, 23, 42, 0.95);
  backdrop-filter: blur(8px);
  padding: 8px 24px;
  transform: translateY(-100%);
  transition: transform 0.25s ease;
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
}}
.scroll-tracker.visible {{
  transform: translateY(0);
}}
.scroll-tracker-inner {{
  max-width: var(--max-w);
  margin: 0 auto;
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: var(--font-sans);
  font-size: 12px;
  color: #94A3B8;
}}
.scroll-tracker .st-secao {{
  color: #E2E8F0;
  font-weight: 600;
}}
.scroll-tracker .st-sep {{
  color: #475569;
}}
.scroll-tracker .st-orgao {{
  color: #94A3B8;
  font-weight: 500;
}}

.footer {{
  text-align: center;
  padding: 24px;
  font-size: 11px;
  color: var(--gray-400);
  line-height: 1.7;
  flex-shrink: 0;
}}
.footer a {{ color: var(--gray-500); }}

@media (max-width: 640px) {{
  .header-inner {{ flex-direction: column; gap: 10px; }}
  .container {{ padding: 12px 12px 40px; }}
  .secao-header {{ padding: 12px 14px; }}
  .orgao {{ padding: 0 14px; }}
}}
</style>
</head>
<body>

<div class="header">
  <div class="header-inner">
    <div>
      <h1>BOLETIM DOU</h1>
      <div class="subtitle">Diário Oficial da União — Seções 1, 2 e 3</div>
    </div>
    <span class="total-badge">{kw['total']} atos</span>
  </div>
</div>

<div class="data-bar">
  <div class="data-bar-inner">
    <h2>{_esc(kw['data_ext'])}</h2>
    <div class="hora">Gerado às {datetime.now().strftime("%H:%M")} (Brasília)</div>
  </div>
</div>

<!-- BREADCRUMB FIXO (aparece ao rolar dentro de seções) -->
<div class="scroll-tracker" id="scrollTracker">
  <div class="scroll-tracker-inner">
    <span class="st-secao" id="stSecao"></span>
    <span class="st-sep" id="stSep">›</span>
    <span class="st-orgao" id="stOrgao"></span>
  </div>
</div>

<div class="container">
  <div class="search-wrap">
    <span class="search-icon">🔍</span>
    <input type="text" id="searchInput" placeholder="Buscar publicações (mínimo 3 caracteres)..." autocomplete="off">
  </div>
  <div class="search-info" id="searchInfo"></div>

  <div class="resumo">
    <div class="resumo-label">Nesta edição</div>
    {kw['resumo']}
  </div>

  {kw['extra_banner']}

  <div id="secoes">
    {kw['secoes']}
  </div>
</div>

<div class="footer">
  Fonte: <a href="https://www.in.gov.br/consulta" target="_blank">Imprensa Nacional</a><br>
  Órgãos: Poderes Executivo, Legislativo e Judiciário · Presidência da República · Min. da Fazenda · Entidades de Fiscalização
</div>

<script>
// ═══════════════════════════════════════════════════════════
// COLAPSAR / EXPANDIR — com max-height:none após transição
// Isso ELIMINA o bug de corte de conteúdo.
//
// Lógica:
//   ABRIR: max-height = scrollHeight → transição → transitionend → max-height = none
//   FECHAR: max-height = scrollHeight (fixo) → reflow → max-height = 0 → transição
// ═══════════════════════════════════════════════════════════

function expandPanel(panel) {{
  // Remove listener antigo se existir
  panel.removeEventListener('transitionend', panel._onExpanded);

  // Listener que seta max-height:none quando a animação terminar
  panel._onExpanded = function handler(e) {{
    if (e.propertyName === 'max-height') {{
      panel.style.maxHeight = 'none';
      panel.style.overflow = 'visible';
      panel.removeEventListener('transitionend', handler);
    }}
  }};
  panel.addEventListener('transitionend', panel._onExpanded);

  // Iniciar animação
  panel.style.overflow = 'hidden';
  panel.style.maxHeight = panel.scrollHeight + 'px';
}}

function collapsePanel(panel) {{
  // Remove listener de expansão se estiver pendente
  if (panel._onExpanded) {{
    panel.removeEventListener('transitionend', panel._onExpanded);
  }}

  // Se já está com max-height:none, precisa fixar o valor atual
  // para que a transição CSS funcione (none → 0 não anima)
  panel.style.overflow = 'hidden';
  panel.style.maxHeight = panel.scrollHeight + 'px';

  // Forçar reflow para o browser registrar o valor fixo
  panel.offsetHeight; // eslint-disable-line no-unused-expressions

  // Agora animar para 0
  panel.style.maxHeight = '0';
}}

function toggleSecao(header) {{
  var secao = header.closest('.secao');
  var conteudo = secao.querySelector('.secao-conteudo');
  var isOpen = secao.classList.contains('open');

  if (isOpen) {{
    collapsePanel(conteudo);
    secao.classList.remove('open');
  }} else {{
    expandPanel(conteudo);
    secao.classList.add('open');
  }}
}}

function toggleOrgao(header) {{
  var orgao = header.closest('.orgao');
  var pubs = orgao.querySelector('.orgao-pubs');
  var isOpen = orgao.classList.contains('open');

  if (isOpen) {{
    collapsePanel(pubs);
    orgao.classList.remove('open');
  }} else {{
    expandPanel(pubs);
    orgao.classList.add('open');

    // Atualizar o painel pai (seção) se ele ainda tiver max-height fixo
    var secaoConteudo = orgao.closest('.secao-conteudo');
    if (secaoConteudo && secaoConteudo.style.maxHeight !== 'none') {{
      // Pai ainda está em transição — atualizar após expansão do órgão
      secaoConteudo.style.maxHeight = secaoConteudo.scrollHeight + pubs.scrollHeight + 'px';
    }}
    // Se pai já tem max-height:none, ele cresce automaticamente — nada a fazer.
  }}
}}

// ═══ ABRIR PROGRAMÁTICO (para busca) ═══
function openSecao(secao) {{
  if (secao.classList.contains('open')) return;
  var conteudo = secao.querySelector('.secao-conteudo');
  expandPanel(conteudo);
  secao.classList.add('open');
}}

function openOrgao(orgao) {{
  if (orgao.classList.contains('open')) return;
  var pubs = orgao.querySelector('.orgao-pubs');
  expandPanel(pubs);
  orgao.classList.add('open');
}}

function closeOrgao(orgao) {{
  if (!orgao.classList.contains('open')) return;
  var pubs = orgao.querySelector('.orgao-pubs');
  collapsePanel(pubs);
  orgao.classList.remove('open');
}}

// ═══ BUSCA EM TEMPO REAL ═══
var searchInput = document.getElementById('searchInput');
var searchInfo = document.getElementById('searchInfo');

searchInput.addEventListener('input', function() {{
  var query = this.value.trim().toLowerCase();

  // Limpar highlights anteriores
  document.querySelectorAll('mark').forEach(function(m) {{
    m.replaceWith(m.textContent);
  }});

  if (query.length < 3) {{
    // Mostrar tudo, colapsar órgãos
    document.querySelectorAll('.pub').forEach(function(p) {{ p.classList.remove('hidden'); }});
    document.querySelectorAll('.orgao').forEach(function(o) {{
      o.style.display = '';
      closeOrgao(o);
    }});
    document.querySelectorAll('.secao').forEach(function(s) {{ s.style.display = ''; }});
    searchInfo.classList.remove('visible');
    return;
  }}

  var totalVisible = 0;

  // Filtrar publicações
  document.querySelectorAll('.pub').forEach(function(pub) {{
    var text = pub.getAttribute('data-search') || '';
    if (text.includes(query)) {{
      pub.classList.remove('hidden');
      totalVisible++;
      highlightText(pub, query);
    }} else {{
      pub.classList.add('hidden');
    }}
  }});

  // Esconder órgãos sem pubs visíveis, expandir os que têm
  document.querySelectorAll('.orgao').forEach(function(orgao) {{
    var visiblePubs = orgao.querySelectorAll('.pub:not(.hidden)');
    if (visiblePubs.length === 0) {{
      orgao.style.display = 'none';
    }} else {{
      orgao.style.display = '';
      openOrgao(orgao);
    }}
  }});

  // Esconder seções sem órgãos visíveis, expandir as que têm
  document.querySelectorAll('.secao').forEach(function(secao) {{
    var visibleOrgaos = secao.querySelectorAll('.orgao:not([style*="display: none"])');
    if (visibleOrgaos.length === 0) {{
      secao.style.display = 'none';
    }} else {{
      secao.style.display = '';
      openSecao(secao);
    }}
  }});

  searchInfo.textContent = totalVisible + ' resultado(s) para "' + this.value.trim() + '"';
  searchInfo.classList.add('visible');
}});

function highlightText(container, query) {{
  var walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT);
  var nodes = [];
  while (walker.nextNode()) nodes.push(walker.currentNode);

  nodes.forEach(function(node) {{
    var text = node.textContent;
    var lower = text.toLowerCase();
    var idx = lower.indexOf(query);
    if (idx === -1) return;
    if (node.parentElement.tagName === 'MARK') return;
    if (node.parentElement.tagName === 'SCRIPT') return;
    if (node.parentElement.tagName === 'STYLE') return;

    var before = text.slice(0, idx);
    var match = text.slice(idx, idx + query.length);
    var after = text.slice(idx + query.length);

    var mark = document.createElement('mark');
    mark.textContent = match;

    var parent = node.parentNode;
    parent.insertBefore(document.createTextNode(before), node);
    parent.insertBefore(mark, node);
    node.textContent = after;
  }});
}}

// Atalho: Ctrl+K ou / para focar na busca
document.addEventListener('keydown', function(e) {{
  if ((e.ctrlKey && e.key === 'k') || (e.key === '/' && document.activeElement.tagName !== 'INPUT')) {{
    e.preventDefault();
    searchInput.focus();
  }}
}});

// ═══ SCROLL TRACKER (breadcrumb fixo) ═══
// Mostra "Seção X › Órgão Y" conforme o usuário rola a página.
// Só aparece quando está dentro de uma seção aberta.
(function() {{
  var tracker = document.getElementById('scrollTracker');
  var stSecao = document.getElementById('stSecao');
  var stSep = document.getElementById('stSep');
  var stOrgao = document.getElementById('stOrgao');
  var lastSecao = '';
  var lastOrgao = '';
  var ticking = false;

  function updateTracker() {{
    var secaoAtual = '';
    var orgaoAtual = '';
    var viewportTop = window.scrollY + 60; // offset para o tracker não cobrir

    // Encontrar a última seção aberta cujo topo passou do viewport
    var secoes = document.querySelectorAll('.secao.open');
    for (var i = 0; i < secoes.length; i++) {{
      var rect = secoes[i].getBoundingClientRect();
      // A seção está visível se seu topo está acima do meio da tela
      // e seu bottom está abaixo do topo da tela
      if (rect.top < 120 && rect.bottom > 0) {{
        secaoAtual = secoes[i].getAttribute('data-secao') || '';

        // Dentro dessa seção, encontrar o último órgão aberto visível
        var orgaos = secoes[i].querySelectorAll('.orgao.open');
        for (var j = 0; j < orgaos.length; j++) {{
          var oRect = orgaos[j].getBoundingClientRect();
          if (oRect.top < 120 && oRect.bottom > 0) {{
            orgaoAtual = orgaos[j].getAttribute('data-orgao') || '';
          }}
        }}
      }}
    }}

    // Atualizar DOM só se mudou (evitar repaints)
    if (secaoAtual !== lastSecao || orgaoAtual !== lastOrgao) {{
      lastSecao = secaoAtual;
      lastOrgao = orgaoAtual;

      if (secaoAtual) {{
        stSecao.textContent = secaoAtual;
        stSep.style.display = orgaoAtual ? '' : 'none';
        stOrgao.textContent = orgaoAtual;
        tracker.classList.add('visible');
      }} else {{
        tracker.classList.remove('visible');
      }}
    }}

    ticking = false;
  }}

  window.addEventListener('scroll', function() {{
    if (!ticking) {{
      requestAnimationFrame(updateTracker);
      ticking = true;
    }}
  }}, {{ passive: true }});
}})();
</script>

</body>
</html>"""
