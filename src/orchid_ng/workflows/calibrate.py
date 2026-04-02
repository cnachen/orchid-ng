from orchid_ng.domain import ExecutionResult


def prepare_execution_calibration(run_id: str) -> ExecutionResult:
    return ExecutionResult(
        run_id=run_id,
        status="planned",
        notes="Execution calibration is intentionally decoupled from the ideation workflow in v1.",
    )
