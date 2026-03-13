"""
email_sender.py — Envio via Gmail SMTP
"""
import logging, smtplib, time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional
import config

logger = logging.getLogger(__name__)

class EmailSender:
    def __init__(self):
        self.server = config.SMTP_SERVER
        self.port = config.SMTP_PORT
        self.user = config.SMTP_USER
        self.pwd = config.SMTP_PASSWORD

    def validar_credenciais(self) -> bool:
        if not self.user or not self.pwd:
            logger.error("Credenciais SMTP não configuradas (GMAIL_USER / GMAIL_APP_PASSWORD).")
            return False
        try:
            with smtplib.SMTP(self.server, self.port, timeout=15) as s:
                s.starttls()
                s.login(self.user, self.pwd)
            logger.info("✓ Credenciais SMTP válidas.")
            return True
        except smtplib.SMTPAuthenticationError:
            logger.error("Falha de autenticação. Use Senha de App (não a senha normal).")
            return False
        except Exception as e:
            logger.error(f"Erro SMTP: {e}")
            return False

    def enviar(self, destinatarios: list, assunto: str, html_body: str, texto_fallback: Optional[str] = None) -> dict:
        result = {"enviados": [], "falhas": []}
        if not destinatarios:
            return result
        if not self.validar_credenciais():
            result["falhas"] = [{"email": e, "erro": "Credenciais inválidas"} for e in destinatarios]
            return result

        for email in destinatarios:
            ok = self._enviar_um(email, assunto, html_body, texto_fallback)
            if ok:
                result["enviados"].append(email)
            else:
                result["falhas"].append({"email": email, "erro": "Falha no envio"})
            time.sleep(1)

        logger.info(f"Envio: {len(result['enviados'])} ok, {len(result['falhas'])} falha(s)")
        return result

    def _enviar_um(self, dest, assunto, html_body, texto_fallback=None, tentativas=3) -> bool:
        msg = MIMEMultipart("alternative")
        msg["From"] = f"{config.SENDER_NAME} <{config.SENDER_EMAIL}>"
        msg["To"] = dest
        msg["Subject"] = assunto
        msg["List-Unsubscribe"] = f"<mailto:{config.UNSUBSCRIBE_EMAIL}?subject=DESCADASTRAR>"
        if texto_fallback:
            msg.attach(MIMEText(texto_fallback, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        for t in range(1, tentativas + 1):
            try:
                with smtplib.SMTP(self.server, self.port, timeout=30) as s:
                    s.starttls()
                    s.login(self.user, self.pwd)
                    s.sendmail(config.SENDER_EMAIL, dest, msg.as_string())
                logger.info(f"  ✉ Enviado: {dest}")
                return True
            except smtplib.SMTPRecipientsRefused:
                logger.warning(f"  ✗ Rejeitado: {dest}")
                return False
            except Exception as e:
                logger.warning(f"  ⚠ Tentativa {t}/{tentativas} falhou para {dest}: {e}")
                if t < tentativas: time.sleep(5 * t)
        logger.error(f"  ✗ Falha definitiva: {dest}")
        return False
