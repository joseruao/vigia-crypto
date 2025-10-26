// frontend/src/components/Sidebar.tsx
'use client'
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';
import { createClientComponentClient } from '@supabase/auth-helpers-nextjs';
import type { Session } from '@supabase/auth-helpers-nextjs';


export function Sidebar({ userSession }: { userSession: Session | null }) {
const pathname = usePathname();
const supabase = createClientComponentClient();
const [session, setSession] = useState<Session | null>(userSession);


useEffect(() => {
const { data: listener } = supabase.auth.onAuthStateChange((_event, session) => {
setSession(session);
});
return () => listener?.subscription?.unsubscribe();
}, [supabase]);


const logout = async () => {
await supabase.auth.signOut();
location.href = '/login';
};


return (
<aside className="w-64 bg-gray-50 border-r border-gray-200 p-4">
<h2 className="text-xl font-semibold mb-4">Vigia Crypto</h2>
<nav className="space-y-2">
<Link href="/" className={pathname === '/' ? 'font-bold' : ''}>Dashboard</Link>
<Link href="/wallets" className={pathname === '/wallets' ? 'font-bold' : ''}>Wallets</Link>
<Link href="/holdings" className={pathname === '/holdings' ? 'font-bold' : ''}>Holdings</Link>
</nav>
{session ? (
<button onClick={logout} className="mt-6 text-sm text-red-600">Sair</button>
) : (
<Link href="/login" className="mt-6 text-sm text-blue-600">Entrar</Link>
)}
</aside>
);
}