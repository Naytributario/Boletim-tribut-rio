"""
dou_fetcher.py — Coleta de publicações do Diário Oficial da União

ESTRATÉGIA DUPLA para não perder nenhuma publicação:

  1ª (primária): /leiturajornal?secao=dou1&data=DD-MM-YYYY
     → retorna TODAS as publicações da seção/data num JSON embutido
     → filtra localmente pelos órgãos desejados
     → garante completude total

  2ª (fallback): /consulta/-/buscar/dou?s=do1&exactDate=DD-MM-YYYY&orgPrin=...
     → busca paginada por órgão
     → usada se a primária falhar

REGRAS DE DATA:
  • Edições regulares (Seção 1, 2, 3): data = HOJE
  • Edições extras (A, B, C...): data = DIA ÚTIL ANTERIOR
"""

import json
import logging
import re
import time
from datetime import date, timedelta
from typing import Optional

import requests
from bs4 import BeautifulSoup

import config

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
#  UTILITÁRIOS DE DATA
# ─────────────────────────────────────────────────────────────

def eh_dia_util(d: date) -> bool:
    return d.weekday() < 5 and d not in config.FERIADOS

def dia_util_anterior(d: date) -> date:
    ant = d - timedelta(days=1)
    while not eh_dia_util(ant):
        ant -= timedelta(days=1)
    return ant

def hoje_eh_dia_de_envio() -> bool:
    return eh_dia_util(date.today())


# ─────────────────────────────────────────────────────────────
#  FETCHER
# ─────────────────────────────────────────────────────────────

