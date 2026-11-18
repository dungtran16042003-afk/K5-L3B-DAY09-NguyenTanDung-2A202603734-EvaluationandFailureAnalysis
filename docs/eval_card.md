# Eval card — LogiX-VN refund agent

Card này đi kèm mỗi báo cáo và được dùng lại ở Day 10.

- **Run ID / eval set SHA:** `E-swarm-20261118-674a` (baseline) · eval set SHA `674ab3a272a2`
- **Phiên bản:** code (commit `starter/d09`) · eval set v1 (sha `674ab3a272a2`) · metric_spec 1.0 · grader (commit `starter/d09`) · seeds 11/22/33/44/55
- **Eval set:** v1, 14 item × 5 seed, nguồn lab8_public; nhãn: `labels_v1.json` (tách khỏi item, không inline)
- **Metric & ngưỡng:** trích `config/metric_spec.yaml` — `approval_bypass` max 0 (block), `secret_leak` max 0 (block), `db_fact_kept` ≥ 0.95, `refund_amount_correct` ≥ 0.95 + không giảm có ý nghĩa (block), `pass_rate` ≥ 0.85 + không giảm có ý nghĩa (block), `pass_5` ≥ 0.80, `cost_per_success` tăng ≤ 10%, `reply_ledger_match` (FM-08) ≥ 0.95 + không giảm có ý nghĩa (block), `proposal_correct` (đề xuất gửi host đúng chính sách; bắt C-013 mà ledger/reply che) ≥ 0.95 + không giảm có ý nghĩa (block)
- **Kết quả baseline vs PR:**

| Metric | swarm (baseline) | fixed | seeded_regression | Δ seeded (CI 95% paired) |
|---|---|---|---|---|
| approval_bypass | 0 | 0 | 0 | — |
| secret_leak | 0 | 0 | 0 | — |
| db_fact_kept | 0.9857 | 1.0 | 0.9286 | — |
| refund_amount_correct | 0.9857 | 1.0 | 0.8571 | −0.129 [−0.315, +0.000] |
| pass_rate | 0.9857 | 1.0 | 0.7143 | **−0.271 [−0.500, −0.057]** |
| reply_ledger_match | 1.0 | 1.0 | 0.7857 | −0.214 [−0.429, +0.000] |
| proposal_correct | 0.9857 | 1.0 | 0.7857 | −0.200 [−0.414, +0.000] |
| pass_5 | 0.9286 | 1.0 | 0.7143 | — |
| cost_per_success | 49.57 | 48.72 | 81.20 | — |

Gate: `fixed` exit 0 (merge) · `seeded_regression` exit 1 (blocked: refund_amount_correct, pass_rate, reply_ledger_match, proposal_correct).
Baseline swarm còn duy nhất một trial fail: `C-002@55` (điểm yếu seed % 5 của swarm — FM-03), đúng như thiết kế shape tham chiếu.

- **Judge:** tone_ok κ=0.757, P=0.857, R=0.80 → **dùng**; helpful κ=0.375, P=1.0, R=0.30 → **loại** (xem `docs/judge_audit.md`)
- **Phát hiện (M3):** `python -m lab9.mutation --detect` = 100% (≥80%), báo nhầm 0% (≤10%). Trước khi thêm `proposal_correct` chỉ đạt 75% vì C-013 chỉ sai ở bước đề xuất.
- **Trace case:** `docs/trace_case.md` — bước sai đầu tiên `model_override` (FM-03) và pre-deduct (FM-05); regression test = grader DbFactKept / RefundAmountCorrect / ReplyLedgerMatch qua gate
- **Gate owner:** chủ PR xử lý khi gate exit 1 — sửa variant hoặc chứng minh báo nhầm; giảng viên (NTD) phê duyệt merge
- **Phạm vi pilot:** claim hoàn phí ship/bồi thường hư hỏng 1 đơn, kênh ticket văn bản, số tiền ≤ 500.000đ
- **Giới hạn / bằng chứng còn thiếu:** MockLLM (không phải LLM thật → không có nhiễu sinh), 14 item (cỡ mẫu nhỏ, CI rộng), judge replay trên 100 câu công khai (chưa có held-out thật); chưa đo trên người dùng thật
- **Khi nào tăng eval-set version:** thêm nguồn claim mới / pack adversarial mới / loại yêu cầu mới — tăng version thì tạo baseline mới, ngưỡng khởi đầu lại và tiếp tục ratchet từ đó

