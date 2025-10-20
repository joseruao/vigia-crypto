import { NextResponse } from 'next/server';
import { supabase } from '@/lib/supabaseClient';

export async function GET() {
  try {
    const { data, error } = await supabase
      .from('transacted_tokens')
      .select('*')
      .eq('type', 'holding')
      .gte('score', 70)
      .order('created_at', { ascending: false })
      .limit(15);

    if (error) {
      console.error('Supabase error:', error);
      return NextResponse.json([], { status: 500 });
    }
    
    console.log(`📊 API Holdings: ${data?.length || 0} holdings encontrados`);
    return NextResponse.json(data || []);
  } catch (error) {
    console.error('Error fetching holdings:', error);
    return NextResponse.json([], { status: 500 });
  }
}