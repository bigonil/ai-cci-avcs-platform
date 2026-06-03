import { type NextRequest, NextResponse } from "next/server"

const UPSTREAM = process.env.GOVERNANCE_SERVICE_URL ?? "http://localhost:8005"

async function proxy(req: NextRequest, params: { path: string[] }): Promise<NextResponse> {
  const tail = params.path.join("/")
  const qs = req.nextUrl.search
  const url = `${UPSTREAM}/${tail}${qs}`

  const init: RequestInit = {
    method: req.method,
    headers: { "Content-Type": "application/json" },
  }
  if (req.method !== "GET" && req.method !== "HEAD") {
    init.body = await req.text()
  }

  try {
    const res = await fetch(url, init)
    const body = await res.text()
    return new NextResponse(body, {
      status: res.status,
      headers: { "Content-Type": res.headers.get("Content-Type") ?? "application/json" },
    })
  } catch (err) {
    return NextResponse.json({ detail: String(err) }, { status: 502 })
  }
}

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
) {
  return proxy(req, await params)
}

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
) {
  return proxy(req, await params)
}
