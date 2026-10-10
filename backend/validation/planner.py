from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from backend.attack_paths.analyzer import CandidateAttackPath
from backend.graph_engine.engine import ApplicationGraph


@dataclass
class TestPlanItem:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    attack_path_id: str = ""
    hypothesis: str = ""
    evidence: list[str] = field(default_factory=list)
    required_accounts: list[str] = field(default_factory=list)
    preconditions: list[str] = field(default_factory=list)
    test_procedure: str = ""
    expected_secure_behavior: str = ""
    potential_insecure_outcomes: list[str] = field(default_factory=list)
    cleanup_steps: list[str] = field(default_factory=list)
    evidence_to_capture: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    status: str = "pending"


class TestPlanner:
    def generate_plans(
        self,
        attack_paths: list[CandidateAttackPath],
        graph: ApplicationGraph,
    ) -> list[TestPlanItem]:
        plans = []
        for path in attack_paths:
            target_lower = path.target_label.lower()
            impact_lower = path.potential_impact.lower()

            if "idor" in impact_lower or "{id}" in target_lower or "object" in impact_lower:
                plans.append(self._plan_for_idor(path))
            elif "privilege" in impact_lower or "role" in target_lower or "admin" in target_lower or "permission" in target_lower:
                plans.append(self._plan_for_privilege_escalation(path))
            elif "auth" in impact_lower or "bypass" in target_lower or "unauthenticated" in impact_lower:
                plans.append(self._plan_for_auth_bypass(path))
            elif "workflow" in impact_lower:
                plans.append(self._plan_for_workflow_abuse(path))
            else:
                plans.append(self._plan_generic(path))
        return plans

    def _plan_for_idor(self, path: CandidateAttackPath) -> TestPlanItem:
        target = path.target_label
        target_url = path.target_label
        return TestPlanItem(
            attack_path_id=path.id,
            hypothesis=f"Resource at {target} may be accessible by unauthorized users through direct object reference manipulation",
            evidence=path.observations,
            required_accounts=["User A (resource owner)", "User B (different role/account)"],
            preconditions=[
                "Two valid test accounts with different permissions",
                "User A owns at least one resource accessible through this endpoint",
            ],
            test_procedure=(
                f"1. Authenticate as User A\n"
                f"2. Create or access a resource at {target_url}, note the resource ID\n"
                f"3. Authenticate as User B (different role or account)\n"
                f"4. Request User A's resource ID using User B's session\n"
                f"5. Compare responses between authorized and unauthorized access\n"
                f"6. Try modifying User A's resource using User B's session (if applicable)"
            ),
            expected_secure_behavior="403 Forbidden or empty response when accessing another user's resource",
            potential_insecure_outcomes=[
                "User B receives User A's data",
                "User B can modify User A's resource",
                "Resource returned without ownership check",
            ],
            cleanup_steps=["Restore any modified test resources", "Revoke test sessions"],
            evidence_to_capture=[
                "Full HTTP request and response for both users",
                "Response status codes",
                "Response body comparison",
            ],
            limitations=[
                "Requires two valid test accounts",
                "Resource IDs must be predictable or enumerable",
                "Cannot test resources that require specific permissions to create",
            ],
        )

    def _plan_for_privilege_escalation(self, path: CandidateAttackPath) -> TestPlanItem:
        entry = path.entry_point_label
        target = path.target_label
        steps_desc = " → ".join([entry] + [s["label"] for s in path.intermediate_steps] + [target])
        return TestPlanItem(
            attack_path_id=path.id,
            hypothesis=f"A lower-privileged user can escalate to {target} through the path: {steps_desc}",
            evidence=path.observations,
            required_accounts=["Low-privileged user account", "Admin or higher-privileged account (for comparison)"],
            preconditions=[
                "Low-privileged test account with minimal permissions",
                "Knowledge of the expected privilege boundary",
            ],
            test_procedure=(
                f"1. Authenticate as the low-privileged user\n"
                f"2. Navigate to {entry}\n"
                f"3. Follow the path: {steps_desc}\n"
                f"4. Attempt to access {target} directly\n"
                f"5. Compare with the admin account's access to {target}\n"
                f"6. Check if intermediate steps can be skipped"
            ),
            expected_secure_behavior=f"403 Forbidden when low-privileged user attempts to access {target}",
            potential_insecure_outcomes=[
                f"Low-privileged user can reach {target}",
                "Intermediate authorization checks are missing",
                "Privilege level can be elevated through the workflow",
            ],
            cleanup_steps=["Verify no privilege changes persisted", "Reset test account permissions"],
            evidence_to_capture=[
                "Full HTTP request/response at each step",
                "Authorization headers present",
                "Status codes at each boundary",
            ],
            limitations=[
                "Requires knowledge of privilege hierarchy",
                "Some steps may require specific application state",
            ],
        )

    def _plan_for_auth_bypass(self, path: CandidateAttackPath) -> TestPlanItem:
        target = path.target_label
        return TestPlanItem(
            attack_path_id=path.id,
            hypothesis=f"Authentication can be bypassed when accessing {target}",
            evidence=path.observations,
            required_accounts=["Unauthenticated session", "Valid authenticated session (for comparison)"],
            preconditions=["Network access to the target endpoint"],
            test_procedure=(
                f"1. Send a request to {target} without any authentication credentials\n"
                f"2. Record the response status and body\n"
                f"3. Authenticate with valid credentials\n"
                f"4. Send the same request with authentication\n"
                f"5. Compare the two responses\n"
                f"6. Test with expired/invalid tokens"
            ),
            expected_secure_behavior="401 Unauthorized or 403 Forbidden without valid credentials",
            potential_insecure_outcomes=[
                "Endpoint returns data without authentication",
                "Endpoint accepts state changes without authentication",
                "Authentication check is client-side only",
            ],
            cleanup_steps=["No cleanup typically needed for read-only tests"],
            evidence_to_capture=[
                "Unauthenticated request and response",
                "Authenticated request and response",
                "Response status code comparison",
            ],
            limitations=[
                "Network-level authentication (VPN, WAF) may not be visible",
                "Authentication may be enforced at a load balancer or reverse proxy",
            ],
        )

    def _plan_for_workflow_abuse(self, path: CandidateAttackPath) -> TestPlanItem:
        entry = path.entry_point_label
        target = path.target_label
        return TestPlanItem(
            attack_path_id=path.id,
            hypothesis=f"Workflow from {entry} to {target} can be abused by skipping or manipulating intermediate steps",
            evidence=path.observations,
            required_accounts=["Valid test account with workflow access"],
            preconditions=[
                "Access to the workflow entry point",
                "Understanding of the expected workflow sequence",
            ],
            test_procedure=(
                f"1. Start the workflow at {entry}\n"
                f"2. Skip directly to {target} without completing intermediate steps\n"
                f"3. Replay requests from earlier steps with modified parameters\n"
                f"4. Attempt to perform {target} operation out of sequence\n"
                f"5. Check for state validation at {target}"
            ),
            expected_secure_behavior=f"Server rejects out-of-sequence requests to {target}",
            potential_insecure_outcomes=[
                "Workflow steps can be skipped",
                "State is not validated at each step",
                "Final operation succeeds without preconditions",
            ],
            cleanup_steps=["Reset workflow state if modified", "Clean up any created resources"],
            evidence_to_capture=[
                "Requests and responses at each step",
                "Out-of-sequence request results",
                "State tokens or session data",
            ],
            limitations=[
                "Workflow state may be complex to manipulate",
                "Some workflows may have irreversible steps",
            ],
        )

    def _plan_generic(self, path: CandidateAttackPath) -> TestPlanItem:
        entry = path.entry_point_label
        target = path.target_label
        return TestPlanItem(
            attack_path_id=path.id,
            hypothesis=f"Security boundary between {entry} and {target} may be insufficient",
            evidence=path.observations,
            required_accounts=["Appropriate test account(s)"],
            preconditions=path.preconditions or ["Access to the entry point"],
            test_procedure=(
                f"1. Access {entry}\n"
                f"2. Trace the path to {target}\n"
                f"3. At each step, verify authorization is enforced\n"
                f"4. Attempt direct access to {target}\n"
                f"5. Document any unexpected access"
            ),
            expected_secure_behavior="Authorization enforced at each step in the path",
            potential_insecure_outcomes=[
                "Intermediate authorization checks are missing",
                f"Direct access to {target} is possible",
            ],
            cleanup_steps=["Review and undo any changes"],
            evidence_to_capture=["Request/response pairs at each step", "Authorization decisions"],
            limitations=["Generic test - may need refinement based on application context"],
        )
