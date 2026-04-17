# KM Curve Analyzer

**Live site:** https://km-curve-analyzer.vercel.app

## What it does

Automates the extraction and analysis of Kaplan-Meier survival curves from published figures.
Upload a KM figure (or retrieve one via PubMed) — the system uses a large language model to
extract time–survival coordinates, reconstructs individual patient data (IPD) via the Guyot
algorithm, and returns a log-rank p-value and hazard ratio with 95% confidence interval.

## How to use

**No API key needed — try the built-in demos:**

1. Open the site and click one of the two demo cards (CABOSUN or CheckMate 9ER)
2. Select which two groups to compare and click **Analyze**
3. Results appear instantly: KM chart, log-rank p-value, HR with 95% CI

**To analyze your own figure:**

1. Enter an LLM API key (OpenAI / Anthropic / Google) in the banner at the top
2. Upload an image directly, or search PubMed and pick a figure from an open-access article
3. Select groups → Analyze

## Additional features

- **Multi-group support** — figures with more than two treatment arms are handled automatically;
  an interactive selector lets you pick any two groups before computing statistics
- **PubMed integration** — keyword search retrieves open-access PMC figures without manual
  downloading; paywalled articles fall back to manual upload
- **Re-select groups** — after seeing results, the group selector stays open so you can
  immediately compare a different pair without re-uploading
- **Indirect treatment comparison (Bucher method)** — navigate to the *Indirect Comparison*
  page to estimate A vs C from two trials sharing a common comparator B; a pre-filled demo
  (Fruquintinib vs Regorafenib via Placebo, using published HRs from FRESCO and CORRECT) is
  included and requires no API key
- **Multi-provider LLM** — supports OpenAI GPT-4o, Anthropic Claude Sonnet, and Google
  Gemini Flash; switch providers in the API key banner

## Source code

https://github.com/Yoz234/KM-Curve-Analyzer
