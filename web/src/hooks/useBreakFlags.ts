"use client";

import { useState, useCallback, useEffect } from "react";
import type { BreakFlag } from "@/types";

const STORAGE_KEY = "wavescout-break-flags";

function generateId(): string {
  // Simple UUID v4 without external deps
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

function loadFromStorage(): BreakFlag[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    // Validate each item has required fields
    return parsed.filter(
      (f: unknown): f is BreakFlag =>
        typeof f === "object" &&
        f !== null &&
        "id" in f &&
        "section_id" in f &&
        "lat" in f &&
        "lon" in f
    );
  } catch {
    return [];
  }
}

function saveToStorage(flags: BreakFlag[]): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(flags));
  } catch (e) {
    // localStorage quota exceeded or unavailable
    console.warn("Failed to save break flags to localStorage:", e);
  }
}

export function useBreakFlags() {
  const [flags, setFlags] = useState<BreakFlag[]>([]);

  // Load from storage on mount
  useEffect(() => {
    setFlags(loadFromStorage());
  }, []);

  const addFlag = useCallback(
    (flag: Omit<BreakFlag, "id" | "flagged_at">) => {
      const newFlag: BreakFlag = {
        ...flag,
        id: generateId(),
        flagged_at: new Date().toISOString(),
      };
      setFlags((prev) => {
        const next = [...prev, newFlag];
        saveToStorage(next);
        return next;
      });
    },
    []
  );

  const removeFlag = useCallback((id: string) => {
    setFlags((prev) => {
      const next = prev.filter((f) => f.id !== id);
      saveToStorage(next);
      return next;
    });
  }, []);

  const exportFlags = useCallback((): string => {
    return JSON.stringify(flags, null, 2);
  }, [flags]);

  return { flags, addFlag, removeFlag, exportFlags };
}
