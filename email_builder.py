"""
email_builder.py — Gerador do boletim HTML

Design inspirado em newsletters jurídicas de primeira linha:
sóbrio, editorial, fácil de escanear. Otimizado para
Outlook, Gmail e Apple Mail.
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


class EmailBuilder:

    def build(self, dados: dict) -> Optional[str]:
        if not dados.get("secoes") or dados.get("total_publicacoes", 0) == 0:
            return None

        resumo = {}
        for ns, orgs in dados["secoes"].items():
            resumo[ns] = sum(len(p) for p in orgs.values())

        corpo = self._corpo(dados["secoes"])
        return self._template(
            dados["data_regular"],
            dados.get("data_extra"),
            dados["total_publicacoes"],
            resumo,
            corpo,
        )

    def build_subject(self, dados: dict) -> str:
        d = dados.get("data_regular", "")
        t = dados.get("total_publicacoes", 0)
        ex = " + Ed. Extra" if any("Extra" in k for k in dados.get("secoes", {})) else ""
        return f"Boletim DOU Tributário — {d}{ex} — {t} ato(s)"

    # ─── CORPO ─────────────────────────────────────────

    def _corpo(self, secoes: dict) -> str:
        parts = []
        for nome, orgaos in secoes.items():
            parts.append(self._secao(nome, orgaos))
        return "\n".join(parts)

    def _secao(self, nome: str, orgaos: dict) -> str:
        is_extra = "Extra" in nome
        # Cores: azul escuro para regular, vermelho escuro para extra
        cor = "#B91C1C" if is_extra else "#1E3A5F"
        bg = "#FEF2F2" if is_extra else "#F0F7FF"
        icone = "EDIÇÃO EXTRA" if is_extra else ""

        orgaos_html = "\n".join(
            self._orgao(n, pubs) for n, pubs in orgaos.items()
        )

        badge = ""
        if icone:
            badge = f"""<span style="display:inline-block;background:#B91C1C;color:#fff;font-size:9px;font-weight:700;padding:2px 7px;border-radius:2px;letter-spacing:0.8px;margin-left:8px;vertical-align:middle;">{icone}</span>"""

        return f"""
<!-- ══ SEÇÃO ══ -->
<tr><td style="padding:32px 32px 0 32px;">
  <table width="100%" cellpadding="0" cellspacing="0" style="border-bottom:2px solid {cor};">
    <tr><td style="padding:0 0 8px 0;">
      <span style="font-family:Georgia,'Times New Roman',serif;font-size:15px;font-weight:700;color:{cor};text-transform:uppercase;letter-spacing:1.5px;">{_esc(nome)}</span>
      {badge}
    </td></tr>
  </table>
</td></tr>
{orgaos_html}
"""

    def _orgao(self, nome: str, pubs: list) -> str:
        rows = "\n".join(self._pub(p, i) for i, p in enumerate(pubs))
        return f"""
<tr><td style="padding:16px 32px 0 32px;">
  <!-- Cabeçalho órgão -->
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr><td style="padding:0 0 6px 0;">
      <span style="font-family:Georgia,'Times New Roman',serif;font-size:12px;color:#64748B;font-weight:400;font-style:italic;">{_esc(nome)} — {len(pubs)} ato(s)</span>
    </td></tr>
  </table>
  <!-- Publicações -->
  <table width="100%" cellpadding="0" cellspacing="0" style="border-left:3px solid #E2E8F0;">
    {rows}
  </table>
