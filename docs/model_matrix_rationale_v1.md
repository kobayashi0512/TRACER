# Model matrix rationale v1

The paper should not compare only Qwen and Kimi. It should compare a **pre-specified, representative matrix** rather than claim an impossible evaluation of every open-weight model.

The minimum publishable pilot spans five roles:

| Role | Why it is needed | Initial candidate |
| --- | --- | --- |
| Tiny open general | Tests whether the deterministic gate protects against very limited model capacity | Qwen3 0.6B; Llama 3.2 1B |
| Small open general | Practical local-research baseline | Qwen2.5-VL 3B |
| Large open reference | Tests whether scale removes the failure mode | Qwen3-VL 30B-A3B |
| Biomedical open | Tests whether domain adaptation changes overclaiming, provenance, or abstention | MedGemma 4B, only after terms/runtime audit |
| Remote/closed reference | Represents high-capability deployed models | Kimi, only with exact API version/date and approved access |

Models are not the experimental units. Each frozen evidence packet is the unit for paired free-form versus gated comparison. The same packet, prompt version, seed policy, and decoding budget must be used within each model. The paper should report results by model and pooled across the pre-specified matrix; it must not choose a model subset after seeing outcomes.

Kimi is useful as a remote reference, but should not be called a “small model.” Its inclusion is contingent on recording the exact API model identifier, provider documentation date, request parameters, and data-use terms. A model whose version cannot be pinned is excluded from the confirmatory analysis.

The initial local runtime and model states are stored in `config/model_matrix_v1.json`. A model becoming downloadable does not itself make it part of the final study: the version, license, and one dry-run trace must all be frozen first.
