"""
PubMed search via NCBI eutils (esearch + efetch).
No API key required; optional key increases rate limit from 3 to 10 req/s.
"""

import xml.etree.ElementTree as ET
from typing import List, Dict, Optional

import httpx

ESEARCH_URL  = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL   = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
ELINK_URL    = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi"
PMC_IMG_BASE = "https://www.ncbi.nlm.nih.gov/pmc/articles"


def search_pubmed(
    query: str,
    max_results: int = 8,
    ncbi_api_key: Optional[str] = None,
) -> List[Dict]:
    """
    Search PubMed and return article summaries with abstracts.

    Returns list of dicts with keys:
      pmid, title, year, authors, journal, abstract
    """
    params: Dict = {
        "db": "pubmed",
        "term": query,
        "retmax": max_results,
        "retmode": "json",
        "sort": "relevance",
    }
    if ncbi_api_key:
        params["api_key"] = ncbi_api_key

    with httpx.Client(timeout=15) as client:
        r = client.get(ESEARCH_URL, params=params)
        r.raise_for_status()
        pmids = r.json().get("esearchresult", {}).get("idlist", [])

        if not pmids:
            return []

        fetch_params: Dict = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "rettype": "abstract",
            "retmode": "xml",
        }
        if ncbi_api_key:
            fetch_params["api_key"] = ncbi_api_key

        r2 = client.get(EFETCH_URL, params=fetch_params)
        r2.raise_for_status()

    return _parse_pubmed_xml(r2.text)


def _parse_pubmed_xml(xml_text: str) -> List[Dict]:
    root = ET.fromstring(xml_text)
    articles = []

    for pub_article in root.findall(".//PubmedArticle"):
        pmid_el = pub_article.find(".//PMID")
        pmid = pmid_el.text if pmid_el is not None else ""

        title_el = pub_article.find(".//ArticleTitle")
        title = "".join(title_el.itertext()) if title_el is not None else ""

        # Year: try multiple locations
        year = (
            pub_article.findtext(".//PubDate/Year")
            or pub_article.findtext(".//PubDate/MedlineDate", "")[:4]
        )

        # Up to 3 authors
        authors = []
        for author in pub_article.findall(".//Author")[:3]:
            last = author.findtext("LastName", "")
            initials = author.findtext("Initials", "")
            if last:
                authors.append(f"{last} {initials}".strip())
        if len(pub_article.findall(".//Author")) > 3:
            authors.append("et al.")

        journal = pub_article.findtext(".//Journal/Title") or \
                  pub_article.findtext(".//MedlineJournalInfo/MedlineTA") or ""

        abstract_parts = pub_article.findall(".//AbstractText")
        abstract = " ".join("".join(a.itertext()) for a in abstract_parts).strip()

        articles.append({
            "pmid": pmid,
            "title": title,
            "year": year,
            "authors": authors,
            "journal": journal,
            "abstract": abstract,
        })

    return articles


def get_pmc_figures(pmid: str, ncbi_api_key: Optional[str] = None) -> Dict:
    """
    For a given PubMed ID, check if the article is in PMC open access,
    then return its figure list by scraping the PMC article HTML page.

    Returns:
        {"pmcid": "PMC1234567", "figures": [{fig_id, label, caption, url}]}
        {"pmcid": None, "figures": []}  if not in PMC
    """
    headers = {"User-Agent": "Mozilla/5.0 (compatible; KMAnalyzer/1.0)"}

    with httpx.Client(timeout=20, follow_redirects=True) as client:
        # Step 1: PMID -> PMCID via elink
        elink_params: Dict = {
            "dbfrom": "pubmed", "db": "pmc",
            "id": pmid, "retmode": "json",
        }
        if ncbi_api_key:
            elink_params["api_key"] = ncbi_api_key

        r = client.get(ELINK_URL, params=elink_params, headers=headers)
        r.raise_for_status()
        data = r.json()

        pmcids = []
        for linkset in data.get("linksets", []):
            for lsdb in linkset.get("linksetdbs", []):
                if lsdb.get("dbto") == "pmc":
                    pmcids.extend(lsdb.get("links", []))

        if not pmcids:
            return {"pmcid": None, "figures": []}

        pmcid_str = f"PMC{pmcids[0]}"

        # Step 2: fetch PMC article HTML page and extract real image URLs
        article_url = f"{PMC_IMG_BASE}/{pmcid_str}/"
        r2 = client.get(article_url, headers=headers)
        r2.raise_for_status()

    figures = _parse_pmc_html_figures(r2.text, pmcid_str)
    return {"pmcid": pmcid_str, "figures": figures}


def _parse_pmc_html_figures(html_text: str, pmcid: str) -> List[Dict]:
    """
    Parse PMC article HTML and extract figure list with actual image URLs.
    PMC HTML wraps each figure in <div class="fig"> or <figure> elements.
    """
    from html.parser import HTMLParser

    class FigureParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.figures: List[Dict] = []
            self._in_fig = 0          # nesting depth inside a figure block
            self._fig_tag = ""        # "div" or "figure"
            self._current: Dict = {}
            self._capture_label = False
            self._capture_caption = False
            self._caption_depth = 0
            self._text_buf: List[str] = []

        def _is_fig_start(self, tag, attrs):
            d = dict(attrs)
            cls = d.get("class", "")
            return (tag == "figure") or (tag == "div" and "fig" in cls.split())

        def handle_starttag(self, tag, attrs):
            d = dict(attrs)
            if self._in_fig == 0 and self._is_fig_start(tag, attrs):
                self._in_fig = 1
                self._fig_tag = tag
                self._current = {
                    "fig_id": d.get("id", f"fig{len(self.figures)+1}"),
                    "label": "", "caption": "", "url": "",
                    "pmcid": pmcid,
                }
                return

            if self._in_fig > 0:
                self._in_fig += 1

                # Label element
                if tag in ("div", "span", "p") and "fig-label" in d.get("class", ""):
                    self._capture_label = True
                    self._text_buf = []

                # Caption element
                if tag in ("div", "p") and (
                    "fig-caption" in d.get("class", "") or
                    "caption" in d.get("class", "")
                ):
                    self._capture_caption = True
                    self._caption_depth = self._in_fig
                    self._text_buf = []

                # Image element — grab the largest/best src
                if tag == "img" and not self._current.get("url"):
                    src = d.get("src", "")
                    if src and not src.endswith(".gif") and "icon" not in src.lower():
                        if src.startswith("//"):
                            src = "https:" + src
                        elif src.startswith("/"):
                            src = "https://www.ncbi.nlm.nih.gov" + src
                        self._current["url"] = src

        def handle_endtag(self, tag):
            if self._in_fig == 0:
                return

            if self._capture_label and tag in ("div", "span", "p"):
                self._current["label"] = " ".join(self._text_buf).strip()
                self._capture_label = False
                self._text_buf = []

            if self._capture_caption and self._in_fig == self._caption_depth:
                self._current["caption"] = " ".join(self._text_buf).strip()[:400]
                self._capture_caption = False
                self._text_buf = []

            self._in_fig -= 1
            if self._in_fig == 0:
                if self._current.get("url"):
                    self.figures.append(self._current)
                self._current = {}

        def handle_data(self, data):
            if self._capture_label or self._capture_caption:
                t = data.strip()
                if t:
                    self._text_buf.append(t)

    parser = FigureParser()
    parser.feed(html_text)
    return parser.figures
