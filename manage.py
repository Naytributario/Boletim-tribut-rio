"""
manage.py — CLI de gestão do Boletim DOU

  python manage.py add EMAIL [NOME]
  python manage.py remove EMAIL
  python manage.py list [--all]
  python manage.py import ARQUIVO.txt
  python manage.py test-smtp
  python manage.py send-test EMAIL
  python manage.py preview
"""
import argparse, json, logging
from subscriber_manager import SubscriberManager
from email_sender import EmailSender

logging.basicConfig(level=logging.INFO, format="%(message)s")

def cmd_add(a):
    sm = SubscriberManager()
    ok, msg = sm.adicionar(a.email, " ".join(a.nome) if a.nome else "")
    print(f"{'✓' if ok else '✗'} {msg}")

def cmd_remove(a):
    sm = SubscriberManager()
    ok, msg = sm.remover(a.email)
    print(f"{'✓' if ok else '✗'} {msg}")

def cmd_list(a):
    sm = SubscriberManager()
    if a.all:
        for s in sm.listar_todos():
            icon = "●" if s.get("status")=="ativo" else "○"
            print(f"  {icon} {s['email']:<38} {s.get('nome',''):<18} {s.get('status','')}")
    else:
        ativos = sm.listar_ativos()
        if not ativos:
            print("Nenhum assinante ativo.\nUse: python manage.py add email@ex.com")
            return
        print(f"Assinantes ativos ({len(ativos)}):")
        for i, e in enumerate(ativos, 1):
            print(f"  {i}. {e}")

def cmd_import(a):
    sm = SubscriberManager()
    with open(a.arquivo, "r") as f:
        emails = [l.strip() for l in f if l.strip() and not l.startswith("#")]
    r = sm.importar_emails(emails)
    print(f"  ✓ {r['adicionados']} adicionados  ○ {r['duplicados']} duplicados  ✗ {r['invalidos']} inválidos")

def cmd_smtp(a):
    s = EmailSender()
    if s.validar_credenciais(): print("✓ SMTP OK!")
    else: print("✗ Falha. Verifique GMAIL_USER e GMAIL_APP_PASSWORD.")

def cmd_send_test(a):
    from main import executar
    executar(force=True, test_email=a.email)

def cmd_preview(a):
    from main import executar
    executar(force=True, preview=True)

def main():
    p = argparse.ArgumentParser(description="Gerenciador do Boletim DOU")
    sub = p.add_subparsers(dest="cmd")

    pa = sub.add_parser("add"); pa.add_argument("email"); pa.add_argument("nome", nargs="*"); pa.set_defaults(func=cmd_add)
    pr = sub.add_parser("remove"); pr.add_argument("email"); pr.set_defaults(func=cmd_remove)
    pl = sub.add_parser("list"); pl.add_argument("--all", action="store_true"); pl.set_defaults(func=cmd_list)
    pi = sub.add_parser("import"); pi.add_argument("arquivo"); pi.set_defaults(func=cmd_import)
    sub.add_parser("test-smtp").set_defaults(func=cmd_smtp)
    pt = sub.add_parser("send-test"); pt.add_argument("email"); pt.set_defaults(func=cmd_send_test)
    sub.add_parser("preview").set_defaults(func=cmd_preview)

    a = p.parse_args()
    if not a.cmd: p.print_help(); return
    a.func(a)

if __name__ == "__main__":
    main()
