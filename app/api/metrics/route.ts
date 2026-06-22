/**
 * /api/metrics — Observability endpoint.
 *
 * Day 5: MLOps. Returns aggregated telemetry from the in-memory metrics store.
 * GET ?window=60  → last 60 minutes of data (default)
 * DELETE          → clear metrics (admin reset)
 */

import { NextRequest, NextResponse } from "next/server";
import { getMetricsSummary, clearMetrics } from "../../../lib/metrics";

export async function GET(req: NextRequest): Promise<NextResponse> {
  const window = parseInt(req.nextUrl.searchParams.get("window") ?? "60", 10);
  const summary = getMetricsSummary(isNaN(window) ? 60 : window);
  return NextResponse.json(summary);
}

export async function DELETE(): Promise<NextResponse> {
  clearMetrics();
  return NextResponse.json({ cleared: true, timestamp: Date.now() });
}
