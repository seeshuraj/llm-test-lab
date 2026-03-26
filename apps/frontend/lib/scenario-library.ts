// Scenario library stored in localStorage — no backend needed
export interface SavedScenario {
  name: string;
  yaml: string;
  savedAt: string;
}

const KEY = "llm_test_lab_scenarios";

export function listSavedScenarios(): SavedScenario[] {
  try {
    return JSON.parse(localStorage.getItem(KEY) || "[]");
  } catch {
    return [];
  }
}

export function saveScenario(name: string, yaml: string): void {
  const existing = listSavedScenarios().filter((s) => s.name !== name);
  const updated = [{ name, yaml, savedAt: new Date().toISOString() }, ...existing];
  localStorage.setItem(KEY, JSON.stringify(updated));
}

export function deleteScenario(name: string): void {
  const updated = listSavedScenarios().filter((s) => s.name !== name);
  localStorage.setItem(KEY, JSON.stringify(updated));
}
