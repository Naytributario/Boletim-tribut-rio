"""
subscriber_manager.py — Gestão de assinantes
"""
import json, logging, os, re
from datetime import datetime
from typing import Optional
import config

logger = logging.getLogger(__name__)

class SubscriberManager:
    def __init__(self, filepath: Optional[str] = None):
        self.filepath = filepath or config.SUBSCRIBERS_FILE
        if not os.path.exists(self.filepath):
            self._save({"subscribers": []})

    def _load(self):
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return {"subscribers": []}

    def _save(self, data):
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def adicionar(self, email, nome=""):
        email = email.strip().lower()
        if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
            return False, f"E-mail inválido: {email}"
        data = self._load()
        for s in data["subscribers"]:
            if s["email"] == email:
                if s["status"] == "inativo":
                    s["status"] = "ativo"
                    self._save(data)
                    return True, f"Reativado: {email}"
                return False, f"Já cadastrado: {email}"
        data["subscribers"].append({"email": email, "nome": nome.strip(), "status": "ativo", "cadastrado_em": datetime.now().isoformat()})
        self._save(data)
        return True, f"Adicionado: {email}"

    def remover(self, email):
        email = email.strip().lower()
        data = self._load()
        for s in data["subscribers"]:
            if s["email"] == email:
                s["status"] = "inativo"
                self._save(data)
                return True, f"Removido: {email}"
        return False, f"Não encontrado: {email}"

    def remover_permanente(self, email):
        email = email.strip().lower()
        data = self._load()
        n = len(data["subscribers"])
        data["subscribers"] = [s for s in data["subscribers"] if s["email"] != email]
        if len(data["subscribers"]) < n:
            self._save(data)
            return True, f"Removido permanentemente: {email}"
        return False, f"Não encontrado: {email}"

    def listar_ativos(self):
        return [s["email"] for s in self._load().get("subscribers",[]) if s.get("status")=="ativo"]

    def listar_todos(self):
        return self._load().get("subscribers", [])

    def importar_emails(self, emails, nome=""):
        r = {"adicionados": 0, "duplicados": 0, "invalidos": 0}
        for e in emails:
            ok, msg = self.adicionar(e, nome)
            if ok: r["adicionados"] += 1
            elif "cadastrado" in msg.lower(): r["duplicados"] += 1
            else: r["invalidos"] += 1
        return r
