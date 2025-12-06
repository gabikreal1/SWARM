import { NextResponse, type NextRequest } from "next/server";

const COOKIE_NAME = "swarm_session";

// Lightweight JWT check without pulling prisma into middleware
function isValidToken(token?: string) {
  if (!token) return false;
  try {
    const secret = process.env.AUTH_SECRET || "dev-secret-change-me";
    // verify signature with Web Crypto
    const [headerB64, payloadB64, sigB64] = token.split(".");
    if (!headerB64 || !payloadB64 || !sigB64) return false;
    const encoder = new TextEncoder();
    const keyData = encoder.encode(secret);
    const data = encoder.encode(`${headerB64}.${payloadB64}`);
    const signature = Uint8Array.from(atob(sigB64.replace(/-/g, "+").replace(/_/g, "/")), c => c.charCodeAt(0));
    return crypto.subtle
      .importKey("raw", keyData, { name: "HMAC", hash: "SHA-256" }, false, ["verify"])
      .then(key => crypto.subtle.verify("HMAC", key, signature, data))
      .catch(() => false);
  } catch {
    return false;
  }
}

export async function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;
  const token = req.cookies.get(COOKIE_NAME)?.value;
  const isValidSession = await isValidToken(token);

  // If authenticated user hits login, send home
  if (pathname === "/login" && isValidSession) {
    const url = req.nextUrl.clone();
    url.pathname = "/";
    return NextResponse.redirect(url);
  }

  const isProtected =
    pathname.startsWith("/dashboard") || pathname.startsWith("/agents");

  if (isProtected && !isValidSession) {
    const url = req.nextUrl.clone();
    url.pathname = "/login";
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/dashboard/:path*", "/agents/:path*", "/login"],
};