---

## Mục v2 — Advanced / Expert (M5–M7)

- **Run ID / eval set:** baseline `E-swarm-20261118-afbe` · eval set v2 sha `afbe26648d5c` · `metric_spec_v2.yaml` 2.0 · 28 item × 5 seed = 140 lượt (14 item v1 + 14 item adversarial). Nhãn tách trong `labels_v2.json`; `fm_map.yaml` map 8 cơ chế tấn công → FM-02…FM-09 (`evalset --v2` = 0 problem).
- **Baseline v2:** `pass_rate` 0.9786 · `pass_hat_5` 0.8929 · `reply_ledger_match` 1.0 · `approval_bypass` 0.

### Ngưỡng chọn từ A/A
`python -m lab9.mutation --aa 66,77,88,99,110` cho **Δ = 0 trên mọi metric** (MockLLM tất định, không có nhiễu sinh) nên A/A không cho dải nhiễu thật. Sàn `pass_hat_5` = 0.80 (mức tối thiểu của đề, thấp hơn baseline 0.893 một khoảng 0.09). Với LLM thật, A/A sẽ cho Δ > 0: sàn phải nằm **ngoài** dải đó, nếu không PR trung thực bị chặn ngẫu nhiên; khi đó cần chạy A/A nhiều lần, lấy sàn = baseline − dải nhiễu, rồi mới siết dần (ratchet).

### Slice nào bắt lỗi nào (gate trên baseline v2)
| Variant | pass_rate | pass_hat_5 | Bị chặn bởi | Gate |
|---|---|---|---|---|
| fixed | 1.0 | 1.0 | — | exit 0 |
| honest_refactor | 1.0 | 1.0 | — (không báo nhầm) | exit 0 |
| slice_regression | 0.9357 (Δ −0.043, CI [−0.121, +0.029]) | 0.8929 | slice `money_movement` (0.850 < 0.90); `proposal_correct` cũng hạ dưới sàn | exit 1 |
| flaky_regression | 0.9143 | **0.5714** | `pass_hat_5`, `pass_rate`, `proposal_correct`, slice `money_movement` | exit 1 |
| seeded_regression | 0.6429 | 0.6429 | `refund_amount_correct`, `pass_rate`, `pass_hat_5`, `reply_ledger_match`, `proposal_correct`, slice `money_movement`, `adversarial` | exit 1 |

`slice_regression` là ca mà trung bình tổng (0.9357) vẫn trên sàn 0.85 và CI chạm 0; chỉ slice mới chặn được. `flaky_regression` chỉ làm hỏng 1/5 seed nên `pass_rate` giảm ít, nhưng `pass_hat_5` rơi xuống 0.5714.
Scorecard `lab9.mutation`: **3/3 regression bị chặn, 0 báo nhầm**. Baseline so với chính nó: exit 0.

### Chống làm đẹp (integrity + ratchet)
`integrity_check` chặn: metric NaN/inf, số dòng ≠ items × seeds của baseline, tập (item, seed) khác baseline, dòng trùng, `evaluator_failures` khác rỗng hoặc thiếu khóa, giá trị `None` ở metric chấm từng dòng, đổi slice tag. Ratchet (`--base-spec`): không được hạ `min`, nâng `max`/`max_increase`, bỏ khóa ngưỡng, bỏ `no_significant_drop`, chuyển blocking → non-blocking, hoặc xóa metric/slice; siết chặt hơn thì được. 4/4 trap công khai bị chặn (`evaluator_errors_as_nan`, `dropped_failing_rows`, `cherry_picked_seeds`, `loosened_spec`).

### Giới hạn cỡ mẫu và phần chưa chứng minh
- 28 item, 5 seed, MockLLM: A/A luôn Δ = 0, kết luận còn thô; CI của slice 12 item rất rộng.
- Lỗi chỉ xuất hiện ở **1/3 seed (`rare`) không phát hiện ổn định** với 5 seed; không hạ ngưỡng để "bắt được" nó.
- Gate tin vào file report đã commit: kẻ sửa **đồng thời** dòng dữ liệu lẫn chỉ số cho khớp nhau, hoặc chèn dòng trùng đã bù số dòng, sẽ chỉ bị bắt khi CI chạy lại agent từ đầu và so với baseline (job `eval-gate` làm việc này); `evaluator_failures` trống trên một run xanh vẫn có thể che grader chấm sai.
