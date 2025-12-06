"use client";

import React, { useEffect, useRef, useState } from 'react';

export type ChatMessage = {
  id: string;
  role: 'user' | 'assistant' | 'system';
  text: string;
  timestamp?: string;
  isTranscribed?: boolean;
};

interface ChatTimelineProps {
  messages: ChatMessage[];
}

export const ChatTimeline: React.FC<ChatTimelineProps> = ({ messages }) => {
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const timersRef = useRef<Record<string, number>>({});
  const startedRef = useRef<Set<string>>(new Set());
  const [renderedTexts, setRenderedTexts] = useState<Record<string, string>>({});

  const setRenderedText = (id: string, text: string) => {
    setRenderedTexts((prev) => ({ ...prev, [id]: text }));
  };

  useEffect(() => {
    if (!bottomRef.current) return;
    bottomRef.current.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    messages.forEach((msg) => {
      if (startedRef.current.has(msg.id)) return;

      startedRef.current.add(msg.id);

      const role = (msg.role || '').toLowerCase();
      const isAgent = role === 'agent' || role === 'assistant';

      if (!isAgent) {
        setRenderedText(msg.id, msg.text);
        return;
      }

      // Start typing animation for assistant messages
      setRenderedText(msg.id, '');
      let idx = 0;
      const intervalId = window.setInterval(() => {
        idx += 1;
        const next = msg.text.slice(0, idx);
        setRenderedText(msg.id, next);

        if (idx >= msg.text.length) {
          window.clearInterval(intervalId);
          delete timersRef.current[msg.id];
        }
      }, 18);

      timersRef.current[msg.id] = intervalId;
    });
  }, [messages]);

  useEffect(() => {
    return () => {
      Object.values(timersRef.current).forEach((id) => window.clearInterval(id));
      timersRef.current = {};
    };
  }, []);

  if (!messages.length) return null;

  return (
    <div className="chat-timeline">
      {messages.map((msg) => {
        const role = (msg.role || '').toLowerCase();
        const isAgent = role === 'agent' || role === 'assistant';
        const isUser = !isAgent; // default anything else to user so it aligns right
        const rowClass = isUser ? 'chat-row-user' : 'chat-row-assistant';
        const altAgent = isAgent && (Number(msg.id?.split('-').pop()) || 0) % 2 === 1;
        const bubbleClass = [
          isUser ? 'chat-bubble-user' : 'chat-bubble-assistant',
          altAgent ? 'chat-bubble-assistant-alt' : null,
          msg.isTranscribed ? 'chat-bubble-transcribed' : null,
        ]
          .filter(Boolean)
          .join(' ');
        const displayText = renderedTexts[msg.id] ?? (isAgent ? '' : msg.text);
        return (
          // Messenger-style: agent/assistant left, user right
          <div key={msg.id} className={`chat-row ${rowClass}`}>
            <div className={`chat-bubble ${bubbleClass}`}>
              <p className="chat-text">{displayText}</p>
            </div>
          </div>
        );
      })}
      <div ref={bottomRef} />
    </div>
  );
};
