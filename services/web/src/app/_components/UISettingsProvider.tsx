"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { setCookie } from "./cookies";

export type Theme = "light" | "dark";
export type Density = "compact" | "comfortable";

type Ctx = {
  theme: Theme;
  density: Density;
  setTheme: (t: Theme) => void;
  setDensity: (d: Density) => void;
};

const UISettingsContext = createContext<Ctx | null>(null);

export function UISettingsProvider({
  children,
  initialTheme,
  initialDensity,
}: {
  children: React.ReactNode;
  initialTheme: Theme;
  initialDensity: Density;
}) {
  const [theme, _setTheme] = useState<Theme>(initialTheme);
  const [density, _setDensity] = useState<Density>(initialDensity);

  const applyToDom = useCallback((t: Theme, d: Density) => {
    if (typeof document === "undefined") return;
    const el = document.documentElement;
    el.dataset.theme = t;
    el.dataset.density = d;
  }, []);

  useEffect(() => {
    applyToDom(theme, density);
  }, [applyToDom, theme, density]);

  const setTheme = useCallback(
    (t: Theme) => {
      _setTheme(t);
      setCookie("retailos_theme", t);
      applyToDom(t, density);
    },
    [applyToDom, density],
  );

  const setDensity = useCallback(
    (d: Density) => {
      _setDensity(d);
      setCookie("retailos_density", d);
      applyToDom(theme, d);
    },
    [applyToDom, theme],
  );

  const value = useMemo<Ctx>(() => ({ theme, density, setTheme, setDensity }), [theme, density, setTheme, setDensity]);

  return <UISettingsContext.Provider value={value}>{children}</UISettingsContext.Provider>;
}

export function useUISettings(): Ctx {
  const ctx = useContext(UISettingsContext);
  if (!ctx) throw new Error("useUISettings must be used within UISettingsProvider");
  return ctx;
}

