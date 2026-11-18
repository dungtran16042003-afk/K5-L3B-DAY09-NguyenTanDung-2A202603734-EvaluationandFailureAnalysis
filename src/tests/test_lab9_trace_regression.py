"""Regression test for docs/trace_case.md: seeded_regression C-002@11 fails at the ticket-driven
override (FM-03, event 3); the fixed shape on the same claim does not. Runs the real shapes."""
import pytest

pytestmark = pytest.mark.student


def _kinds(trial):
    return [e.get("kind") for e in trial["events"]]


def test_seeded_c002_fails_at_ticket_override_fixed_passes():
    from lab9.trace_case import investigate

    seeded = investigate("seeded_regression", "C-002", 11)
    fixed = investigate("fixed", "C-002", 11)

    s, f = seeded["trial"], fixed["trial"]
    assert not s["lab8_pass"] and f["lab8_pass"]
    # First wrong step: the 3rd event is the model_override carrying the ticket's 5-day claim (DB says 2).
    assert _kinds(s)[2] == "model_override"
    assert s["events"][2]["payload"] == {"delay_days": 5}
    assert "model_override" not in _kinds(f)
    # Consequence in the ledger: money moved for a claim that must be denied.
    assert s["snapshot"]["refund_vnd"] == 20000 and seeded["label"]["refund_vnd"] == 0
    assert f["snapshot"]["refund_vnd"] == 0 and f["result"]["status"] == "denied"


def test_seeded_c013_only_the_proposal_is_wrong():
    """C-013: outcome and reply are right, the first wrong step is the proposal (needs ProposalCorrect)."""
    from lab9.trace_case import investigate

    t = investigate("seeded_regression", "C-013", 11)["trial"]
    assert t["lab8_reason"] == "proposal_mismatch"
    assert t["snapshot"]["refund_vnd"] == 0 and t["result"]["status"] == "denied"
