'use client';

import React from 'react';
import { motion } from 'framer-motion';

type SplitTextProps = {
  text: string;
  type?: 'words' | 'chars';
  className?: string;
};

export function SplitText({ text, type = 'words', className }: SplitTextProps) {
  const items = type === 'words' ? text.split(' ') : Array.from(text);

  return (
    <span className={className}>
      {items.map((item, index) => (
        <motion.span
          key={index}
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, ease: 'easeOut', delay: index * 0.06 }}
          style={{ display: 'inline-block', whiteSpace: 'pre' }}
        >
          {type === 'words' ? (index > 0 ? ` ${item}` : item) : item}
        </motion.span>
      ))}
    </span>
  );
}
