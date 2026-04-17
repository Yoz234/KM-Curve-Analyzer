"use client";

import { useState, useEffect } from "react";
import { getApiKey, setApiKey, clearApiKey, getProvider, setProvider, PROVIDERS, type Provider } from "@/lib/apiKey";
import clsx from "clsx";

export default function ApiKeyBanner() {
  const [provider, setProviderState] = useState<Provider>("openai");
  // One key input per provider
  const [keys, setKeys] = useState<Record<Provider, string>>({
    openai: "", anthropic: "", google: "",
  });
  const [show, setShow] = useState(false);

  useEffect(() => {
    const p = getProvider();
    setProviderState(p);
    setKeys({
      openai:    getApiKey("openai"),
      anthropic: getApiKey("anthropic"),
      google:    getApiKey("google"),
    });
    const anyMissing = !getApiKey(p);
    if (anyMissing) setShow(true);
  }, []);

  function handleProviderChange(p: Provider) {
    setProviderState(p);
    setProvider(p);
  }

  function handleSave(p: Provider) {
    setApiKey(keys[p], p);
  }

  function handleClear(p: Provider) {
    clearApiKey(p);
    setKeys((prev) => ({ ...prev, [p]: "" }));
  }

  const activeKey = keys[provider];
  const label = PROVIDERS.find((p) => p.value === provider)?.label ?? provider;

  return (
    <div className="mb-6 rounded-xl border border-slate-200 bg-white overflow-hidden">
      <button
        onClick={() => setShow((s) => !s)}
        className="w-full flex items-center justify-between px-4 py-3 text-sm hover:bg-slate-50"
      >
        <div className="flex items-center gap-2">
          <span className="font-medium text-slate-700">LLM Provider & API Key</span>
          <span className="text-xs text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full">{label}</span>
          {activeKey ? (
            <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">Key saved</span>
          ) : (
            <span className="text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full">Key required</span>
          )}
        </div>
        <span className="text-slate-400 text-xs">{show ? "▲" : "▼"}</span>
      </button>

      {show && (
        <div className="border-t border-slate-100 px-4 pb-4 space-y-4">
          {/* Provider tabs */}
          <div className="flex gap-2 mt-3">
            {PROVIDERS.map((p) => (
              <button
                key={p.value}
                onClick={() => handleProviderChange(p.value)}
                className={clsx(
                  "flex-1 text-xs px-3 py-2 rounded-lg border transition-colors",
                  provider === p.value
                    ? "border-primary bg-blue-50 text-primary font-medium"
                    : "border-slate-200 text-slate-500 hover:border-slate-300"
                )}
              >
                {p.label}
              </button>
            ))}
          </div>

          {/* One key row per provider */}
          {PROVIDERS.map((p) => (
            <div key={p.value} className={clsx(provider !== p.value && "hidden")}>
              <label className="text-xs text-slate-500 mb-1 block">
                {p.label} API Key
                <span className="ml-2 text-slate-400">(stored locally, never shared)</span>
              </label>
              <div className="flex gap-2">
                <input
                  type="password"
                  className="flex-1 border border-slate-300 rounded-lg px-3 py-2 text-sm font-mono"
                  placeholder={p.placeholder}
                  value={keys[p.value]}
                  onChange={(e) => setKeys((prev) => ({ ...prev, [p.value]: e.target.value }))}
                  onKeyDown={(e) => e.key === "Enter" && handleSave(p.value)}
                />
                <button
                  onClick={() => handleSave(p.value)}
                  className="bg-primary text-white px-4 rounded-lg text-sm font-medium hover:bg-blue-700"
                >
                  Save
                </button>
                {keys[p.value] && (
                  <button
                    onClick={() => handleClear(p.value)}
                    className="border border-slate-300 text-slate-600 px-3 rounded-lg text-sm hover:bg-slate-50"
                  >
                    Clear
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
