# N1 G1 — new Candidate Human Integration Authorization review

Captured 2026-10-08 from isolated ECS PostgreSQL, Work Git, exact downloaded artifact bytes and current APIs. **No authorization or Delivery Acceptance is recorded by this review.** Runtime source is `0d4835353dbdb38abd6abfc19127b84eb5544475`; all four isolated runtime roles use image `sha256:64289d0a086ecf03efb2dae24ab036bd83906905e00fd71fa30fc51feb160709`.

| Identity | Exact value |
| --- | --- |
| Product / new Work | `252cce32-842b-4da7-b998-3ca04237c501` / `044f0268-f9cc-5663-a145-ea4d30b8e5bb` |
| PWU / run | `6f7c9329-8e9f-4ccd-b69b-4511529bac05` / `6f32fe5b-1450-49b4-8ee8-3632be67882f` |
| Sealed Candidate | `695cc730-849a-5dce-88da-c62c19c9f6b8` |
| Candidate fingerprint | `481e481d6f68936f149541f4c8a4b3e5551a4fec318de88deca4b73d92ae7ff7` |
| Exact file | `docs/n1-g1-lineage.md`, 2,020 UTF-8 bytes, SHA256 `925a7ea9e6b0125c59b3537c19e50073d44e42c60d1e72d2765540e07aa9fbce` |
| Git source → Candidate | `8e6a42995b5192c3dc8502ec844e5ad97a4b75fe` → `bda800eafa1cf720d6c0f9ade31170608e9d2912`; Candidate tree `178dc6e1df7ca50122d6b003c8ddac4f349e01ce` |
| Verification | `e0b16874-f96f-5e38-964b-73301e4bc3c8` = **PASS**, exact path, CREATE, nonempty UTF-8, ordered H2 sections and all four literal markers |
| Guardian | `NOT_STARTED`, `required=false`, zero findings; no Guardian PASS is claimed |
| Human authority | Zero Candidate authorization records; no integration, Runtime Commit, Manifest or Delivery Acceptance |

## Admitted Work Contract versus exact Candidate

| Required item | Observed result |
| --- | --- |
| One new English Markdown file at `docs/n1-g1-lineage.md` and no other changed file | PASS: immutable Git diff and Verification `exact_path_only=true`, `operation_matches=true` |
| Exactly three H2 sections in order: Purpose, Assumptions, Verification Checklist | PASS: exact blob has those three H2 headings only; Verification `section_order_matches=true` |
| Explain the repair purpose, assumptions and checks | Present in the respective three sections; checklist items are review prompts, not claims that Human acceptance occurred |
| Cite original Work `ae8530f0-1f28-55f7-aea6-e79b13c7fabd` | Present verbatim in exact blob and nonempty PWU `required_markers` |
| Cite original Semantic IR `9a88e343-6c62-5b30-af81-83594b03e171` | Present verbatim and independently required |
| Cite governance IDs `f4a91c10-1d27-57c5-9617-2220b916b33b` and `efb0a35b-a549-4f3e-ae94-9fcf75d68724` | Both present verbatim and independently required |
| Missing any identifier must fail | Exact-marker verifier checks each against the Git blob; new isolated negative Candidate regression omitting the Semantic IR ID returns `required_markers_present=false` and overall FAIL; reversed H2 order also FAIL |
| Identifiers are content citations, not source selectors or approval | Candidate says this explicitly; admitted source is the separate exact managed Work Git revision above |
| No application code, deployment or publication | Only the document was added in isolated Work Git; zero integration/Manifest/deployment records and no production business endpoint effect observed |

## Effect of a future precise Human Integration Authorization

An explicit `AUTHORIZE` decision for **this Candidate ID and fingerprint** would persist a Candidate-scoped Human decision in isolated PostgreSQL. On subsequent Work advancement, Watt would prepare a repository integration effect, compare-and-swap the **isolated Work repository** accepted branch from the exact source revision to the Candidate commit, observe convergence, and create a trusted source baseline and Runtime Commit. These are durable isolated Git and database writes on the ECS. They do **not** update `/data/watt/runtime/source`, production main, or the production business environment.

Human **Integration Authorization** permits this exact Candidate to enter trusted runtime/source lineage. It is separate from **Delivery Acceptance** of a later exact Document Package Manifest. No Manifest exists yet; its fingerprint cannot be approved in advance. A further Human accept/reject decision will be needed after integration and Manifest creation. The historical sealed Candidate `7d410081-4319-5529-a12e-ce844f9d9ac2` is outside this authorization request.
