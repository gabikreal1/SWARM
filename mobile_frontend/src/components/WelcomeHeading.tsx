'use client';

import React from 'react';
import { SplitText } from './SplitText';

export function WelcomeHeading() {
  return (
    <h1 className="text-3xl md:text-4xl font-bold text-white mb-4">
      <SplitText text="Welcome to Swarm" type="words" className="inline-block" />
    </h1>
  );
}

