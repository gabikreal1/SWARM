import { NextResponse, type NextRequest } from "next/server";

const COOKIE_NAME = "swarm_session";

// Lightweight presence check; API routes do full JWT verification.
function isValidToken(token?: string) {
  return Boolean(token);
}

export async function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;
  const token = req.cookies.get(COOKIE_NAME)?.value;
  const isValidSession = isValidToken(token);

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

