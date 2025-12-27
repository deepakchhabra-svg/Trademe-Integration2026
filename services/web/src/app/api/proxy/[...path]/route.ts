import { NextRequest, NextResponse } from "next/server";

/**
 * API Proxy Route
 * Forwards all requests to the backend API to avoid CORS issues
 * and centralize error handling.
 *
 * Usage: GET /api/proxy/vaults/raw?page=1
 * Forwards to: GET http://127.0.0.1:8000/vaults/raw?page=1
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

export async function GET(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const resolvedParams = await params;
  const path = resolvedParams.path.join("/");
  const searchParams = request.nextUrl.searchParams.toString();
  const url = `${API_BASE_URL}/${path}${searchParams ? `?${searchParams}` : ""}`;

  try {
    const response = await fetch(url, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
        // Forward relevant headers from the client request
        ...(request.headers.get("X-RetailOS-Role") && {
          "X-RetailOS-Role": request.headers.get("X-RetailOS-Role")!,
        }),
        ...(request.headers.get("X-RetailOS-Token") && {
          "X-RetailOS-Token": request.headers.get("X-RetailOS-Token")!,
        }),
      },
      cache: "no-store",
    });

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error(`[API Proxy] GET /${path} failed:`, error);
    return NextResponse.json(
      { error: "API request failed", detail: error instanceof Error ? error.message : "Unknown error" },
      { status: 503 }
    );
  }
}

export async function POST(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const resolvedParams = await params;
  const path = resolvedParams.path.join("/");
  const url = `${API_BASE_URL}/${path}`;

  try {
    const body = await request.text();
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(request.headers.get("X-RetailOS-Role") && {
          "X-RetailOS-Role": request.headers.get("X-RetailOS-Role")!,
        }),
        ...(request.headers.get("X-RetailOS-Token") && {
          "X-RetailOS-Token": request.headers.get("X-RetailOS-Token")!,
        }),
      },
      body,
      cache: "no-store",
    });

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error(`[API Proxy] POST /${path} failed:`, error);
    return NextResponse.json(
      { error: "API request failed", detail: error instanceof Error ? error.message : "Unknown error" },
      { status: 503 }
    );
  }
}

export async function PUT(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const resolvedParams = await params;
  const path = resolvedParams.path.join("/");
  const url = `${API_BASE_URL}/${path}`;

  try {
    const body = await request.text();
    const response = await fetch(url, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        ...(request.headers.get("X-RetailOS-Role") && {
          "X-RetailOS-Role": request.headers.get("X-RetailOS-Role")!,
        }),
        ...(request.headers.get("X-RetailOS-Token") && {
          "X-RetailOS-Token": request.headers.get("X-RetailOS-Token")!,
        }),
      },
      body,
      cache: "no-store",
    });

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error(`[API Proxy] PUT /${path} failed:`, error);
    return NextResponse.json(
      { error: "API request failed", detail: error instanceof Error ? error.message : "Unknown error" },
      { status: 503 }
    );
  }
}

export async function DELETE(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const resolvedParams = await params;
  const path = resolvedParams.path.join("/");
  const url = `${API_BASE_URL}/${path}`;

  try {
    const response = await fetch(url, {
      method: "DELETE",
      headers: {
        "Content-Type": "application/json",
        ...(request.headers.get("X-RetailOS-Role") && {
          "X-RetailOS-Role": request.headers.get("X-RetailOS-Role")!,
        }),
        ...(request.headers.get("X-RetailOS-Token") && {
          "X-RetailOS-Token": request.headers.get("X-RetailOS-Token")!,
        }),
      },
      cache: "no-store",
    });

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error(`[API Proxy] DELETE /${path} failed:`, error);
    return NextResponse.json(
      { error: "API request failed", detail: error instanceof Error ? error.message : "Unknown error" },
      { status: 503 }
    );
  }
}
