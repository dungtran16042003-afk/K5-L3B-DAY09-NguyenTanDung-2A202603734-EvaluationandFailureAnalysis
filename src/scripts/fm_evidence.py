"""Sinh bằng chứng trace cho các failure mode không có trong variant công khai (M1).

Dùng đúng công tắc lỗi của lab9.variant_agent (không sửa lab8, không sửa variant).
Mỗi probe đăng ký một shape một-off rồi chạy 1 claim@seed qua lab9.trace_case.

    python -m scripts.fm_evidence            # chạy toàn bộ probe in ra trace
"""
from __future__ import annotations

import json

from lab8.console import utf8_stdio
from lab9.trace_case import investigate
from lab9.variant_agent import make_shape

# (tên probe, tập công tắc lỗi, claim, seed, FM muốn quan sát)
PROBES = [
    ("probe_leaky", {"leaky_trace"}, "C-001", 11, "FM-01"),
    ("probe_stale", {"stale_clause"}, "C-006", 11, "FM-06"),
    ("probe_sibling", {"sibling_refund"}, "C-012", 11, "FM-07"),
    ("probe_misreport", {"misreport"}, "C-008", 11, "FM-08"),
]


def main() -> int:
    utf8_stdio()
    from lab8.shapes import SHAPES

    for name, bugs, claim, seed, fm in PROBES:
        SHAPES.setdefault(name, make_shape(name, frozenset(bugs)))
        case = investigate(name, claim, seed)
        t, label = case["trial"], case["label"]
        print(f"\n== {fm} {name} {claim}@{seed}  lab8: {'PASS' if t['lab8_pass'] else 'FAIL'} ({t['lab8_reason']})")
        for i, e in enumerate(t["events"], 1):
            print(f"  {i:>2} {e.get('kind', '?'):<18} {json.dumps(e.get('payload'), ensure_ascii=False)[:130]}")
        print(f"  ledger refund_vnd={t['snapshot'].get('refund_vnd')} label={label.get('refund_vnd')} "
              f"unexpected_rows={t['unexpected_rows']} reply_blob={t['blob'][:90]!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