</td></tr>
"""

    def _pub(self, pub: dict, idx: int) -> str:
        titulo = _esc(pub.get("titulo", "Sem título"))
        ementa = pub.get("ementa", "")
        tipo = pub.get("tipo_ato", "")
        sub = pub.get("sub_orgao", "")
        url = pub.get("url", "")

        # Ementa: limitar e escapar
        if ementa:
            em_text = _esc(ementa[:280])
            if len(ementa) > 280:
                em_text += "…"
        else:
            em_text = ""

        # Tipo de ato — badge discreto
        tipo_html = ""
        if tipo:
            tipo_html = f"""<span style="display:inline-block;background:#F1F5F9;color:#475569;font-family:-apple-system,Helvetica,Arial,sans-serif;font-size:10px;font-weight:600;padding:1px 6px;border-radius:2px;text-transform:uppercase;letter-spacing:0.4px;margin-bottom:4px;">{_esc(tipo[:40])}</span><br/>"""

        # Sub-órgão
        sub_html = ""
        if sub:
            sub_html = f"""<span style="font-family:-apple-system,Helvetica,Arial,sans-serif;font-size:10px;color:#94A3B8;">↳ {_esc(sub[:80])}</span><br/>"""

        # Ementa
        ementa_html = ""
        if em_text:
            ementa_html = f"""<p style="font-family:Georgia,'Times New Roman',serif;font-size:12px;color:#64748B;line-height:1.55;margin:4px 0 0 0;">{em_text}</p>"""

        # Link
        link_html = ""
        if url:
            link_html = f"""<a href="{_esc(url)}" target="_blank" style="font-family:-apple-system,Helvetica,Arial,sans-serif;font-size:10px;color:#2563EB;text-decoration:none;font-weight:500;letter-spacing:0.2px;">LER ÍNTEGRA →</a>"""

        return f"""
    <tr><td style="padding:10px 0 10px 16px;border-bottom:1px solid #F1F5F9;">
      {tipo_html}
      {sub_html}
      <a href="{_esc(url)}" target="_blank" style="font-family:Georgia,'Times New Roman',serif;font-size:14px;font-weight:700;color:#0F172A;text-decoration:none;line-height:1.35;">{titulo}</a>
      {ementa_html}
      <div style="margin-top:6px;">{link_html}</div>
    </td></tr>
