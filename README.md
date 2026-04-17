# KM Curve Analyzer

A web application for automated Kaplan-Meier curve digitization, survival statistics, and indirect treatment comparison.

Upload a KM figure (or search PubMed directly) — an LLM extracts the curve data, the Guyot algorithm reconstructs individual patient data, and the system computes log-rank p-values and hazard ratios. A Bucher indirect comparison module estimates A vs C from two trials sharing a common comparator.

---

## Features

- **KM figure digitization** — upload an image or retrieve figures from PubMed/PMC automatically
- **Multi-group support** — figures with >2 groups show an interactive selector before analysis
- **Log-rank test + hazard ratio** — reconstructed IPD → scipy log-rank, Cox or Mantel–Haenszel HR
- **Bucher indirect comparison** — combine A vs B and B vs C to estimate A vs C
- **Multi-provider LLM** — OpenAI GPT-4o, Anthropic Claude Sonnet, Google Gemini Flash
- **PubMed search** — keyword search → article list → PMC figure auto-fetch; graceful fallback for paywalled articles

---

## Project Structure

```
bio2final/
├── backend/
│   ├── main.py                      # FastAPI app, 13 endpoints
│   └── modules/
│       ├── llm_extraction.py        # Multi-provider LLM extraction
│       ├── ipd_reconstruction.py    # Guyot algorithm
│       ├── logrank.py               # Log-rank, Cox/MH HR
│       ├── indirect_comparison.py   # Bucher method
│       └── pubmed.py                # NCBI eutils + PMC HTML scraping
├── frontend/
│   └── src/
│       ├── app/
│       │   ├── page.tsx             # Main analysis page
│       │   └── indirect/page.tsx    # Indirect comparison page
│       ├── components/
│       │   ├── KMAnalysisFlow.tsx   # Extract → select → analyze flow
│       │   ├── PubmedFigurePicker.tsx
│       │   ├── GroupSelector.tsx
│       │   ├── KMChart.tsx
│       │   ├── ResultCard.tsx
│       │   ├── DropZone.tsx
│       │   └── ApiKeyBanner.tsx
│       └── lib/
│           ├── api.ts               # Axios client
│           └── apiKey.ts            # Per-provider key storage
├── report/                          # Course technical report (LaTeX)
├── start.bat                        # One-click launcher (Windows)
└── requirements.txt
```

---

## Setup

### Prerequisites

- [Anaconda](https://www.anaconda.com/) (Python 3.11)
- [Node.js](https://nodejs.org/) 18+
- API key from at least one LLM provider (OpenAI / Anthropic / Google)

### Backend

```bash
conda create -n km-analyzer python=3.11 -y
conda activate km-analyzer
cd backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### One-click start (Windows)

Double-click **`start.bat`** — kills any existing processes on ports 8000/3000, opens both servers in separate windows, and launches the browser after 10 seconds.

---

## Usage

### Single KM Figure Analysis

1. Open `http://localhost:3000`
2. **Upload Image** tab: drag and drop a KM figure
   **Search PubMed** tab: enter a keyword → select article → select figure
3. If the figure has more than two groups, select the pair to compare
4. Results show log-rank p-value, hazard ratio with 95% CI, and reconstructed KM curves

### Indirect Comparison (Bucher Method)

1. Open the **Indirect Comparison** page
2. Set treatment labels A, B, C
3. For each of the two trial slots, search PubMed or upload the KM figure
4. Click **Run Indirect Comparison** — the system computes HR(A vs C) with p-value and CI

### API Key

Enter your LLM API key in the banner at the top of any page. Keys are stored in browser localStorage and never sent to any server other than the selected provider.

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/extract-km` | Image file → LLM extraction only |
| POST | `/api/extract-km-from-url` | Figure URL → LLM extraction only |
| POST | `/api/analyze-km` | Full pipeline from file (legacy) |
| POST | `/api/analyze-km-from-url` | Full pipeline from URL (legacy) |
| POST | `/api/analyze-from-extraction` | Log-rank from pre-computed extraction + group indices |
| POST | `/api/reconstruct-ipd` | Curve points → IPD |
| POST | `/api/logrank` | Log-rank from manual data |
| POST | `/api/indirect-comparison` | Bucher indirect comparison |
| POST | `/api/extract-hr` | Extract HR from article text via LLM |
| GET  | `/api/search-pubmed` | PubMed keyword search |
| GET  | `/api/pmc-figures` | PMC figure list for a PMID |
| GET  | `/api/proxy-image` | Proxy remote image (CORS fix) |
| GET  | `/api/debug-headers` | Diagnostic |

---

## Statistical Methods

**IPD Reconstruction** — Guyot et al. (2012) algorithm inverts the KM estimator using published curve coordinates and at-risk counts to impute event and censoring times.

**Log-rank Test** — standard two-sample log-rank statistic (scipy). Hazard ratio estimated by Cox proportional hazards model (lifelines); Mantel–Haenszel used as fallback.

**Bucher Indirect Comparison** — for trials A vs B and B vs C:

$$\ln\widehat{HR}_{AC} = \ln\widehat{HR}_{AB} - \ln\widehat{HR}_{BC}, \qquad \mathrm{SE}^2 = \mathrm{SE}^2_{AB} + \mathrm{SE}^2_{BC}$$

Two-sided z-test yields p-value and 95% CI. Assumes homogeneity of effect modifiers across trials.

---

## Dependencies

**Backend** — FastAPI, uvicorn, lifelines, scipy, numpy, pandas, httpx, openai, anthropic, google-genai, Pillow

**Frontend** — Next.js 14, TypeScript, Tailwind CSS, axios, recharts

---

## References

1. Guyot P, et al. Enhanced secondary analysis of survival data: reconstructing the data from published Kaplan-Meier survival curves. *BMC Med Res Methodol.* 2012;12:9.
2. Bucher HC, et al. The results of direct and indirect treatment comparisons in meta-analysis of randomized controlled trials. *J Clin Epidemiol.* 1997;50(6):683–691.
