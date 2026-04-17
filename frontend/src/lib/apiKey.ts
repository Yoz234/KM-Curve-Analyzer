const PROVIDER_STORAGE_KEY = "llm_provider";

export type Provider = "openai" | "anthropic" | "google";

export const PROVIDERS: { value: Provider; label: string; placeholder: string }[] = [
  { value: "openai",    label: "OpenAI (gpt-4o)",              placeholder: "sk-..." },
  { value: "anthropic", label: "Anthropic (claude-sonnet-4-6)", placeholder: "sk-ant-api03-..." },
  { value: "google",    label: "Google (gemini-2.0-flash)",     placeholder: "AIza..." },
];

function keyStorageKey(provider: Provider): string {
  return `api_key_${provider}`;
}

export function getApiKey(provider?: Provider): string {
  if (typeof window === "undefined") return "";
  const p = provider ?? getProvider();
  return localStorage.getItem(keyStorageKey(p)) ?? "";
}

export function setApiKey(key: string, provider?: Provider): void {
  if (typeof window === "undefined") return;
  const p = provider ?? getProvider();
  // Strip BOM, carriage returns, and all non-printable/non-ASCII-visible chars
  const cleaned = key.replace(/[\u0000-\u001F\u007F\uFEFF\r\n]/g, "").trim();
  cleaned ? localStorage.setItem(keyStorageKey(p), cleaned)
          : localStorage.removeItem(keyStorageKey(p));
}

export function clearApiKey(provider?: Provider): void {
  if (typeof window === "undefined") return;
  const p = provider ?? getProvider();
  localStorage.removeItem(keyStorageKey(p));
}

export function getProvider(): Provider {
  if (typeof window === "undefined") return "openai";
  return (localStorage.getItem(PROVIDER_STORAGE_KEY) as Provider) ?? "openai";
}

export function setProvider(p: Provider): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(PROVIDER_STORAGE_KEY, p);
}