"""

    # ─── TEMPLATE PRINCIPAL ────────────────────────────

    def _template(self, data_regular, data_extra, total, resumo, corpo) -> str:
        # Data por extenso
        try:
            dt = datetime.strptime(data_regular, "%d/%m/%Y")
            data_ext = f"{DIAS[dt.weekday()]}, {dt.day} de {MESES[dt.month - 1]} de {dt.year}"
        except Exception:
            data_ext = data_regular

        # Sumário
        sumario_rows = []
        for sec, cnt in resumo.items():
            is_ex = "Extra" in sec
            dot_c = "#B91C1C" if is_ex else "#1E3A5F"
            sumario_rows.append(f"""
            <tr><td style="padding:2px 0;">
              <span style="display:inline-block;width:6px;height:6px;background:{dot_c};border-radius:50%;margin-right:8px;vertical-align:middle;"></span>
              <span style="font-family:-apple-system,Helvetica,Arial,sans-serif;font-size:12px;color:#475569;">{_esc(sec)}</span>
              <span style="font-family:-apple-system,Helvetica,Arial,sans-serif;font-size:12px;font-weight:700;color:#0F172A;margin-left:4px;">{cnt}</span>
            </td></tr>""")

        # Banner extra
        extra_banner = ""
        if data_extra and any("Extra" in k for k in resumo):
            extra_banner = f"""
            <tr><td style="padding:16px 32px 0;">
              <table width="100%" cellpadding="0" cellspacing="0"><tr>
                <td style="background:#FEF2F2;border-left:3px solid #B91C1C;padding:10px 14px;">
                  <span style="font-family:-apple-system,Helvetica,Arial,sans-serif;font-size:11px;color:#991B1B;font-weight:600;">⚡ Inclui Edições Extras de {_esc(data_extra)}</span>
                </td>
              </tr></table>
            </td></tr>"""

        hora = datetime.now().strftime("%H:%M")

        return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<meta http-equiv="X-UA-Compatible" content="IE=edge">
<title>Boletim DOU — {_esc(data_regular)}</title>
<!--[if mso]><noscript><xml><o:OfficeDocumentSettings><o:PixelsPerInch>96</o:PixelsPerInch></o:OfficeDocumentSettings></xml></noscript><![endif]-->
<style>
  body,table,td,p {{margin:0;padding:0;}}
  img {{border:0;display:block;}}
  a {{color:#2563EB;}}
  @media only screen and (max-width:620px) {{
    .outer {{width:100%!important;}}
    td[style*="padding:32px"] {{padding:16px!important;}}
    td[style*="padding:16px 32px"] {{padding:12px 16px!important;}}
  }}
</style>
</head>
<body style="margin:0;padding:0;background:#E8ECF1;-webkit-text-size-adjust:100%;">

<!-- Preheader -->
<div style="display:none;max-height:0;overflow:hidden;font-size:1px;line-height:1px;color:#E8ECF1;">
{total} publicações — {data_ext} — Seções 1, 2 e 3
</div>

<table width="100%" cellpadding="0" cellspacing="0" style="background:#E8ECF1;">
<tr><td align="center" style="padding:20px 8px;">

<!-- ═══════════════════════════════════════════ -->
<!--           CONTAINER PRINCIPAL              -->
<!-- ═══════════════════════════════════════════ -->
<table class="outer" width="640" cellpadding="0" cellspacing="0" style="background:#FFFFFF;border-radius:0;box-shadow:0 1px 4px rgba(0,0,0,0.06);">

<!-- ▬▬▬ HEADER ▬▬▬ -->
<tr><td style="background:#0F172A;padding:24px 32px;">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr>
      <td>
        <p style="font-family:Georgia,'Times New Roman',serif;font-size:22px;font-weight:700;color:#FFFFFF;margin:0;letter-spacing:-0.3px;">BOLETIM DOU</p>
        <p style="font-family:-apple-system,Helvetica,Arial,sans-serif;font-size:10px;color:#94A3B8;margin:4px 0 0;letter-spacing:1.5px;text-transform:uppercase;">Diário Oficial da União — Seções 1, 2 e 3</p>
      </td>
      <td align="right" valign="top">
        <span style="display:inline-block;background:#1E3A5F;color:#E2E8F0;font-family:-apple-system,Helvetica,Arial,sans-serif;font-size:11px;font-weight:600;padding:4px 10px;border-radius:3px;">{total} atos</span>
      </td>
    </tr>
  </table>
</td></tr>

<!-- ▬▬▬ FAIXA DE DATA ▬▬▬ -->
<tr><td style="background:#F8FAFC;border-bottom:1px solid #E2E8F0;padding:14px 32px;">
  <p style="font-family:Georgia,'Times New Roman',serif;font-size:14px;color:#334155;margin:0;font-weight:400;">{_esc(data_ext)}</p>
  <p style="font-family:-apple-system,Helvetica,Arial,sans-serif;font-size:10px;color:#94A3B8;margin:2px 0 0;">Gerado às {hora} (Brasília)</p>
</td></tr>

<!-- ▬▬▬ SUMÁRIO ▬▬▬ -->
<tr><td style="padding:20px 32px 4px;">
  <p style="font-family:-apple-system,Helvetica,Arial,sans-serif;font-size:9px;font-weight:700;color:#94A3B8;text-transform:uppercase;letter-spacing:1.5px;margin:0 0 8px;">Nesta edição</p>
  <table cellpadding="0" cellspacing="0">
    {"".join(sumario_rows)}
  </table>
</td></tr>

{extra_banner}

<!-- ═══ PUBLICAÇÕES ═══ -->
{corpo}

<!-- ▬▬▬ FOOTER ▬▬▬ -->
<tr><td style="height:24px;"></td></tr>
<tr><td style="background:#F8FAFC;border-top:1px solid #E2E8F0;padding:20px 32px;">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr><td align="center">
      <p style="font-family:-apple-system,Helvetica,Arial,sans-serif;font-size:10px;color:#94A3B8;line-height:1.7;margin:0;">
        Fonte: <a href="https://www.in.gov.br/consulta" style="color:#64748B;text-decoration:underline;">Imprensa Nacional</a>
      </p>
      <p style="font-family:-apple-system,Helvetica,Arial,sans-serif;font-size:10px;color:#94A3B8;line-height:1.7;margin:4px 0 0;">
        Órgãos monitorados: Atos dos Poderes Executivo, Legislativo e Judiciário ·
        Presidência da República · Min. da Fazenda · Entidades de Fiscalização
      </p>
      <p style="font-family:-apple-system,Helvetica,Arial,sans-serif;font-size:9px;color:#CBD5E1;margin:12px 0 0;">
        Para cancelar, responda com DESCADASTRAR
      </p>
    </td></tr>
  </table>
</td></tr>

</table>
<!-- /CONTAINER -->

</td></tr>
</table>

</body>
</html>"""
