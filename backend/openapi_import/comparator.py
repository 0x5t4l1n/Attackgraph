from __future__ import annotations

from dataclasses import dataclass

from backend.openapi_import.parser import OpenAPISpec


@dataclass
class SpecDiscrepancy:
    discrepancy_type: str  # undocumented_endpoint, unobserved_endpoint, method_mismatch, parameter_mismatch, auth_inconsistency
    endpoint_path: str
    method: str | None = None
    spec_value: str | None = None
    observed_value: str | None = None
    description: str = ""
    confidence: float = 0.5


class SpecComparator:
    """Compare OpenAPI spec against observed endpoints."""

    def compare(
        self, spec: OpenAPISpec, observed_endpoints: list[dict]
    ) -> list[SpecDiscrepancy]:
        """
        observed_endpoints: list of {"path": str, "method": str, "status_code": int|None}
        Returns discrepancies.
        """
        discrepancies: list[SpecDiscrepancy] = []
        spec_paths = {(e.path, e.method.upper()) for e in spec.endpoints}
        obs_paths = {(e["path"], e["method"].upper()) for e in observed_endpoints}

        for path, method in obs_paths - spec_paths:
            discrepancies.append(
                SpecDiscrepancy(
                    discrepancy_type="undocumented_endpoint",
                    endpoint_path=path,
                    method=method,
                    description=f"Endpoint {method} {path} was observed but is not documented in the API specification",
                    confidence=0.8,
                )
            )

        for path, method in spec_paths - obs_paths:
            discrepancies.append(
                SpecDiscrepancy(
                    discrepancy_type="unobserved_endpoint",
                    endpoint_path=path,
                    method=method,
                    description=f"Endpoint {method} {path} is documented but was not observed during testing",
                    confidence=0.6,
                )
            )

        return discrepancies
