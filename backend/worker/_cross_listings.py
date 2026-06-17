import os
from collections import defaultdict
from pathlib import Path
from supabase import create_client
from dotenv import load_dotenv

load_dotenv(Path(__file__).parents[2] / ".env")
sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])

# Pull all prelisting wallet rows
rows = []
start = 0
while True:
    r = sb.table("token_prelisting_wallets").select(
        "address,token,token_id,score,total_in_usd,classification,listing_exchange,listing_ts"
    ).range(start, start + 999).execute()
    if not r.data:
        break
    rows.extend(r.data)
    if len(r.data) < 1000:
        break
    start += 1000

print(f"Linhas totais: {len(rows)}")

by_addr = defaultdict(list)
for row in rows:
    by_addr[(row["address"] or "").lower()].append(row)

# Cross-listing repeat players: same address in >1 distinct token
repeat = []
for addr, recs in by_addr.items():
    toks = sorted(set(x["token"] for x in recs))
    if len(toks) > 1:
        total_in = sum((x["total_in_usd"] or 0) for x in recs)
        avg_score = sum((x["score"] or 0) for x in recs) / len(recs)
        exchanges = sorted(set((x["listing_exchange"] or "?") for x in recs))
        repeat.append((addr, len(toks), toks, total_in, avg_score, exchanges))

repeat.sort(key=lambda x: (-x[1], -x[3]))

print(f"\n{'='*100}")
print(f"REPEAT PLAYERS — wallets em MAIS de 1 listing ({len(repeat)} wallets)")
print(f"{'='*100}\n")
for addr, n, toks, total_in, avg_score, exchanges in repeat[:60]:
    print(f"{addr}  | {n} tokens | ${total_in:,.0f} | score~{avg_score:.0f} | {'/'.join(exchanges)}")
    print(f"    tokens: {', '.join(toks)}")
