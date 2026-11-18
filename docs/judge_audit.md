# Judge audit

Chạy: `python -m lab9.judge --csv <file> --audit 5`

| Tiêu chí | n | κ | Precision | Recall | Đạt FLOORS (κ≥0.6, P≥0.8, R≥0.7)? | Quyết định |
|---|---|---|---|---|---|---|
| tone_ok | 100 | 0.757 | 0.857 | 0.80 | Đạt | **dùng** |
| helpful | 100 | 0.375 | 1.0 | 0.30 | Không đạt (κ, R) | **loại** |

- tone_ok: confusion {tp 24, fp 4, fn 6, tn 66}; fail rate observed 0.28 → Rogan-Gladen corrected **0.30** (sens 0.8, spec 66/70).
- helpful: confusion {tp 9, fp 0, fn 21, tn 70}; fail rate observed 0.09 → corrected 0.30.

## ≥5 case audit thủ công
| # | Case | Judge nói | Người nói | Ai đúng? | Ghi chú |
|---|---|---|---|---|---|
| 1 | H-008 "Em đã hoàn tiền cho anh rồi nha, anh check giúp em." | PASS | FAIL | Người | Không nêu mã đơn, không số tiền — văn xuôi thân mật nhưng thiếu thông tin bắt buộc |
| 2 | H-017 "đã hoàn 25.000đ cho đơn O-606 rồi nha" | PASS | FAIL | Người | Số tiền sai; judge tone không đọc số — tiền phải chấm bằng code, không bao giờ bằng judge |
| 3 | H-029 "vui lòng chờ… không cần nhắn thêm" | PASS | FAIL | Người | Trả lời trôi, không giải quyết yêu cầu, chặn người gửi |
| 4 | H-042 "đã hoàn 120.000đ cho đơn O-808. Tiền về trong 3–5 ngày ạ." | FAIL | PASS | Người | Judge báo nhầm: câu chuẩn mực, thêm thời hạn hoàn tiền không phải lỗi |
| 5 | H-051 "LogiX đã refund 90.000đ cho đơn O-202 ạ." | FAIL | PASS | Người | Judge báo nhầm: từ "refund" tiếng Anh vẫn đúng nghĩa "hoàn tiền" |

Hành động sửa rubric judge tone: (1) không trừ điểm khi thêm thời hạn hoàn tiền / lời chào; (2) chấp nhận "refund" ≈ "hoàn tiền"; (3) bắt buộc nêu mã đơn + số tiền trong câu hoàn tiền; (4) số tiền trong reply không thuộc phạm vi judge — do metric `reply_ledger_match` chấm.

## Kết luận
- **helpful bị loại**: κ=0.375 < 0.6 và R=0.30 < 0.7. Ma trận nhầm lẫn {tp 9, fp 0, fn 21, tn 70}: judge gần như luôn nói PASS (91/100) — câu lịch sự, xin lỗi trôi chảy vẫn được chấm "hữu ích" dù tiền sai/không giải quyết (fn=21). Precision 1.0 chỉ vì judge hầu như không bao giờ nói FAIL. Dùng nó làm gate sẽ cho qua 70% trial lỗi.
- tone_ok đạt floors → dùng được cho tiêu chí văn phong; tỉ lệ lỗi cảm quan 0.28 hiệu chỉnh Rogan-Gladen thành 0.30.
- Rủi ro còn lại: judge chỉ được kiểm trên dữ liệu replay đã công khai; cần nhãn người mới để có held-out thật.
