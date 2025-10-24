'use client'
import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { supabase } from '@/lib/supabaseClient'


export default function Callback() {
const router = useRouter()


useEffect(() => {
supabase.auth.getSession().then(({ data: { session } }) => {
if (session) {
router.push('/')
} else {
supabase.auth.getUser().then(() => {
router.push('/')
}).catch(() => {
router.push('/login')
})
}
})
}, [router])


return <p className="p-6 text-sm">A processar login...</p>
}