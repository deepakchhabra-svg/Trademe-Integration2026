import { NextRequest, NextResponse } from "next/server";

/**
 * Media Proxy Route (binary-safe)
 * Serves protected backend media (GET /media/*) via same-origin Next.js route.
 *
 * Usage: <img src="/api/media/<rel_path>" />
 * Forwards to: GET ${NEXT_PUBLIC_API_BASE_URL}/media/<rel_path>
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

export async function GET(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const resolvedParams = await params;
  const relPath = resolvedParams.path.join("/");
  const url = `${API_BASE_URL}/media/${relPath}`;

  const token = request.headers.get("X-RetailOS-Token") || request.cookies.get("retailos_token")?.value || "";
  if (!token) {
    return NextResponse.json(
      { error: "Unauthorized", detail: "Missing retailos_token cookie (or X-RetailOS-Token header)." },
      { status: 401 }
    );
  }

  try {
    const upstream = await fetch(url, {
      method: "GET",
      headers: {
        "X-RetailOS-Token": token,
      },
      cache: "no-store",
    });

    if (!upstream.ok) {
      const txt = await upstream.text().catch(() => "");
      return new NextResponse(txt || upstream.statusText, {
        status: upstream.status,
        headers: {
          "Content-Type": upstream.headers.get("Content-Type") || "text/plain; charset=utf-8",
        },
      });
    }

    const contentType = upstream.headers.get("Content-Type") || "application/octet-stream";
    return new NextResponse(upstream.body, {
      status: 200,
      headers: {
        "Content-Type": contentType,
        // Don't leak to shared caches; browsers can still cache privately.
        "Cache-Control": "private, max-age=300",
      },
    });
  } catch (error) {
    console.error(`[Media Proxy] GET /media/${relPath} failed:`, error);
    return NextResponse.json(
      { error: "Media request failed", detail: error instanceof Error ? error.message : "Unknown error" },
      { status: 503 }
    );
  }
}

