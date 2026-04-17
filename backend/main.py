"""
FastAPI backend for KM curve extraction and survival analysis.
"""

import io
import os
import logging
import traceback
import time
from typing import Optional, List

import httpx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from modules.llm_extraction import (
    extract_km_from_image,
    extract_hr_from_text,
    extraction_to_ipd_inputs,
)
from modules.ipd_reconstruction import reconstruct_ipd, validate_curve_points
from modules.logrank import compute_logrank, fit_km
from modules.indirect_comparison import bucher_indirect_comparison
from modules.pubmed import search_pubmed, get_pmc_figures

app = FastAPI(
    title="KM Curve Analyzer",
    description="Extract KM data via LLM, reconstruct IPD, compute log-rank tests.",
    version="1.0.0",
)

_cors_origins = [
    "http://localhost:3000",
    "http://localhost:3001",
]
# Allow any additional frontend URL set via environment variable, e.g. the Vercel URL
_extra_origin = os.environ.get("FRONTEND_URL", "").strip().rstrip("/")
if _extra_origin:
    _cors_origins.append(_extra_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class CurvePoint(BaseModel):
    time: float
    survival: float

class AtRiskEntry(BaseModel):
    time: float
    n_at_risk: int

class GroupData(BaseModel):
    name: str
    curve_points: List[CurvePoint]
    at_risk_table: Optional[List[AtRiskEntry]] = None
    n_total: Optional[int] = None

class TwoGroupAnalysisRequest(BaseModel):
    group_a: GroupData
    group_b: GroupData

class AnalyzeFromExtractionRequest(BaseModel):
    extraction: dict
    group_a_index: int = 0
    group_b_index: int = 1

class IndirectComparisonRequest(BaseModel):
    hr_ab: float = Field(..., description="HR(A vs B)")
    ci_lower_ab: float
    ci_upper_ab: float
    hr_bc: float = Field(..., description="HR(B vs C)")
    ci_lower_bc: float
    ci_upper_bc: float
    label_a: str = "A"
    label_b: str = "B"
    label_c: str = "C"


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/debug-headers")
async def debug_headers(
    x_api_key: Optional[str] = Header(default=None),
    x_provider: Optional[str] = Header(default=None),
):
    """Diagnostic: echo back what headers the backend actually received."""
    return {
        "x_provider": x_provider,
        "x_api_key_received": bool(x_api_key),
        "x_api_key_prefix": (x_api_key[:12] + "...") if x_api_key else None,
    }


# ---------------------------------------------------------------------------
# Endpoint 1: Extract KM data from uploaded image
# ---------------------------------------------------------------------------

@app.post("/api/extract-km")
async def extract_km(
    file: UploadFile = File(..., description="KM curve image (PNG/JPEG/PDF page)"),
    x_api_key: Optional[str] = Header(default=None),
    x_provider: Optional[str] = Header(default="openai"),
):
    """
    Upload a KM curve image → LLM extracts curve data.
    Returns raw extraction + validation warnings.
    """
    content_type = file.content_type or "image/png"
    if "pdf" in content_type.lower():
        raise HTTPException(
            status_code=400,
            detail="PDF not supported directly. Please upload a PNG/JPEG image of the figure.",
        )

    image_bytes = await file.read()
    if len(image_bytes) > 20 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image too large (max 20 MB).")

    try:
        extraction = extract_km_from_image(
            image_bytes, media_type=content_type,
            provider=x_provider or "openai", api_key=x_api_key,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM extraction failed: {e}")

    # Validate each group's curve
    warnings = {}
    for group in extraction.get("groups", []):
        pts = [(p["time"], p["survival"]) for p in group.get("curve_points", [])]
        w = validate_curve_points(pts)
        if w:
            warnings[group.get("name", "?")] = w

    return {"extraction": extraction, "warnings": warnings}


# ---------------------------------------------------------------------------
# Endpoint 2: Reconstruct IPD from curve data
# ---------------------------------------------------------------------------

@app.post("/api/reconstruct-ipd")
def reconstruct_ipd_endpoint(group: GroupData):
    """
    Given curve points + at-risk table, return reconstructed IPD as JSON.
    """
    pts = [(p.time, p.survival) for p in group.curve_points]
    risk = (
        [(r.time, r.n_at_risk) for r in group.at_risk_table]
        if group.at_risk_table
        else None
    )

    try:
        df = reconstruct_ipd(
            curve_points=pts,
            at_risk_table=risk,
            n_total=group.n_total,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "name": group.name,
        "n_reconstructed": len(df),
        "n_events": int(df["event"].sum()),
        "ipd": df.to_dict(orient="records"),
    }


# ---------------------------------------------------------------------------
# Endpoint 3: Full pipeline — upload image → IPD → log-rank
# ---------------------------------------------------------------------------

@app.post("/api/analyze-km")
async def analyze_km(
    file: UploadFile = File(...),
    group_a_name: str = Form(default=""),
    group_b_name: str = Form(default=""),
    x_api_key: Optional[str] = Header(default=None),
    x_provider: Optional[str] = Header(default="openai"),
):
    """
    Full pipeline:
      1. Extract KM curves from image via LLM  ← LLM used here
      2. Reconstruct IPD for each group
      3. Compute log-rank test between first two groups
    """
    content_type = file.content_type or "image/png"
    image_bytes = await file.read()

    logging.info("analyze_km start | provider=%s | file=%s | size=%d bytes",
                 x_provider, file.filename, len(image_bytes))

    # Step 1: Extract via LLM Vision API
    t0 = time.time()
    logging.info("Step 1: calling LLM extraction...")
    try:
        extraction = extract_km_from_image(
            image_bytes, media_type=content_type,
            provider=x_provider or "openai", api_key=x_api_key,
        )
        logging.info("Step 1 done in %.1fs | groups=%d", time.time() - t0,
                     len(extraction.get("groups", [])))
    except Exception as e:
        logging.error("Step 1 FAILED after %.1fs\n%s", time.time() - t0, traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Extraction failed: {e}")

    groups_input = extraction_to_ipd_inputs(extraction)
    if len(groups_input) < 2:
        raise HTTPException(
            status_code=422,
            detail="Need at least 2 groups in the KM figure.",
        )

    # Override names if provided
    if group_a_name:
        groups_input[0]["name"] = group_a_name
    if group_b_name:
        groups_input[1]["name"] = group_b_name

    # Step 2: Reconstruct IPD
    logging.info("Step 2: reconstructing IPD...")
    ipd_list = []
    for g in groups_input[:2]:
        try:
            df = reconstruct_ipd(
                curve_points=g["curve_points"],
                at_risk_table=g["at_risk_table"],
                n_total=g["n_total"],
            )
            ipd_list.append((g["name"], df))
            logging.info("  IPD for '%s': n=%d events=%d", g["name"], len(df), int(df["event"].sum()))
        except Exception as e:
            logging.error("Step 2 FAILED for '%s'\n%s", g["name"], traceback.format_exc())
            raise HTTPException(
                status_code=500,
                detail=f"IPD reconstruction failed for {g['name']}: {e}",
            )

    name_a, ipd_a = ipd_list[0]
    name_b, ipd_b = ipd_list[1]

    # Step 3: Log-rank
    logging.info("Step 3: computing log-rank...")
    try:
        result = compute_logrank(ipd_a, ipd_b, name_a, name_b)
        logging.info("Step 3 done | p=%.4f", result.get("p_value", -1))
    except Exception as e:
        logging.error("Step 3 FAILED\n%s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Log-rank failed: {e}")

    return {
        "extraction": extraction,
        "groups": [
            {
                "name": name_a,
                "n": len(ipd_a),
                "n_events": int(ipd_a["event"].sum()),
            },
            {
                "name": name_b,
                "n": len(ipd_b),
                "n_events": int(ipd_b["event"].sum()),
            },
        ],
        "logrank": result,
    }


# ---------------------------------------------------------------------------
# Shared helper: run full KM pipeline from raw bytes
# ---------------------------------------------------------------------------

def _run_km_pipeline(
    image_bytes: bytes,
    content_type: str,
    group_a_name: str,
    group_b_name: str,
    provider: str,
    api_key: Optional[str],
) -> dict:
    """Extract KM → IPD → log-rank. Raises HTTPException on failure."""
    t0 = time.time()
    logging.info("KM pipeline start | provider=%s | size=%d", provider, len(image_bytes))

    try:
        extraction = extract_km_from_image(
            image_bytes, media_type=content_type,
            provider=provider, api_key=api_key,
        )
        logging.info("Extraction done in %.1fs | groups=%d", time.time() - t0,
                     len(extraction.get("groups", [])))
    except Exception as e:
        logging.error("Extraction FAILED\n%s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Extraction failed: {e}")

    groups_input = extraction_to_ipd_inputs(extraction)
    if len(groups_input) < 2:
        raise HTTPException(status_code=422, detail="Need at least 2 groups in the KM figure.")

    if group_a_name:
        groups_input[0]["name"] = group_a_name
    if group_b_name:
        groups_input[1]["name"] = group_b_name

    ipd_list = []
    for g in groups_input[:2]:
        try:
            df = reconstruct_ipd(
                curve_points=g["curve_points"],
                at_risk_table=g["at_risk_table"],
                n_total=g["n_total"],
            )
            ipd_list.append((g["name"], df))
        except Exception as e:
            raise HTTPException(status_code=500,
                                detail=f"IPD reconstruction failed for {g['name']}: {e}")

    name_a, ipd_a = ipd_list[0]
    name_b, ipd_b = ipd_list[1]

    try:
        result = compute_logrank(ipd_a, ipd_b, name_a, name_b)
        logging.info("Log-rank done | p=%.4f", result.get("p_value", -1))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Log-rank failed: {e}")

    return {
        "extraction": extraction,
        "groups": [
            {"name": name_a, "n": len(ipd_a), "n_events": int(ipd_a["event"].sum())},
            {"name": name_b, "n": len(ipd_b), "n_events": int(ipd_b["event"].sum())},
        ],
        "logrank": result,
    }


# ---------------------------------------------------------------------------
# Endpoint 4: Log-rank from manually provided data
# ---------------------------------------------------------------------------

@app.post("/api/logrank")
def logrank_from_data(req: TwoGroupAnalysisRequest):
    """
    Compute log-rank test from manually supplied curve + at-risk data.
    """
    import pandas as pd

    def build_ipd(group: GroupData):
        pts = [(p.time, p.survival) for p in group.curve_points]
        risk = (
            [(r.time, r.n_at_risk) for r in group.at_risk_table]
            if group.at_risk_table
            else None
        )
        return reconstruct_ipd(curve_points=pts, at_risk_table=risk, n_total=group.n_total)

    try:
        ipd_a = build_ipd(req.group_a)
        ipd_b = build_ipd(req.group_b)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    result = compute_logrank(ipd_a, ipd_b, req.group_a.name, req.group_b.name)
    return result


# ---------------------------------------------------------------------------
# Endpoint 5: Extract HR from article text
# ---------------------------------------------------------------------------

@app.post("/api/extract-hr")
async def extract_hr(
    text: str = Form(..., description="Article text (abstract / results section)"),
    x_api_key: Optional[str] = Header(default=None),
    x_provider: Optional[str] = Header(default="openai"),
):
    """Extract HR values from pasted article text via LLM."""
    try:
        result = extract_hr_from_text(text, provider=x_provider or "openai", api_key=x_api_key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"HR extraction failed: {e}")
    return result


# ---------------------------------------------------------------------------
# Endpoint 6: Indirect comparison (Bucher method)
# ---------------------------------------------------------------------------

@app.post("/api/indirect-comparison")
def indirect_comparison(req: IndirectComparisonRequest):
    """
    Bucher indirect comparison: A vs C via common comparator B.
    Provide HR + 95% CI for A vs B and B vs C.
    """
    try:
        result = bucher_indirect_comparison(
            hr_ab=req.hr_ab,
            ci_lower_ab=req.ci_lower_ab,
            ci_upper_ab=req.ci_upper_ab,
            hr_bc=req.hr_bc,
            ci_lower_bc=req.ci_lower_bc,
            ci_upper_bc=req.ci_upper_bc,
            label_a=req.label_a,
            label_b=req.label_b,
            label_c=req.label_c,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result


# ---------------------------------------------------------------------------
# Endpoint 7: PubMed search
# ---------------------------------------------------------------------------

@app.get("/api/search-pubmed")
def search_pubmed_endpoint(
    q: str,
    max_results: int = 8,
    ncbi_api_key: Optional[str] = None,
):
    """
    Search PubMed by keyword. Returns title, year, authors, journal, abstract.
    max_results: 1-20.
    ncbi_api_key: optional NCBI API key for higher rate limits.
    """
    max_results = max(1, min(max_results, 20))
    try:
        results = search_pubmed(q, max_results, ncbi_api_key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PubMed search failed: {e}")
    return {"query": q, "count": len(results), "results": results}


# ---------------------------------------------------------------------------
# Endpoint 8: Proxy image from URL (avoids browser CORS on PMC images)
# ---------------------------------------------------------------------------

@app.get("/api/proxy-image")
async def proxy_image(url: str):
    """
    Download an image from a remote URL and return it directly.
    Tries .jpg then .png if the first returns a non-image content-type.
    """
    from fastapi.responses import Response

    headers = {"User-Agent": "Mozilla/5.0 (compatible; KMAnalyzer/1.0)"}
    logging.info("proxy-image | trying: %s", url)

    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        r = await client.get(url, headers=headers)
        ct = r.headers.get("content-type", "")
        logging.info("proxy-image | status=%d ct=%s url=%s", r.status_code, ct, r.url)

        if r.status_code != 200 or not ct.startswith("image/"):
            # Try swapping jpg <-> png
            if url.lower().endswith(".jpg"):
                alt = url[:-4] + ".png"
            elif url.lower().endswith(".png"):
                alt = url[:-4] + ".jpg"
            else:
                alt = url + ".jpg"
            logging.info("proxy-image | retrying alt: %s", alt)
            r2 = await client.get(alt, headers=headers)
            ct2 = r2.headers.get("content-type", "")
            logging.info("proxy-image | alt status=%d ct=%s", r2.status_code, ct2)
            if r2.status_code == 200 and ct2.startswith("image/"):
                r = r2
                ct = ct2

        if not ct.startswith("image/"):
            logging.warning("proxy-image | FAILED body preview: %s", r.text[:200])
            raise HTTPException(status_code=404, detail=f"Image not found. NCBI returned: {ct}")

    return Response(content=r.content, media_type=ct)


# ---------------------------------------------------------------------------
# Endpoint 10: Get PMC figures for a PMID
# ---------------------------------------------------------------------------

@app.get("/api/pmc-figures")
def pmc_figures_endpoint(pmid: str, ncbi_api_key: Optional[str] = None):
    """
    Given a PubMed ID, return the list of figures from its PMC open-access article.
    Returns {"pmcid": "PMCxxxxxx", "figures": [{fig_id, label, caption, url}]}
    or {"pmcid": null, "figures": []} if not in PMC.
    """
    try:
        result = get_pmc_figures(pmid, ncbi_api_key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PMC lookup failed: {e}")
    return result


# ---------------------------------------------------------------------------
# Endpoint 11: Full KM pipeline from a figure URL (PMC image)
# ---------------------------------------------------------------------------

@app.post("/api/analyze-km-from-url")
async def analyze_km_from_url(
    figure_url: str = Form(...),
    group_a_name: str = Form(default=""),
    group_b_name: str = Form(default=""),
    x_api_key: Optional[str] = Header(default=None),
    x_provider: Optional[str] = Header(default="openai"),
):
    """
    Download a figure from a URL (e.g. PMC image) then run the full KM pipeline.
    """
    logging.info("analyze_km_from_url | url=%s", figure_url)
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(figure_url)
            r.raise_for_status()
            image_bytes = r.content
            content_type = r.headers.get("content-type", "image/jpeg").split(";")[0]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to download figure: {e}")

    return _run_km_pipeline(
        image_bytes, content_type, group_a_name, group_b_name,
        x_provider or "openai", x_api_key,
    )


# ---------------------------------------------------------------------------
# Endpoint 12: Extract KM from a figure URL (no stats)
# ---------------------------------------------------------------------------

@app.post("/api/extract-km-from-url")
async def extract_km_from_url_endpoint(
    figure_url: str = Form(...),
    x_api_key: Optional[str] = Header(default=None),
    x_provider: Optional[str] = Header(default="openai"),
):
    """Download a figure from URL and run LLM extraction only (no IPD/log-rank)."""
    logging.info("extract-km-from-url | url=%s", figure_url)
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(figure_url, headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            image_bytes = r.content
            content_type = r.headers.get("content-type", "image/jpeg").split(";")[0]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to download figure: {e}")

    try:
        extraction = extract_km_from_image(
            image_bytes, media_type=content_type,
            provider=x_provider or "openai", api_key=x_api_key,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {e}")

    warnings = {}
    for group in extraction.get("groups", []):
        pts = [(p["time"], p["survival"]) for p in group.get("curve_points", [])]
        w = validate_curve_points(pts)
        if w:
            warnings[group.get("name", "?")] = w

    return {"extraction": extraction, "warnings": warnings}


# ---------------------------------------------------------------------------
# Endpoint 13: Run IPD + log-rank on a pre-computed extraction, by group index
# ---------------------------------------------------------------------------

@app.post("/api/analyze-from-extraction")
def analyze_from_extraction(req: AnalyzeFromExtractionRequest):
    """
    Given a KM extraction dict (from extract-km or extract-km-from-url) and
    two group indices, reconstruct IPD and compute log-rank.
    Allows selecting any two groups when the figure has > 2 groups.
    """
    groups_input = extraction_to_ipd_inputs(req.extraction)
    n = len(groups_input)
    if n < 2:
        raise HTTPException(status_code=422, detail="Need at least 2 groups.")
    if req.group_a_index >= n or req.group_b_index >= n:
        raise HTTPException(status_code=400,
                            detail=f"Group index out of range (0–{n-1}).")
    if req.group_a_index == req.group_b_index:
        raise HTTPException(status_code=400, detail="group_a_index and group_b_index must differ.")

    g_a = groups_input[req.group_a_index]
    g_b = groups_input[req.group_b_index]

    try:
        ipd_a = reconstruct_ipd(
            curve_points=g_a["curve_points"],
            at_risk_table=g_a["at_risk_table"],
            n_total=g_a["n_total"],
        )
        ipd_b = reconstruct_ipd(
            curve_points=g_b["curve_points"],
            at_risk_table=g_b["at_risk_table"],
            n_total=g_b["n_total"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"IPD reconstruction failed: {e}")

    try:
        result = compute_logrank(ipd_a, ipd_b, g_a["name"], g_b["name"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Log-rank failed: {e}")

    return {
        "extraction": req.extraction,
        "groups": [
            {"name": g_a["name"], "n": len(ipd_a), "n_events": int(ipd_a["event"].sum())},
            {"name": g_b["name"], "n": len(ipd_b), "n_events": int(ipd_b["event"].sum())},
        ],
        "logrank": result,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
