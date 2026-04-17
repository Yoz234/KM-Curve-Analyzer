/**
 * Pre-stored KM extractions for demo mode.
 * These are realistic approximations based on published trial data.
 * No LLM API key is needed — the backend uses these to reconstruct
 * IPD and compute log-rank statistics live.
 *
 * Sources:
 *   CABOSUN   — Choueiri et al. 2017, NEJM; PFS HR=0.66 (0.46–0.95)
 *   CheckMate 9ER — Choueiri et al. 2021, NEJM; OS HR=0.60 (0.40–0.89)
 */

import type { KMExtraction } from "./api";

export interface DemoCase {
  id: string;
  label: string;          // card title
  description: string;    // card subtitle
  badge: string;          // e.g. "PFS" or "OS"
  trial: string;          // trial name
  published_hr: string;   // e.g. "0.66 (0.46–0.95)"
  extraction: KMExtraction;
}

// ---------------------------------------------------------------------------
// CABOSUN — Cabozantinib vs Sunitinib, PFS
// Choueiri et al. NEJM 2017; doi:10.1056/NEJMoa1704618
// Median PFS: Cabo 8.2 mo, Suni 5.6 mo; HR=0.66 (0.46–0.95), p=0.012
// ---------------------------------------------------------------------------
const cabosun: KMExtraction = {
  title: "CABOSUN: Progression-Free Survival",
  n_groups: 2,
  extraction_notes: "Pre-extracted demo data. At-risk table from published figure.",
  x_axis: { label: "Months", min: 0, max: 24, unit: "months" },
  y_axis: { label: "Progression-Free Survival", is_percentage: false },
  groups: [
    {
      name: "Cabozantinib",
      color_description: "blue",
      censor_marks: [8.5, 10.1, 11.3, 13.7, 15.2, 17.4, 19.8, 22.1],
      at_risk_table: [
        { time: 0,  n_at_risk: 79 },
        { time: 3,  n_at_risk: 62 },
        { time: 6,  n_at_risk: 47 },
        { time: 9,  n_at_risk: 37 },
        { time: 12, n_at_risk: 26 },
        { time: 15, n_at_risk: 20 },
        { time: 18, n_at_risk: 14 },
        { time: 21, n_at_risk: 9  },
        { time: 24, n_at_risk: 4  },
      ],
      curve_points: [
        { time: 0,  survival: 1.000 },
        { time: 1,  survival: 0.919 },
        { time: 2,  survival: 0.845 },
        { time: 3,  survival: 0.777 },
        { time: 4,  survival: 0.714 },
        { time: 5,  survival: 0.656 },
        { time: 6,  survival: 0.603 },
        { time: 7,  survival: 0.554 },
        { time: 8,  survival: 0.509 },
        { time: 9,  survival: 0.468 },
        { time: 10, survival: 0.430 },
        { time: 11, survival: 0.395 },
        { time: 12, survival: 0.363 },
        { time: 14, survival: 0.307 },
        { time: 16, survival: 0.259 },
        { time: 18, survival: 0.219 },
        { time: 20, survival: 0.185 },
        { time: 22, survival: 0.156 },
        { time: 24, survival: 0.132 },
      ],
    },
    {
      name: "Sunitinib",
      color_description: "red",
      censor_marks: [6.1, 7.8, 9.3, 11.5, 14.2, 17.6, 20.3],
      at_risk_table: [
        { time: 0,  n_at_risk: 78 },
        { time: 3,  n_at_risk: 54 },
        { time: 6,  n_at_risk: 38 },
        { time: 9,  n_at_risk: 25 },
        { time: 12, n_at_risk: 18 },
        { time: 15, n_at_risk: 11 },
        { time: 18, n_at_risk: 7  },
        { time: 21, n_at_risk: 4  },
        { time: 24, n_at_risk: 2  },
      ],
      curve_points: [
        { time: 0,  survival: 1.000 },
        { time: 1,  survival: 0.884 },
        { time: 2,  survival: 0.781 },
        { time: 3,  survival: 0.691 },
        { time: 4,  survival: 0.611 },
        { time: 5,  survival: 0.540 },
        { time: 6,  survival: 0.477 },
        { time: 7,  survival: 0.422 },
        { time: 8,  survival: 0.373 },
        { time: 9,  survival: 0.330 },
        { time: 10, survival: 0.291 },
        { time: 11, survival: 0.258 },
        { time: 12, survival: 0.228 },
        { time: 14, survival: 0.178 },
        { time: 16, survival: 0.139 },
        { time: 18, survival: 0.108 },
        { time: 20, survival: 0.084 },
        { time: 22, survival: 0.066 },
        { time: 24, survival: 0.051 },
      ],
    },
  ],
};

