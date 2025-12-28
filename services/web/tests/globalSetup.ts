import { execSync } from "child_process";
import path from "path";

export default async function globalSetup() {
  const repoRoot = path.resolve(__dirname, "../..", "..");

  // Use a single sqlite DB for API + worker during E2E runs.
  const dbUrl = process.env.RETAILOS_E2E_DATABASE_URL || "sqlite:///./dev_db.sqlite";

  // Seed deterministic data so table-based tests always have rows.
  execSync("python3 scripts/seed_smoke_data.py", {
    cwd: repoRoot,
    stdio: "inherit",
    env: {
      ...process.env,
      PYTHONPATH: repoRoot,
      DATABASE_URL: dbUrl,
    },
  });
}

