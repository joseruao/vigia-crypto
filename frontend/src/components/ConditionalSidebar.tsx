'use client';

import { usePathname } from 'next/navigation';
import { Sidebar } from './Sidebar';

// The crypto chat sidebar belongs to the main site, not to private standalone tools.
export function ConditionalSidebar() {
  const pathname = usePathname();
  if (pathname?.startsWith('/devil')) return null;
  if (pathname?.startsWith('/pme')) return null;
  return <Sidebar />;
}
