'use client';
import React from 'react';

export default function Markdown({ text }: { text: string }) {
  const html = text
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/^\s*-\s+/gm, '• ')
    .replace(/\n/g, '<br/>');

  return <span dangerouslySetInnerHTML={{ __html: html }} />;
}
