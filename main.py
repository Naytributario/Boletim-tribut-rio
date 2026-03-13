"""
main.py — Orquestrador do Boletim DOU

Uso:
  python main.py                  # Normal (verifica dia útil)
  python main.py --force          # Força em qualquer dia
  python main.py --preview        # Salva preview.html sem enviar
  python main.py --test EMAIL     # Envia só para um e-mail
"""
import argparse, logging, os, sys
from datetime import date

from dou_fetcher import DOUFetcher, dia_util_anterior, hoje_eh_dia_de_envio
from email_builder import EmailBuilder
from email_sender import EmailSender
from subscriber_manager import SubscriberManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("boletim_dou.log", encoding="utf-8")],
)
logger = logging.getLogger("BoletimDOU")


def executar(force=False, preview=False, test_email=""):
    logger.info("=" * 55)
    logger.info("BOLETIM DOU — Início")
    logger.info("=" * 55)

    if not force and not hoje_eh_dia_de_envio():
        logger.info("Hoje não é dia útil. Saindo.")
        return

    hoje = date.today()
    ontem_util = dia_util_anterior(hoje)

    logger.info(f"Edições regulares: {hoje.strftime('%d/%m/%Y')} (HOJE)")
    logger.info(f"Edições extras:    {ontem_util.strftime('%d/%m/%Y')} (dia útil anterior)")

    # Buscar
    fetcher = DOUFetcher()
    dados = fetcher.buscar_publicacoes_do_dia(
        data_regular=hoje,
        data_extra=ontem_util,
    )

    total = dados.get("total_publicacoes", 0)
    logger.info(f"\nTotal encontrado: {total} publicação(ões)")

    if total == 0:
        logger.info("Nenhuma publicação relevante. Boletim NÃO será enviado.")
        return

    # Gerar HTML
    builder = EmailBuilder()
    html_email = builder.build(dados)
    assunto = builder.build_subject(dados)

    if not html_email:
        logger.info("HTML vazio. Saindo.")
        return

    # Preview
    if preview:
        path = os.path.join(os.path.dirname(__file__), "preview.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(html_email)
        logger.info(f"✓ Preview salvo: {path}")
        return

    # Enviar
    sm = SubscriberManager()
    dests = [test_email] if test_email else sm.listar_ativos()
    if test_email:
        logger.info(f"Modo teste: {test_email}")
    else:
        logger.info(f"Destinatários ativos: {len(dests)}")

    if not dests:
        logger.warning("Nenhum destinatário. Use: python manage.py add EMAIL")
        return

    sender = EmailSender()
    r = sender.enviar(dests, assunto, html_email,
        texto_fallback=f"Boletim DOU — {dados['data_regular']} — {total} atos.")

    logger.info(f"\nRESULTADO: {len(r['enviados'])} ok / {len(r['falhas'])} falha(s)")
    logger.info("=" * 55)


def main():
    p = argparse.ArgumentParser(description="Boletim DOU")
    p.add_argument("--force", action="store_true")
    p.add_argument("--preview", action="store_true")
    p.add_argument("--test", metavar="EMAIL", default="")
    a = p.parse_args()
    executar(force=a.force, preview=a.preview, test_email=a.test)

if __name__ == "__main__":
    main()
