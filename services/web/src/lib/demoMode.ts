"use client";

import { apiGet } from "./api";

let demoModeState: boolean | null = null;

interface HealthResponse {
    status: string;
    utc: string;
}

/**
 * Check if the API is available
 * This is called on app load (client-side only)
 */
export async function checkApiHealth(): Promise<boolean> {
    try {
        const health = await apiGet<HealthResponse>("/health", { timeout: 3000 });
        return health.status === "ok";
    } catch {
        return false;
    }
}

/**
 * Initialize demo mode detection
 * Call this once on app load
 */
export async function initDemoMode(): Promise<void> {
    const isHealthy = await checkApiHealth();
    demoModeState = !isHealthy;

    if (demoModeState) {
        console.warn("[Demo Mode] API is offline. Using fixture data.");
    }
}

/**
 * Check if demo mode is enabled
 */
export function isDemoMode(): boolean {
    return demoModeState === true;
}

/**
 * Force set demo mode (for testing)
 */
export function setDemoMode(enabled: boolean): void {
    demoModeState = enabled;
}

/**
 * Get demo data from fixtures
 */
export async function getDemoData<T>(key: string): Promise<T> {
    try {
        const response = await fetch(`/fixtures/${key}.json`);
        if (!response.ok) {
            throw new Error(`Failed to load fixture: ${key}`);
        }
        return (await response.json()) as T;
    } catch (error) {
        console.error(`[Demo Mode] Failed to load fixture ${key}:`, error);
        throw error;
    }
}
