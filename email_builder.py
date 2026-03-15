"""
email_builder.py — E-mail de notificação com saudação + link para o site

Visual: como se alguém tivesse digitado o e-mail e inserido o link depois.
Não é um template de newsletter corporativa — é uma mensagem pessoal
com design limpo.

Modelo EXATO (Diva):
  1. "Bom dia, [Nome]!" ou "Bom dia!" (sem nome se teste)
  2. "Seu boletim do Diário Oficial de hoje já está disponível."
  3. Banner "Inclui Edições Extras de DD/MM/YYYY" (se houver)
  4. "Hoje temos X publicações dos órgãos monitorados."
  5. Resumo por seção
  6. "É só clicar no link abaixo, e começar o dia atualizado!"
  7. Botão "Abrir boletim completo"
  8. "Que você tenha um excelente e abençoado dia."
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
        """Gera o HTML do e-mail seguindo o modelo exato."""
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

        # ── 1. Saudação ──
        hora = datetime.now().hour
        if hora < 12:
            saudacao = "Bom dia"
        elif hora < 18:
            saudacao = "Boa tarde"
        else:
            saudacao = "Boa noite"

        nome = nome_destinatario.strip().split()[0] if nome_destinatario and nome_destinatario.strip() else ""
        if nome:
            saudacao_linha = f"{saudacao}, {nome}!"
        else:
            saudacao_linha = f"{saudacao}!"

        # ── 3. Banner extra (condicional) ──
        extra_html = ""
        if data_extra and any("Extra" in k for k in dados["secoes"]):
            extra_html = f"""
              <p style="margin:12px 0;padding:10px 14px;background:#FEF2F2;border-left:3px solid #B91C1C;border-radius:0 4px 4px 0;font-size:13px;color:#991B1B;font-weight:600;">
                ⚡ Inclui Edições Extras de {_esc(data_extra)}
              </p>"""

        # ── 5. Resumo por seção ──
        resumo_lines = []
        for sec, orgaos in dados["secoes"].items():
            cnt = sum(len(p) for p in orgaos.values())
            is_ex = "Extra" in sec
            dot_c = "#B91C1C" if is_ex else "#1E3A5F"
            resumo_lines.append(
                f'<span style="display:inline-block;width:7px;height:7px;'
                f'background:{dot_c};border-radius:50%;margin-right:8px;'
                f'vertical-align:middle;"></span>'
                f'<span style="color:#475569;">{_esc(sec)}</span> '
                f'<strong style="color:#0F172A;">{cnt}</strong>'
            )
        resumo_html = "<br>".join(resumo_lines)

        page_url = config.GITHUB_PAGES_URL

        # ── ESTILO: fonte consistente, como e-mail digitado ──
        f = "font-family:Georgia,'Times New Roman',serif;"
        fs = "font-family:-apple-system,Helvetica,Arial,sans-serif;"

        return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Boletim DOU — {_esc(data_reg)}</title>
<style>body,table,td,p{{margin:0;padding:0;}}a{{color:#2563EB;}}</style>
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
  <table width="100%" cellpadding="0" cellspacing="0"><tr>
    <td>
      <p style="{f}font-size:22px;font-weight:700;color:#fff;margin:0;">BOLETIM DOU</p>
      <p style="{fs}font-size:10px;color:#94A3B8;margin:4px 0 0;letter-spacing:1.5px;text-transform:uppercase;">Seções 1, 2 e 3</p>
    </td>
    <td align="right" valign="top">
      <span style="display:inline-block;background:#1E3A5F;color:#E2E8F0;{fs}font-size:12px;font-weight:600;padding:4px 12px;border-radius:4px;">{total} atos</span>
    </td>
  </tr></table>
</td></tr>

<!-- DATA -->
<tr><td style="background:#F8FAFC;border-bottom:1px solid #E2E8F0;padding:12px 32px;">
  <p style="{f}font-size:14px;color:#334155;margin:0;">{_esc(data_ext)}</p>
</td></tr>

<!-- CORPO — como e-mail digitado -->
<tr><td style="padding:28px 32px 28px;">

  <!-- 1. Saudação -->
  <p style="{f}font-size:17px;color:#0F172A;margin:0 0 14px;font-weight:600;">{_esc(saudacao_linha)}</p>

  <!-- 2. Frase fixa -->
  <p style="{fs}font-size:14px;color:#475569;margin:0 0 6px;line-height:1.7;">Seu boletim do Diário Oficial de hoje já está disponível.</p>

  <!-- 3. Banner extra -->
  {extra_html}

  <!-- 4. Contagem -->
  <p style="{fs}font-size:14px;color:#475569;margin:12px 0 14px;line-height:1.7;">Hoje temos <strong style="color:#0F172A;">{total} publicações</strong> dos órgãos monitorados.</p>

  <!-- 5. Resumo por seção -->
  <div style="{fs}font-size:13px;line-height:2.0;margin:0 0 18px;padding:12px 16px;background:#F8FAFC;border-radius:6px;border:1px solid #E2E8F0;">
    {resumo_html}
  </div>

  <!-- 6. Chamada -->
  <p style="{fs}font-size:14px;color:#475569;margin:0 0 20px;line-height:1.7;">É só clicar no link abaixo, e começar o dia atualizado!</p>

  <!-- 7. Botão — como link inserido depois de digitar -->
  <table cellpadding="0" cellspacing="0" style="margin:0 auto;"><tr><td>
    <a href="{_esc(page_url)}" target="_blank" style="
      display:inline-block;
      background:#1E3A5F;
      color:#ffffff;
      {fs}
      font-size:14px;
      font-weight:600;
      padding:14px 36px;
      border-radius:6px;
      text-decoration:none;
      letter-spacing:0.3px;
    ">Abrir boletim completo →</a>
  </td></tr></table>

  <!-- 8. Encerramento -->
  <p style="{f}font-size:14px;color:#64748B;margin:24px 0 0;line-height:1.7;font-style:italic;">Que você tenha um excelente e abençoado dia.</p>

</td></tr>

<!-- FOOTER -->
<tr><td style="background:#F8FAFC;border-top:1px solid #E2E8F0;padding:18px 32px;">
  <p style="{fs}font-size:10px;color:#94A3B8;text-align:center;line-height:1.7;margin:0;">
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

    def build_alerta_incompleto(self, dados: dict) -> Optional[str]:
        """Gera e-mail de alerta quando o boletim ficou incompleto (Camada 4)."""
        faltantes = dados.get("secoes_faltantes", [])
        if not faltantes:
            return None

        data_reg = dados.get("data_regular", "")
        total = dados.get("total_publicacoes", 0)
        lista = "".join(f"<li>{_esc(s)}</li>" for s in faltantes)

        return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>ALERTA — Boletim incompleto</title></head>
<body style="margin:0;padding:20px;font-family:-apple-system,Helvetica,Arial,sans-serif;background:#fff;">
<div style="max-width:560px;margin:0 auto;">
  <h2 style="color:#B91C1C;margin:0 0 16px;">⚠ Boletim DOU — Resultado incompleto</h2>
  <p style="font-size:14px;color:#334155;line-height:1.7;">
    O boletim de <strong>{_esc(data_reg)}</strong> foi gerado com <strong>{total} publicações</strong>,
    mas as seguintes seções regulares não retornaram dados após todas as tentativas:
  </p>
  <ul style="font-size:14px;color:#B91C1C;margin:12px 0;line-height:1.8;">{lista}</ul>
  <p style="font-size:14px;color:#334155;line-height:1.7;">
    O boletim foi enviado com o que foi encontrado. As seções acima podem ter
    sido perdidas por instabilidade da API da Imprensa Nacional.
  </p>
  <p style="font-size:13px;color:#64748B;margin:20px 0 0;">
    Você pode reexecutar manualmente pelo GitHub Actions se necessário.
  </p>
</div>
</body></html>"""
