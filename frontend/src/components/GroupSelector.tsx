"use client";

import { useState } from "react";

interface Props {
  groups: string[];          // extracted group names from LLM
  onConfirm: (indexA: number, indexB: number) => void;
}

export default function GroupSelector({ groups, onConfirm }: Props) {
  const [indexA, setIndexA] = useState(0);
  const [indexB, setIndexB] = useState(1);

  const invalid = indexA === indexB;

  return (
    <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 space-y-3">
      <p className="text-sm font-semibold text-amber-900">
        {groups.length} groups detected — select two to compare:
      </p>

      <div className="grid grid-cols-2 gap-3">
        {(["A", "B"] as const).map((slot) => {
          const idx = slot === "A" ? indexA : indexB;
          const setIdx = slot === "A" ? setIndexA : setIndexB;
          return (
            <div key={slot}>
              <label className="text-xs text-slate-500 mb-1 block">Group {slot}</label>
              <select
                value={idx}
                onChange={(e) => setIdx(Number(e.target.value))}
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm bg-white"
              >
                {groups.map((name, i) => (
                  <option key={i} value={i}>{name}</option>
                ))}
              </select>
            </div>
          );
        })}
      </div>

      {invalid && (
        <p className="text-xs text-red-500">Group A and Group B must be different.</p>
      )}

      <button
        onClick={() => onConfirm(indexA, indexB)}
        disabled={invalid}
        className="w-full bg-primary text-white rounded-xl py-2 text-sm font-semibold disabled:opacity-50 hover:bg-blue-700"
      >
        Compare Selected Groups
      </button>
    </div>
  );
}
