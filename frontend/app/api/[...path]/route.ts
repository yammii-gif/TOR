import { NextRequest } from 'next/server';

export const dynamic = 'force-dynamic';

// Browser requests stay on the frontend origin, including HttpOnly sessions.
// Only this server needs access to the backend's internal address.
async function proxy(request: NextRequest) {
  const backend = process.env.BACKEND_URL || 'http://127.0.0.1:8000';
  const path = request.nextUrl.pathname.slice('/api'.length);
  const target = new URL(backend);
  target.pathname = path;
  target.search = request.nextUrl.search;
  const headers = new Headers();
  for (const name of ['content-type', 'cookie']) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }
  try {
    const upstream = await fetch(target, {
      method: request.method,
      headers,
      body: request.method === 'POST' ? await request.arrayBuffer() : undefined,
      cache: 'no-store',
      redirect: 'manual',
      signal: AbortSignal.timeout(30000),
    });
    const output = new Headers({ 'Cache-Control': 'no-store' });
    for (const name of ['content-type', 'content-disposition']) {
      const value = upstream.headers.get(name);
      if (value) output.set(name, value);
    }
    for (const cookie of upstream.headers.getSetCookie()) {
      output.append('set-cookie', cookie);
    }
    return new Response(upstream.body, { status: upstream.status, headers: output });
  } catch {
    return Response.json({ detail: 'ไม่สามารถเชื่อมต่อ Backend ได้ กรุณาตรวจสอบบริการ' }, { status: 502 });
  }
}

export { proxy as GET, proxy as POST };
