import pytest
from unittest.mock import patch
from dispute_escrow import DisputeEscrow
import genlayer as gl

RUBRIC = "Must cite 3 issues with line refs."
DELIVERABLE = "Line 10 null check. Line 42 SQLi. Line 88 race."

def make(payee="0xPAYEE", deadline=9999999999, amount=1000):
    with patch("genlayer.gl.message") as m:
        m.sender_address = "0xPAYER"; m.value = amount; m.timestamp = 1000
        return DisputeEscrow(payee, deadline, gl.keccak(RUBRIC.encode()))

def test_deadline_reverts():
    c = make(deadline=1500)
    with patch("genlayer.gl.message") as m:
        m.sender_address = "0xPAYEE"; m.timestamp = 2000
        with pytest.raises(AssertionError):
            c.submit_deliverable(DELIVERABLE)

def test_wrong_sender_reverts():
    c = make()
    with patch("genlayer.gl.message") as m:
        m.sender_address = "0xSTRANGER"; m.timestamp = 2000
        with pytest.raises(AssertionError):
            c.submit_deliverable(DELIVERABLE)

def _submit(c):
    with patch("genlayer.gl.message") as m:
        m.sender_address = "0xPAYEE"; m.timestamp = 2000
        c.submit_deliverable(DELIVERABLE)

def test_approve():
    c = make(); _submit(c)
    r = {"verdict": "approve", "score": 95, "reasoning": "All 3 issues cited."}
    with patch("genlayer.gl.vm.run_nondet_unsafe", return_value=r), patch("genlayer.gl.send") as s:
        c.judge(RUBRIC, DELIVERABLE)
    assert c.get_status() == "SETTLED"
    s.assert_called_once_with("0xPAYEE", 1000)

def test_partial():
    c = make(); _submit(c)
    r = {"verdict": "partial", "score": 60, "reasoning": "Thin reasoning."}
    with patch("genlayer.gl.vm.run_nondet_unsafe", return_value=r), patch("genlayer.gl.send") as s:
        c.judge(RUBRIC, DELIVERABLE)
    calls = [x.args for x in s.call_args_list]
    assert ("0xPAYEE", 600) in calls and ("0xPAYER", 400) in calls

def test_reject():
    c = make(); _submit(c)
    r = {"verdict": "reject", "score": 10, "reasoning": "No refs at all."}
    with patch("genlayer.gl.vm.run_nondet_unsafe", return_value=r), patch("genlayer.gl.send") as s:
        c.judge(RUBRIC, DELIVERABLE)
    s.assert_called_once_with("0xPAYER", 1000)

def test_validator_rejects_short_reasoning():
    def v(r): return bool(r) and len(r.get("reasoning", "")) >= 10
    assert v({"verdict": "approve", "score": 90, "reasoning": ""}) is False

def test_validator_rejects_bad_score():
    def v(r): return isinstance(r["score"], int) and 0 <= r["score"] <= 100
    assert v({"verdict": "approve", "score": 150, "reasoning": "valid reason"}) is False
