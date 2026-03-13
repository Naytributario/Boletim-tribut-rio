"""
email_builder.py — E-mail de notificação com saudação + link para o site

O conteúdo completo vive na página web (GitHub Pages).
O e-mail é um convite elegante com:
  - Saudação personalizada (Bom dia + nome)
  - Resumo das seções
  - Botão para abrir o boletim no navegador
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


def _esc(t):
    return html_mod.escape(t) if t else ""


class EmailBuilder:

    def build(self, dados: dict, nome_destinatario: str = "") -> Optional[str]:
        """Gera o HTML do e-mail. Recebe nome do destinatário para saudação."""
        if not dados.get("secoes") or dados.get("total_publicacoes", 0) == 0:
            return None

        data_reg = dados["data_regular"]
        data_extra = dados.get("data_extra")
        total = dados["total_publicacoes"]

        try:
            dt = datetime.strptime(data_reg, "%d/%m/%Y")
            data_ext = f"{DIAS[dt.weekday()]}, {dt.day} de {MESES[dt.month - 1]} de {dt.year}"
        except Exception:
            data_ext = data_reg

        # Saudação
        hora = datetime.now().hour
        if hora < 12:
            saudacao = "Bom dia"
        elif hora < 18:
            saudacao = "Boa tarde"
        else:
            saudacao = "Boa noite"

        nome = nome_destinatario.split()[0] if nome_destinatario else ""
        saudacao_completa = f"{saudacao}, {nome}!" if nome else f"{saudacao}!"

        # Resumo por seção
        resumo_rows = []
        for sec, orgaos in dados["secoes"].items():
            cnt = sum(len(p) for p in orgaos.values())
            is_ex = "Extra" in sec
            dot_c = "#B91C1C" if is_ex else "#1E3A5F"
            resumo_rows.append(f"""
            <tr><td style="padding:4px 0;">
              <span style="display:inline-block;width:7px;height:7px;background:{dot_c};border-radius:50%;margin-right:10px;vertical-align:middle;"></span>
              <span style="font-family:-apple-system,Helvetica,Arial,sans-serif;font-size:13px;color:#475569;">{_esc(sec)}</span>
              <span style="font-family:-apple-system,Helvetica,Arial,sans-serif;font-size:13px;font-weight:700;color:#0F172A;margin-left:6px;">{cnt}</span>
            </td></tr>""")

        # Banner extra
        extra_html = ""
        if data_extra and any("Extra" in k for k in dados["secoes"]):
            extra_html = f"""
            <tr><td style="padding:0 0 16px;">
              <div style="background:#FEF2F2;border-left:3px solid #B91C1C;padding:10px 14px;border-radius:0 4px 4px 0;">
                <span style="font-size:12px;color:#991B1B;font-weight:600;">⚡ Inclui Edições Extras de {_esc(data_extra)}</span>
              </div>
            </td></tr>"""

        # URL do boletim
        page_url = config.GITHUB_PAGES_URL

        return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Boletim DOU — {_esc(data_reg)}</title>
<style>
  body,table,td,p {{margin:0;padding:0;}}
  a {{color:#2563EB;}}
</style>
</head>
<body style="margin:0;padding:0;background:#E8ECF1;">

<div style="display:none;max-height:0;overflow:hidden;font-size:1px;color:#E8ECF1;">
{total} publicações — {data_ext}
</div>

<table width="100%" cellpadding="0" cellspacing="0" style="background:#E8ECF1;">
<tr><td align="center" style="padding:24px 8px;">

<table width="580" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,0.06);">

<!-- HEADER -->
<tr><td style="background:#0F172A;padding:24px 32px;">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr>
      <td>
        <p style="font-family:Georgia,serif;font-size:22px;font-weight:700;color:#fff;margin:0;">BOLETIM DOU</p>
        <p style="font-family:-apple-system,Helvetica,Arial,sans-serif;font-size:10px;color:#94A3B8;margin:4px 0 0;letter-spacing:1.5px;text-transform:uppercase;">Seções 1, 2 e 3</p>
      </td>
      <td align="right" valign="top">
        <span style="display:inline-block;background:#1E3A5F;color:#E2E8F0;font-family:-apple-system,Helvetica,Arial,sans-serif;font-size:12px;font-weight:600;padding:4px 12px;border-radius:4px;">{total} atos</span>
      </td>
    </tr>
  </table>
</td></tr>

<!-- DATA -->
<tr><td style="background:#F8FAFC;border-bottom:1px solid #E2E8F0;padding:12px 32px;">
  <p style="font-family:Georgia,serif;font-size:14px;color:#334155;margin:0;">{_esc(data_ext)}</p>
</td></tr>

<!-- SAUDAÇÃO -->
<tr><td style="padding:28px 32px 8px;">
  <p style="font-family:Georgia,serif;font-size:18px;color:#0F172A;margin:0;font-weight:600;">{_esc(saudacao_completa)}</p>
  <p style="font-family:-apple-system,Helvetica,Arial,sans-serif;font-size:13px;color:#64748B;margin:10px 0 0;line-height:1.6;">
    Seu boletim do Diário Oficial da União está pronto. Hoje temos <strong style="color:#0F172A;">{total} publicações</strong> dos órgãos monitorados.
  </p>
</td></tr>

<!-- RESUMO -->
<tr><td style="padding:16px 32px;">
  <p style="font-family:-apple-system,Helvetica,Arial,sans-serif;font-size:10px;font-weight:700;color:#94A3B8;text-transform:uppercase;letter-spacing:1.5px;margin:0 0 8px;">Nesta edição</p>
  <table cellpadding="0" cellspacing="0">
    {"".join(resumo_rows)}
  </table>
</td></tr>

{extra_html}

<!-- BOTÃO -->
<tr><td style="padding:8px 32px 28px;" align="center">
  <table cellpadding="0" cellspacing="0"><tr><td>
    <a href="{_esc(page_url)}" target="_blank" style="
      display:inline-block;
      background:#1E3A5F;
      color:#ffffff;
      font-family:-apple-system,Helvetica,Arial,sans-serif;
      font-size:14px;
      font-weight:600;
      padding:14px 36px;
      border-radius:6px;
      text-decoration:none;
      letter-spacing:0.3px;
    ">Abrir boletim completo →</a>
  </td></tr></table>
  <p style="font-family:-apple-system,Helvetica,Arial,sans-serif;font-size:11px;color:#94A3B8;margin:10px 0 0;">
    Abre no navegador com busca e seções interativas
  </p>
</td></tr>

<!-- FOOTER -->
<tr><td style="background:#F8FAFC;border-top:1px solid #E2E8F0;padding:18px 32px;">
  <p style="font-family:-apple-system,Helvetica,Arial,sans-serif;font-size:10px;color:#94A3B8;text-align:center;line-height:1.7;margin:0;">
    Fonte: <a href="https://www.in.gov.br/consulta" style="color:#64748B;">Imprensa Nacional</a><br>
    <span style="font-size:9px;color:#CBD5E1;">Para cancelar, responda com DESCADASTRAR</span>
  </p>
</td></tr>

</table>
</td></tr>
</table>

</body>
</html>"""

    def build_subject(self, dados: dict) -> str:
        d = dados.get("data_regular", "")
        t = dados.get("total_publicacoes", 0)
        ex = " + Ed. Extra" if any("Extra" in k for k in dados.get("secoes", {})) else ""
        return f"Boletim DOU Tributário — {d}{ex} — {t} ato(s)"
