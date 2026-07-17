"""
Slår sammen JSON-output fra alle skraperne (DNB, OBOS, USBL, Elbilforeningen)
til én flat fil, webapp/data/discounts.json, som PWA-appen laster.

Kjør: python3 combine.py
(kjør skraperne først: dnb_faste_rabatter.py, obos_medlemsfordeler.py,
usbl_medlemsfordeler.py - elbilforeningen_medlemsfordeler.json er et
manuelt vedlikeholdt øyeblikksbilde, se README)
"""

import json
from datetime import datetime, timezone
from pathlib import Path

SOURCE_FILES = [
    "dnb_faste_rabatter.json",
    "obos_medlemsfordeler.json",
    "elbilforeningen_medlemsfordeler.json",
    "usbl_medlemsfordeler.json",
    "lofavor_medlemsfordeler.json",
    "akademikerforbundet_medlemsfordeler.json",
]

OUTPUT_PATH = Path("webapp/data/discounts.json")


def main():
    all_discounts = []
    sources_meta = []

    for filename in SOURCE_FILES:
        path = Path(filename)
        if not path.exists():
            print(f"Hopper over {filename} (finnes ikke - kjør skraperen først)")
            continue

        data = json.loads(path.read_text(encoding="utf-8"))
        discounts = data.get("discounts", [])
        all_discounts.extend(discounts)

        sources_meta.append(
            {
                "provider": data.get("provider"),
                "source_page": data.get("source_page"),
                "shared_discount_code": data.get("shared_discount_code"),
                "count": len(discounts),
                "fetched_at": data.get("fetched_at"),
            }
        )
        print(f"{data.get('provider')}: {len(discounts)} rabatter")

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sources": sources_meta,
        "discounts": all_discounts,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"\nTotalt {len(all_discounts)} rabatter fra {len(sources_meta)} leverandører")
    print(f"Lagret til {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
