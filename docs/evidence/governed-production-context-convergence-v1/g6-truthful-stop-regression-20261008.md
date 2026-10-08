# N1 G6 truthful-stop regression checkpoint

Captured 2026-10-08 after the `285e49aeb4fc3da85db3ab9b13fa31b4e1e9bb50` exact-source image was built. The four tests below ran in disposable `watt-n1-pytest:20261008` containers against `/tmp/watt-n1-285e49a-source`, with regression database `spg_n1_regression_20261008_b` where integration persistence was needed. All four passed. They did not modify an original incident Work or the live N1 qualification database.

| Test | Established boundary |
| --- | --- |
| `tests/test_native_executor_contracts.py::test_kernel_requires_terminal_decision_after_three_ineffective_rounds` | Ineffective rounds have a bounded terminal decision. |
| `tests/test_native_executor_contracts.py::test_kernel_checkpoints_safe_provider_validation_fingerprint` | A rejected provider decision records safe validation details and terminates `UNABLE_TO_COMPLETE`. |
| `tests/integration/test_native_executor_runtime.py::test_worker_rejects_unbound_task_context_before_kernel` | Unbound Task context cannot reach the native kernel and leaves failed execution state. |
| `tests/integration/test_native_executor_runtime.py::test_production_worker_verification_failure_cannot_claim_result_ready` | A false-success kernel with no repository effect cannot claim `RESULT_READY` or a successful observed result. |

This is a scoped **regression PASS**, not a live G6 Work PASS. G6 still needs an independently admitted, irreparable isolated qualification Work with a persisted truthful stop, bounded no-retry observation and user-visible status. Existing G0/G3 stops were repairable context or input-shape cases and cannot substitute for that proof.
