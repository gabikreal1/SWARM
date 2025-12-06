'use client';

import React from 'react';
import { motion } from 'framer-motion';

type ShinyTextProps = {
  children: string;
  className?: string;
};

export function ShinyText({ children, className }: ShinyTextProps) {
  return (
    <motion.span
      className={
        className ??
        'relative inline-block bg-clip-text text-transparent bg-gradient-to-r from-slate-200 via-white to-slate-300'
      }
      initial={{ backgroundPosition: '0% 50%' }}
      animate={{ backgroundPosition: ['0% 50%', '100% 50%', '0% 50%'] }}
      transition={{ duration: 3, repeat: Infinity, ease: 'linear' }}
      style={{ backgroundSize: '200% 200%' }}
    >
      {children}
    </motion.span>
  );
}
