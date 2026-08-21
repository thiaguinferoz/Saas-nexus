import { NextRequest, NextResponse } from "next/server";

const SITE_HOSTS = new Set(["usenexusia.com", "www.usenexusia.com"]);
const APP_HOST = "app.usenexusia.com";

export function middleware(request: NextRequest) {
  const forwardedHost = request.headers.get("x-forwarded-host")?.split(",")[0]?.trim();
  const hostname = (forwardedHost ?? request.nextUrl.hostname).split(":")[0];
  const pathname = request.nextUrl.pathname;

  if (hostname === APP_HOST && pathname === "/") {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  if (SITE_HOSTS.has(hostname) && pathname === "/") {
    return NextResponse.rewrite(new URL("/landing", request.url));
  }

  const accountRoutes = ["/login", "/cadastro", "/esqueci-minha-senha", "/reenviar-confirmacao", "/verificar-email", "/redefinir-senha"];
  if (SITE_HOSTS.has(hostname) && (accountRoutes.includes(pathname) || pathname.startsWith("/app"))) {
    const destination = request.nextUrl.clone();
    destination.hostname = APP_HOST;
    destination.port = "";
    destination.protocol = "https:";
    return NextResponse.redirect(destination);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/", "/login", "/cadastro", "/esqueci-minha-senha", "/reenviar-confirmacao", "/verificar-email", "/redefinir-senha", "/app/:path*"],
};
