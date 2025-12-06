"use client";

import { usePathname } from "next/navigation";
import { ReactNode } from "react";

type Props = {
  children: ReactNode;
};

/**
 * Lightweight route transition wrapper.
 * Adds a subtle fade/slide when the pathname changes.
 */
export function PageTransition({ children }: Props) {
  const pathname = usePathname();

  return (
    <div key={pathname} className="page-transition">
      {children}
    </div>
  );
}

