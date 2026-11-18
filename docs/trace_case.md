# Trace case: từ trace tới quyết định sai đầu tiên

Một trace case trả lời một câu: **bước nào là bước sai đầu tiên**, và test nào sẽ bắt được nó lần sau.

```bash
cd src
python -m lab9.trace_case --shape seeded_regression --claim C-002 --seed 11
python -m lab9.trace_case --shape fixed --claim C-002 --seed 11   # đối chứng
```

Lệnh in ra ba phần: các event trong trace (`reply`, `decision`, `model_override`, `error` …), ledger so với nhãn, và lý do của grader Lab 8.

## Case 1 — `seeded_regression C-002@11` (FM-03 ticket_trust)

| Trường | Nội dung |
|---|---|
| Trial | `seeded_regression C-002@11`, run ID `E-seeded_regression-20261118-674a` (report `eval_seeded_regression.json`) |
| Triệu chứng | lab8 grader FAIL `status resolved != denied`. Reply "Đã, LogiX đã hoàn 20.000đ cho đơn O-202." nhưng ledger ghi `refund_vnd=20000, refund_count=1` — nhãn yêu cầu denied, 0đ (C-002 trễ 2 ngày < 3 ngày điều kiện clause) |
| Bước sai đầu tiên | Event 3 `model_override {"delay_days": 5}` — đặt lại delay DB=2 bằng số 5 trong ticket |
| Vì sao là bước *đầu tiên* | Event 1 handoff đúng, event 2 investigator trả đúng `delay_days: 2` của DB; chỉ từ event 3 dữ liệu fact bị ghi đè, dẫn đến quote 20.000đ (event 4) và hoàn tiền sai |
| Failure mode | FM-03 (ticket_trust — tin ticket hơn DB) |
| Đối chứng | `fixed C-002@11`: không có event `model_override`; event 3 quote `amount_vnd: 0, reason: no_entitlement` → denied đúng nhãn |
| Regression test | Grader `DbFactKept` (bắt event `model_override`) + metric `pass_rate`: FAIL trên `seeded_regression` (pass_rate 0.7143), PASS trên `fixed` (1.0); gate exit 1 với `pass_rate` Δ −0.271 CI [−0.500, −0.057] |
| Chưa chắc chắn | Trace không chứng minh vì sao LLM tin ticket (MockLLM): chỉ thấy hành vi ghi đè, không thấy "lý do" nội tại |

## Case 2 — `seeded_regression C-014@11` (FM-05 pre_deducted + FM-08 misreport)

| Trường | Nội dung |
|---|---|
| Trial | `seeded_regression C-014@11`, cùng run ID trên |
| Triệu chứng | lab8 grader FAIL `proposal_mismatch`. Reply "đã hoàn 120.000đ" nhưng ledger ghi 90.000đ (nhãn 120.000đ) |
| Bước sai đầu tiên | Event 4 `proposal {"amount_vnd": 120000}` — agent tự trừ 30.000 (prior refund C-HIST-515) trước khi gọi host; host trừ tiếp → 90.000 |
| Vì sao là bước *đầu tiên* | Event 3 quote đúng 150.000đ (SHIP-LATE-03 + DMG-04); việc trừ trước khi được host duyệt ở event 4 là phép tính đầu tiên sai |
| Failure mode | FM-05 (pre_deducted); reply đồng thời nói sai số ledger → FM-08 |
| Đối chứng | `fixed C-014@11`: không có event `refund_history`/`proposal`, hoàn đúng 120.000đ |
| Regression test | Grader `RefundAmountCorrect` (ledger 90.000 ≠ nhãn 120.000) + `ReplyLedgerMatch` (reply 120.000 vs ledger 90.000) |
| Chưa chắc chắn | Trace không cho biết tiền "mất" ở đâu trong host (host trừ lần nữa) — chỉ thấy chênh lệch 120.000 → 90.000 |

## Quy tắc

- Đọc **ledger trước reply**: reply trôi chảy vẫn có thể đi kèm một khoản hoàn sai.
- "Bước sai đầu tiên" phải dẫn số event cụ thể, không phải "agent bị nhầm".
- Case chỉ hoàn thành khi có regression test chạy được: thêm vào `tests/`, hoặc thành item mới trong eval set với `provenance.from_trace`.
