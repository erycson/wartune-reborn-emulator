"""Recalcula a tabela "Resumo" do docs/progresso.md a partir das linhas de status (Inglês / Turco)."""

import pathlib
import re

DOC = pathlib.Path(__file__).resolve().parent.parent / "docs" / "progresso.md"
KEYS = ["✅", "🟡", "🧪", "❌"]


def main() -> None:
    text = DOC.read_text(encoding="utf-8")
    rows: list[tuple[str, str, str]] = []
    cat = ""
    for line in text.splitlines():
        if line.startswith("## "):
            cat = line[3:].strip()
        elif line.startswith("| ") and not line.startswith(("| Sistema", "| Categoria", "| **Total")):
            c = [x.strip() for x in line.strip().strip("|").split("|")]
            if len(c) == 4:
                assert c[1] in KEYS and c[2] in ("", "🇹🇷"), line
                rows.append((cat, c[1], c[2]))
    out = ["## Resumo", "", "| Categoria | ✅ | 🟡 | 🧪 | ❌ | 🇹🇷 |", "|---|---|---|---|---|---|"]
    tot = [0] * 5
    for k in dict.fromkeys(r[0] for r in rows):
        n = [sum(r[0] == k and r[1] == e for r in rows) for e in KEYS]
        n.append(sum(r[0] == k and r[2] == "🇹🇷" for r in rows))
        tot = [a + b for a, b in zip(tot, n, strict=True)]
        out.append(f"| {k} | " + " | ".join(map(str, n)) + " |")
    out.append("| **Total** | " + " | ".join(f"**{x}**" for x in tot) + " |")
    new, count = re.subn(r"## Resumo\n.*?\| \*\*Total\*\*[^\n]*", "\n".join(out), text, count=1, flags=re.S)
    assert count == 1, "seção Resumo não encontrada"
    DOC.write_text(new, encoding="utf-8")
    print(len(rows), "sistemas; ok/parcial/inventado/sem/turco =", tot)


if __name__ == "__main__":
    main()
