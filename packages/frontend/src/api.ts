import type { AnalyzeResponse } from "./types.ts";

const API_BASE = import.meta.env.VITE_API_URL || '/api';

export const fetchTargetWord = async (minMora = 2, maxMora = 8): Promise<AnalyzeResponse> => {
  const res = await fetch(`${API_BASE}/target-word?min_mora=${minMora}&max_mora=${maxMora}`);
  if (!res.ok) {
    throw new Error('Failed to fetch target word');
  }
  return res.json();
};

export const analyzeText = async (text: string): Promise<AnalyzeResponse> => {
  const res = await fetch(`${API_BASE}/analyze`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ text }),
  });
  if (!res.ok) {
    throw new Error('Failed to analyze text');
  }
  return res.json();
};
