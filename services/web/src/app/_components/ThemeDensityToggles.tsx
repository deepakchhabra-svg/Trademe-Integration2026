"use client";

import { buttonClass } from "./ui";
import { useUISettings } from "./UISettingsProvider";

export function ThemeDensityToggles() {
  const { theme, density, setTheme, setDensity } = useUISettings();

  return (
    <div className="space-y-3">
      <div className="text-[11px] font-semibold uppercase tracking-wide ros-muted">Appearance</div>

      <div className="flex items-center justify-between gap-2">
        <div className="text-xs ros-muted">Theme</div>
        <div className="flex gap-1">
          <button
            type="button"
            className={buttonClass({ variant: theme === "light" ? "primary" : "outline" })}
            onClick={() => setTheme("light")}
          >
            Light
          </button>
          <button
            type="button"
            className={buttonClass({ variant: theme === "dark" ? "primary" : "outline" })}
            onClick={() => setTheme("dark")}
          >
            Dark
          </button>
        </div>
      </div>

      <div className="flex items-center justify-between gap-2">
        <div className="text-xs ros-muted">Tables</div>
        <div className="flex gap-1">
          <button
            type="button"
            className={buttonClass({ variant: density === "compact" ? "primary" : "outline" })}
            onClick={() => setDensity("compact")}
          >
            Compact
          </button>
          <button
            type="button"
            className={buttonClass({ variant: density === "comfortable" ? "primary" : "outline" })}
            onClick={() => setDensity("comfortable")}
          >
            Comfortable
          </button>
        </div>
      </div>

      <div className="text-[11px] ros-muted">Saved locally (cookie). No refresh required.</div>
    </div>
  );
}