// ---------------------------------------------------------------------------
// CheckMate 9ER — Nivolumab+Cabozantinib vs Sunitinib, OS
// Choueiri et al. NEJM 2021; doi:10.1056/NEJMoa2026982
// Median OS: NivoCabo NR, Suni ~25.9 mo; HR=0.60 (0.40–0.89), p=0.0010
// ---------------------------------------------------------------------------
const checkmate9er: KMExtraction = {
  title: "CheckMate 9ER: Overall Survival",
  n_groups: 2,
  extraction_notes: "Pre-extracted demo data. Curve approximated from published figure.",
  x_axis: { label: "Months", min: 0, max: 55, unit: "months" },
  y_axis: { label: "Overall Survival", is_percentage: false },
  groups: [
    {
      name: "Nivolumab + Cabozantinib",
      color_description: "blue",
      censor_marks: [12.4, 18.7, 24.1, 30.5, 36.8, 42.3, 48.6],
      at_risk_table: [
        { time: 0,  n_at_risk: 323 },
        { time: 6,  n_at_risk: 281 },
        { time: 12, n_at_risk: 243 },
        { time: 18, n_at_risk: 210 },
        { time: 24, n_at_risk: 181 },
        { time: 30, n_at_risk: 155 },
        { time: 36, n_at_risk: 118 },
        { time: 42, n_at_risk: 82  },
        { time: 48, n_at_risk: 41  },
      ],
      curve_points: [
        { time: 0,  survival: 1.000 },
        { time: 3,  survival: 0.959 },
        { time: 6,  survival: 0.920 },
        { time: 9,  survival: 0.882 },
        { time: 12, survival: 0.846 },
        { time: 15, survival: 0.811 },
        { time: 18, survival: 0.778 },
        { time: 21, survival: 0.746 },
        { time: 24, survival: 0.715 },
        { time: 27, survival: 0.686 },
        { time: 30, survival: 0.658 },
        { time: 33, survival: 0.631 },
        { time: 36, survival: 0.605 },
        { time: 39, survival: 0.580 },
        { time: 42, survival: 0.556 },
        { time: 45, survival: 0.533 },
        { time: 48, survival: 0.511 },
        { time: 51, survival: 0.490 },
        { time: 54, survival: 0.470 },
      ],
    },
    {
      name: "Sunitinib",
      color_description: "red",
      censor_marks: [8.2, 15.3, 22.7, 29.1, 35.4, 41.8],
      at_risk_table: [
        { time: 0,  n_at_risk: 328 },
        { time: 6,  n_at_risk: 278 },
        { time: 12, n_at_risk: 231 },
        { time: 18, n_at_risk: 188 },
        { time: 24, n_at_risk: 152 },
        { time: 30, n_at_risk: 119 },
        { time: 36, n_at_risk: 86  },
        { time: 42, n_at_risk: 56  },
        { time: 48, n_at_risk: 26  },
      ],
      curve_points: [
        { time: 0,  survival: 1.000 },
        { time: 3,  survival: 0.921 },
        { time: 6,  survival: 0.848 },
        { time: 9,  survival: 0.781 },
        { time: 12, survival: 0.719 },
        { time: 15, survival: 0.662 },
        { time: 18, survival: 0.610 },
        { time: 21, survival: 0.561 },
        { time: 24, survival: 0.517 },
        { time: 27, survival: 0.476 },
        { time: 30, survival: 0.438 },
        { time: 33, survival: 0.403 },
        { time: 36, survival: 0.371 },
        { time: 39, survival: 0.342 },
        { time: 42, survival: 0.315 },
        { time: 45, survival: 0.290 },
        { time: 48, survival: 0.267 },
        { time: 51, survival: 0.246 },
        { time: 54, survival: 0.226 },
      ],
    },
  ],
};

// ---------------------------------------------------------------------------
// Exported demo cases
// ---------------------------------------------------------------------------
export const DEMO_CASES: DemoCase[] = [
  {
    id: "cabosun",
    label: "CABOSUN Trial",
    description: "Cabozantinib vs Sunitinib in advanced RCC",
    badge: "PFS",
    trial: "NCT01630083",
    published_hr: "0.66 (0.46–0.95)",
    extraction: cabosun,
  },
  {
    id: "checkmate9er",
    label: "CheckMate 9ER",
    description: "Nivolumab+Cabozantinib vs Sunitinib in RCC",
    badge: "OS",
    trial: "NCT03141177",
    published_hr: "0.60 (0.40–0.89)",
    extraction: checkmate9er,
  },
];
