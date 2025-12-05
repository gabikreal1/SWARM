import jwt from "jsonwebtoken";
import { cookies } from "next/headers";
import type { NextResponse } from "next/server";
import { prisma } from "./prisma";

type TokenPayload = {
  sub: number;
  email: string;
};

const COOKIE_NAME = "swarm_session";

const getSecret = () => {
  const secret = process.env.AUTH_SECRET || "dev-secret-change-me";
  return secret;
};

export const createAuthToken = (payload: TokenPayload) => {
  return jwt.sign(payload, getSecret(), { expiresIn: "7d" });
};

export const verifyAuthToken = (token?: string) => {
  if (!token) return null;
  try {
    return jwt.verify(token, getSecret()) as TokenPayload;
  } catch {
    return null;
  }
};

const baseCookie = {
  name: COOKIE_NAME,
  httpOnly: true,
  sameSite: "lax" as const,
  path: "/",
  secure: process.env.NODE_ENV === "production",
};

export const setAuthCookieOnResponse = (res: NextResponse, token: string) => {
  res.cookies.set({
    ...baseCookie,
    value: token,
    maxAge: 60 * 60 * 24 * 7, // 7 days
  });
};

export const clearAuthCookieOnResponse = (res: NextResponse) => {
  res.cookies.set({
    ...baseCookie,
    value: "",
    maxAge: 0,
  });
};

export const getUserFromRequest = async () => {
  const cookieStore = await cookies();
  const token = cookieStore.get(COOKIE_NAME)?.value;
  const decoded = verifyAuthToken(token);
  if (!decoded) return null;
  const user = await prisma.user.findUnique({ where: { id: decoded.sub } });
  return user;
};

