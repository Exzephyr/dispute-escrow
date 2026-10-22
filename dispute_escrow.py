from genlayer import *

class DisputeEscrow(gl.Contract):
    payer: Address
    payee: Address
    amount: u256
    deadline: u64
    rubric_hash: str
    deliverable_hash: str
    status: str
    final_score: u8

    def __init__(self, payee: Address, deadline: u64, rubric_hash: str):
        self.payer = gl.message.sender_address
        self.payee = payee
        self.amount = gl.message.value
        self.deadline = deadline
        self.rubric_hash = rubric_hash
        self.deliverable_hash = ""
        self.status = "FUNDED"
        self.final_score = 0

    @gl.public.write
    def submit_deliverable(self, deliverable: str):
        assert self.status == "FUNDED"
        assert gl.message.sender_address == self.payee
        assert gl.message.timestamp <= self.deadline
        assert len(deliverable) > 0
        self.deliverable_hash = gl.keccak(deliverable.encode())
        self.status = "SUBMITTED"

    @gl.public.write
    def judge(self, rubric: str, deliverable: str):
        assert self.status == "SUBMITTED"
        assert gl.keccak(rubric.encode()) == self.rubric_hash
        assert gl.keccak(deliverable.encode()) == self.deliverable_hash

        prompt = f"""Evaluate deliverable against rubric. Return JSON only:
{{"verdict": "approve"|"reject"|"partial", "score": 0-100, "reasoning": "cite rubric"}}

RUBRIC: {rubric}
DELIVERABLE: {deliverable}"""

        def leader_fn():
            return gl.nondet.exec_prompt(prompt, format="json")

        def validator_fn(leader_result) -> bool:
            if not leader_result or "verdict" not in leader_result:
                return False
            if leader_result["verdict"] not in ("approve", "reject", "partial"):
                return False
            if not isinstance(leader_result["score"], int) or not (0 <= leader_result["score"] <= 100):
                return False
            if len(leader_result.get("reasoning", "")) < 10:
                return False
            v = gl.nondet.exec_prompt(prompt, format="json")
            if not v or v.get("verdict") != leader_result["verdict"]:
                return False
            return abs(v.get("score", 0) - leader_result["score"]) <= 15

        result = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
        assert result is not None
        self.final_score = result["score"]
        self.status = "JUDGED"
        self._settle(result["verdict"], result["score"])

    def _settle(self, verdict: str, score: u8):
        if verdict == "approve":
            gl.send(self.payee, self.amount)
        elif verdict == "partial":
            payee_amt = self.amount * score // 100
            gl.send(self.payee, payee_amt)
            gl.send(self.payer, self.amount - payee_amt)
        else:
            gl.send(self.payer, self.amount)
        self.status = "SETTLED"

    @gl.public.view
    def get_status(self) -> str:
        return self.status

    @gl.public.view
    def get_final_score(self) -> u8:
        return self.final_score
