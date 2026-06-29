'use client';

import { usePathname } from 'next/navigation';
import { Sidebar } from './Sidebar';

// The crypto chat sidebar belongs to the main site, not to the Devil's Advocate
// legal tool. Hide it on /devil and /devils-advocate so the page (and the desktop
// app, which loads /devil) renders as a clean standalone UI.
export function ConditionalSidebar() {
  const pathname = usePathname();
  if (pathname?.startsWith('/devil')) return null;
  return <Sidebar />;
}
