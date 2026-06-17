"""
Cross-token destination crossmatch.

If two accumulator wallets from DIFFERENT token listings sent profits to
the same destination address → likely same operator, even with fresh
accumulator wallets per listing.

Filters:
- Destinations with total_usd < MIN_USD excluded (dust)
- Destinations that appear in only 1 listing excluded
- Known exchange hot wallets excluded (Binance, OKX, etc.) — they'd
  generate thousands of false positives
"""

import os
from collections import defaultdict
from pathlib import Path
from supabase import create_client
from dotenv import load_dotenv

load_dotenv(Path(__file__).parents[2] / ".env")
sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])

MIN_USD = 1_000       # minimum USD per destination transfer to count
MIN_TOKENS = 2        # minimum distinct tokens sharing a destination

# Known exchange/infra addresses to ignore (add more as discovered)
EXCHANGE_ADDRS = {
    # Binance
    "0x28c6c06298d514db089934071355e5743bf21d60",
    "0x21a31ee1afc51d94c2efccaa2092ad1028285549",
    "0xdfd5293d8e347dfe59e90efd55b2956a1343963d",
    "0xeb2d2f1b8c558a40207669291fda468e50c8a0bb",
    # OKX
    "0x6cc5f688a315f3dc28a7781717a9a798a59fda7b",
    "0xb3de8fd36faea35c2db2e6d8f0a6e56c06f6ae38",
    # Coinbase
    "0x503828976d22510aad0201ac7ec88293211d23da",
    "0xa9d1e08c7793af67e9d92fe308d5697fb81d3e43",
    # Gate.io
    "0x0d0707963952f2fba59dd06f2b425ace40b492fe",
    "0xc882b111a75c0c657fc507c04fbfcd2cc984f071",
    # Kraken
    "0x2910543af39aba0cd09dbb2d50200b3e800a63d2",
}

print("Pulling token_prelisting_wallets...")
rows = []
start = 0
while True:
    r = sb.table("token_prelisting_wallets").select(
        "address,token,token_id,score,total_in_usd,classification,listing_exchange,listing_ts,post_listing_destinations"
    ).range(start, start + 999).execute()
    if not r.data:
        break
    rows.extend(r.data)
    if len(r.data) < 1000:
        break
    start += 1000

print(f"Total rows: {len(rows)}")

# destination_addr -> list of {wallet, token, token_id, listing_exchange, usd, ts}
by_dest = defaultdict(list)

for row in rows:
    dests = row.get("post_listing_destinations") or []
    for d in dests:
        dest = (d.get("destination") or "").lower().strip()
        usd = float(d.get("usd") or 0)
        if not dest or dest in EXCHANGE_ADDRS:
            continue
        if usd < MIN_USD:
            continue
        by_dest[dest].append({
            "wallet": (row["address"] or "").lower(),
            "token": row["token"],
            "token_id": row["token_id"],
            "exchange": row["listing_exchange"] or "?",
            "score": row["score"] or 0,
            "total_in": row["total_in_usd"] or 0,
            "dest_usd": usd,
            "ts": d.get("ts", ""),
        })

# Find destinations shared across multiple distinct tokens
cross_dest = []
for dest, hits in by_dest.items():
    tokens = sorted(set(h["token"] for h in hits))
    if len(tokens) < MIN_TOKENS:
        continue
    total_dest_usd = sum(h["dest_usd"] for h in hits)
    wallets = sorted(set(h["wallet"] for h in hits))
    exchanges = sorted(set(h["exchange"] for h in hits))
    cross_dest.append({
        "dest": dest,
        "token_count": len(tokens),
        "tokens": tokens,
        "wallet_count": len(wallets),
        "wallets": wallets,
        "total_usd": total_dest_usd,
        "exchanges": exchanges,
        "hits": sorted(hits, key=lambda x: -x["dest_usd"]),
    })

cross_dest.sort(key=lambda x: (-x["token_count"], -x["total_usd"]))

print(f"\n{'='*110}")
print(f"CROSS-TOKEN DESTINATION MATCH - mesmo destino em >1 listing ({len(cross_dest)} destinos)")
print(f"{'='*110}\n")

for i, c in enumerate(cross_dest[:50]):
    print(f"{'-'*110}")
    print(f"DEST #{i+1}: {c['dest']}")
    print(f"  Tokens ({c['token_count']}): {', '.join(c['tokens'])}")
    print(f"  Exchanges: {', '.join(c['exchanges'])}")
    print(f"  Wallets acumuladoras: {c['wallet_count']}  |  Total enviado: ${c['total_usd']:,.0f}")
    for h in c["hits"][:6]:
        print(f"    {h['wallet'][:20]}... [{h['token']:<10}] score={h['score']:<4} -> ${h['dest_usd']:>12,.0f}  {h['ts'][:10]}")

print(f"\n{'='*110}")
print(f"RESUMO: {len(cross_dest)} destinos comuns | {sum(c['wallet_count'] for c in cross_dest)} pares wallet-dest")

if cross_dest:
    print(f"\nTOP 3 destinos (possível operador recorrente):")
    for c in cross_dest[:3]:
        print(f"  {c['dest']} → {c['token_count']} tokens: {', '.join(c['tokens'])}")