class DOUFetcher:
    """Coleta publicações do DOU via Imprensa Nacional."""

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8",
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    # ─── MÉTODO PRINCIPAL ─────────────────────────────────

    def buscar_publicacoes_do_dia(
        self, data_regular: date, data_extra: Optional[date] = None
    ) -> dict:
        """
        Busca todas as publicações relevantes.

        Retorna:
        {
            "data_regular": "13/03/2026",
            "data_extra": "12/03/2026" | None,
            "secoes": {
                "Seção 1": {
                    "Ministério da Fazenda": [ {pub}, {pub}, ... ],
                    ...
                },
                ...
            },
            "total_publicacoes": int,
        }
        """
        resultado = {
            "data_regular": data_regular.strftime("%d/%m/%Y"),
            "data_extra": data_extra.strftime("%d/%m/%Y") if data_extra else None,
            "secoes": {},
            "total_publicacoes": 0,
        }

        # ── 1) EDIÇÕES REGULARES (Seção 1, 2, 3 — data de HOJE) ──
        for secao_id, nome_secao in config.SECOES_REGULARES.items():
            logger.info(f"▶ {nome_secao} — {data_regular.strftime('%d/%m/%Y')}")
            orgaos = self._buscar_secao(secao_id, data_regular)
            if orgaos:
                resultado["secoes"][nome_secao] = orgaos
                n = sum(len(v) for v in orgaos.values())
                resultado["total_publicacoes"] += n
                logger.info(f"  ✓ {n} publicação(ões) relevante(s)")
            else:
                logger.info(f"  ○ Nenhuma publicação relevante")

        # ── 2) EDIÇÕES EXTRAS (data do DIA ÚTIL ANTERIOR) ──
        if data_extra:
            for base_id, base_nome in config.SECOES_REGULARES.items():
                for sufixo in config.EXTRA_SUFIXOS:
                    secao_extra_id = f"{base_id}{sufixo}"
                    nome_extra = config.nome_extra(base_nome, sufixo)
                    logger.info(
                        f"▶ {nome_extra} — {data_extra.strftime('%d/%m/%Y')} "
                        f"(verificando...)"
                    )
                    orgaos = self._buscar_secao(secao_extra_id, data_extra)
                    if orgaos:
                        resultado["secoes"][nome_extra] = orgaos
                        n = sum(len(v) for v in orgaos.values())
                        resultado["total_publicacoes"] += n
                        logger.info(f"  ✓ {n} publicação(ões) em edição extra!")
                    # Se não encontrou, silencia (é esperado que extras não existam)

        return resultado

    # ─── BUSCA POR SEÇÃO ──────────────────────────────────

    def _buscar_secao(self, secao_id: str, data: date) -> dict:
        """
        Busca TODAS as publicações de uma seção/data.

        1ª tentativa: /leiturajornal (JSON completo)
        2ª tentativa: /consulta/-/buscar/dou (busca paginada)

        Retorna: { "Nome Órgão": [lista de pubs] } (filtrado)
        """
        # Tentativa 1: /leiturajornal
        items = self._fetch_via_leiturajornal(secao_id, data)

        if items is None:
            # Tentativa 2: busca paginada por órgão
            logger.info(f"    Fallback: usando endpoint de busca...")
            return self._fetch_via_busca(secao_id, data)

        if not items:
            return {}

        # Filtrar por órgãos de interesse
        return self._filtrar_por_orgaos(items)

    # ─── ESTRATÉGIA 1: /leiturajornal ─────────────────────

    def _fetch_via_leiturajornal(
        self, secao_id: str, data: date
    ) -> Optional[list]:
        """
        Acessa /leiturajornal?secao=dou1&data=DD-MM-YYYY
        Extrai o JSON de <script id="params"> → jsonArray
        Retorna lista de items (sem filtro) ou None se falhar.
        """
        data_str = data.strftime("%d-%m-%Y")
        url = f"{config.DOU_LEITURA_URL}?secao={secao_id}&data={data_str}"

        for tentativa in range(1, config.MAX_RETRIES + 1):
            try:
                logger.debug(f"    GET {url} (tentativa {tentativa})")
                resp = self.session.get(url, timeout=config.REQUEST_TIMEOUT)
                resp.raise_for_status()

                # Extrair JSON do <script id="params">
                items = self._parse_leiturajornal(resp.text)
                if items is not None:
                    return items

                # Se não encontrou o script, pode ser seção inexistente (extra)
                # Verificar se a página tem indicação de "sem conteúdo"
                if "nenhum resultado" in resp.text.lower() or len(resp.text) < 2000:
                    return []

                logger.warning(f"    Não encontrou jsonArray na resposta")
                return None

            except requests.RequestException as e:
                logger.warning(f"    Tentativa {tentativa} falhou: {e}")
                if tentativa < config.MAX_RETRIES:
                    time.sleep(config.REQUEST_DELAY * tentativa)

        return None

    def _parse_leiturajornal(self, html: str) -> Optional[list]:
        """
        Extrai items do JSON embutido em <script id="params">.

        O campo jsonArray pode vir como:
          - string JSON escapada: "[{...}, {...}]"  → precisa json.loads()
          - lista Python já parseada: [{...}, {...}] → usar direto
        """
        soup = BeautifulSoup(html, "html.parser")

        # Estratégia 1: <script id="params">
        script = soup.find("script", {"id": "params"})
        if script and script.string:
            try:
                data = json.loads(script.string)
                json_array = data.get("jsonArray", [])

                # jsonArray pode ser string OU lista
                if isinstance(json_array, list):
                    items = json_array
                elif isinstance(json_array, str):
                    items = json.loads(json_array)
                else:
                    items = []

                if isinstance(items, list):
                    logger.debug(f"    jsonArray: {len(items)} itens totais")
                    return items
            except (json.JSONDecodeError, TypeError, ValueError) as e:
                logger.warning(f"    Erro ao parsear script#params: {e}")

        # Estratégia 2: qualquer <script type="application/json">
        for tag in soup.find_all("script", {"type": "application/json"}):
            if not tag.string:
                continue
            try:
                data = json.loads(tag.string)
                if isinstance(data, dict) and "jsonArray" in data:
                    json_array = data["jsonArray"]
                    if isinstance(json_array, list):
                        items = json_array
                    elif isinstance(json_array, str):
                        items = json.loads(json_array)
                    else:
                        continue
                    if isinstance(items, list):
                        return items
            except (json.JSONDecodeError, TypeError, ValueError):
                continue

        # Estratégia 3: regex brute-force
        match = re.search(
            r'"jsonArray"\s*:\s*"(\[.*?\])"\s*[,}]',
            html,
            re.DOTALL,
        )
        if match:
            try:
                raw = (
                    match.group(1)
                    .replace('\\"', '"')
                    .replace("\\/", "/")
                    .replace("\\n", " ")
                )
                items = json.loads(raw)
                if isinstance(items, list):
                    return items
            except json.JSONDecodeError:
                pass

        return None

    # ─── ESTRATÉGIA 2: /consulta/-/buscar/dou (FALLBACK) ──

    def _fetch_via_busca(self, secao_id: str, data: date) -> dict:
        """
        Busca paginada por órgão no endpoint de busca.
        secao_id no formato "dou1" precisa virar "do1" para a busca.
        """
        # Converter: dou1 → do1, dou2 → do2, dou1a → do1a
        busca_secao = secao_id.replace("dou", "do")
        data_str = data.strftime("%d-%m-%Y")
        orgaos_resultado = {}

        for orgao in config.ORGAOS_FILTRO:
            pubs = self._busca_paginada(busca_secao, data_str, orgao)
            if pubs:
                orgaos_resultado[orgao] = pubs

        return orgaos_resultado

    def _busca_paginada(
        self, secao: str, data_str: str, orgao: str
    ) -> list:
        """Busca paginada de todas as publicações de um órgão."""
        todas = []
        start = 0

        while True:
            try:
                params = {
                    "q": "*",
                    "s": secao,
                    "exactDate": data_str,
                    "orgPrin": orgao,
                    "delta": config.MAX_RESULTS_PER_PAGE,
                    "start": start,
                }
                resp = self.session.get(
                    config.DOU_BUSCA_URL,
                    params=params,
                    timeout=config.REQUEST_TIMEOUT,
                )
                resp.raise_for_status()

                items, total = self._parse_busca_html(resp.text)
                if not items:
                    break

                for item in items:
                    pub = self._normalizar_item(item)
                    if pub:
                        todas.append(pub)

                start += config.MAX_RESULTS_PER_PAGE
                if start >= total or len(items) < config.MAX_RESULTS_PER_PAGE:
                    break

                time.sleep(config.REQUEST_DELAY)

            except Exception as e:
                logger.warning(f"    Erro busca {orgao}: {e}")
                break

        return todas

    def _parse_busca_html(self, html: str) -> tuple:
        """Extrai items do HTML de busca. Retorna (items, total)."""
        soup = BeautifulSoup(html, "html.parser")

        for tag in soup.find_all("script", {"type": "application/json"}):
            if not tag.string:
                continue
            try:
                data = json.loads(tag.string)
                if isinstance(data, dict) and "jsonArray" in data:
                    json_array = data["jsonArray"]
                    if isinstance(json_array, list):
                        items = json_array
                    elif isinstance(json_array, str):
                        items = json.loads(json_array)
                    else:
                        continue
                    total = data.get("total", len(items))
                    return items, total
            except (json.JSONDecodeError, TypeError, ValueError):
                continue

        return [], 0

    # ─── FILTRO E NORMALIZAÇÃO ────────────────────────────

    def _filtrar_por_orgaos(self, items: list) -> dict:
        """
        Recebe lista bruta de items do JSON e filtra pelos órgãos.

        Campos relevantes do JSON:
          - artCategory: órgão principal (ex: "Ministério da Fazenda")
          - hierarchyStr: hierarquia completa
          - urlTitle: slug para montar URL
          - title: título
          - content / abstract: ementa
          - artType / pubName: tipo do ato
          - numberPage: nº da página
          - editionNumber: nº da edição
          - pubDate: data de publicação
          - hierarchyList: lista de níveis hierárquicos
        """
        orgaos_filtro_lower = {o.lower(): o for o in config.ORGAOS_FILTRO}
        resultado = {}

        for item in items:
            # O campo "artCategory" contém o órgão principal
            art_category = (item.get("artCategory") or "").strip()

            # Verificar se o órgão está na lista de filtro
            orgao_match = None
            cat_lower = art_category.lower()

            if cat_lower in orgaos_filtro_lower:
                orgao_match = orgaos_filtro_lower[cat_lower]
            else:
                # Fallback: verificar hierarchyStr
                hierarchy = (item.get("hierarchyStr") or "").strip()
                for filtro_lower, filtro_original in orgaos_filtro_lower.items():
                    if filtro_lower in hierarchy.lower():
                        orgao_match = filtro_original
                        break

            if not orgao_match:
                continue

            pub = self._normalizar_item(item)
            if pub:
                resultado.setdefault(orgao_match, []).append(pub)

        return resultado

    def _normalizar_item(self, item: dict) -> Optional[dict]:
        """Normaliza um item JSON para formato padronizado."""
        try:
            url_title = (item.get("urlTitle") or "").strip()
            if not url_title:
                return None

            url = f"{config.DOU_ARTICLE_BASE}{url_title}"

            # Montar sub-órgão a partir de hierarchyList ou hierarchyStr
            hierarchy_list = item.get("hierarchyList") or []
            sub_orgao = ""
            if isinstance(hierarchy_list, list) and len(hierarchy_list) > 1:
                sub_orgao = hierarchy_list[-1].strip()
            elif isinstance(hierarchy_list, str):
                parts = hierarchy_list.split(" > ")
                if len(parts) > 1:
                    sub_orgao = parts[-1].strip()

            # Ementa: tentar "content" primeiro, depois "abstract"
            ementa = (item.get("content") or item.get("abstract") or "").strip()

            return {
                "titulo": (item.get("title") or "Sem título").strip(),
                "ementa": ementa,
                "tipo_ato": (
                    item.get("artType")
                    or item.get("pubName")
                    or ""
                ).strip(),
                "orgao": (item.get("artCategory") or "").strip(),
                "sub_orgao": sub_orgao,
                "url": url,
                "pagina": str(item.get("numberPage") or ""),
                "edicao": str(item.get("editionNumber") or ""),
                "data_pub": (item.get("pubDate") or "").strip(),
            }
        except Exception as e:
            logger.warning(f"    Erro normalização: {e}")
            return None
