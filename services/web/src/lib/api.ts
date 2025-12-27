/**
 * Client-side API wrapper
 * Use this for client components that need to make API calls
 * Server components should use the existing _components/api.ts
 */

export class ApiError extends Error {
    constructor(
        message: string,
        public status: number,
        public detail?: string
    ) {
        super(message);
        this.name = "ApiError";
    }
}

export interface FetchOptions {
    method?: "GET" | "POST" | "PUT" | "DELETE";
    body?: unknown;
    timeout?: number;
    retry?: boolean;
}

/**
 * Fetch data from the API via the proxy route
 */
export async function apiFetch<T>(path: string, options: FetchOptions = {}): Promise<T> {
    const { method = "GET", body, timeout = 10000, retry = false } = options;

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    try {
        const url = `/api/proxy/${path.startsWith("/") ? path.slice(1) : path}`;

        const response = await fetch(url, {
            method,
            headers: {
                "Content-Type": "application/json",
            },
            body: body ? JSON.stringify(body) : undefined,
            signal: controller.signal,
            cache: "no-store",
        });

        clearTimeout(timeoutId);

        if (!response.ok) {
            let detail = "";
            try {
                const errorData = await response.json();
                detail = errorData.detail || errorData.error || "";
            } catch {
                detail = await response.text();
            }
            throw new ApiError(`API request failed: ${method} ${path}`, response.status, detail);
        }

        return (await response.json()) as T;
    } catch (error) {
        clearTimeout(timeoutId);

        if (error instanceof ApiError) {
            throw error;
        }

        if (error instanceof Error && error.name === "AbortError") {
            throw new ApiError(`Request timeout: ${method} ${path}`, 408, `Request took longer than ${timeout}ms`);
        }

        throw new ApiError(
            `Network error: ${method} ${path}`,
            0,
            error instanceof Error ? error.message : "Unknown error"
        );
    }
}

/**
 * Convenience method for GET requests
 */
export async function apiGet<T>(path: string, options: Omit<FetchOptions, "method"> = {}): Promise<T> {
    return apiFetch<T>(path, { ...options, method: "GET" });
}

/**
 * Convenience method for POST requests
 */
export async function apiPost<T>(path: string, body?: unknown, options: Omit<FetchOptions, "method" | "body"> = {}): Promise<T> {
    return apiFetch<T>(path, { ...options, method: "POST", body });
}

/**
 * Convenience method for PUT requests
 */
export async function apiPut<T>(path: string, body?: unknown, options: Omit<FetchOptions, "method" | "body"> = {}): Promise<T> {
    return apiFetch<T>(path, { ...options, method: "PUT", body });
}

/**
 * Convenience method for DELETE requests
 */
export async function apiDelete<T>(path: string, options: Omit<FetchOptions, "method"> = {}): Promise<T> {
    return apiFetch<T>(path, { ...options, method: "DELETE" });
}
