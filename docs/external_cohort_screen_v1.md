# External cohort screen v1

This is an exclusion and audit log, not an evidence table. A public single-cell dataset is not automatically an eligible ICI response-replication cohort.

| Accession | Public metadata observed | Decision | Reason |
| --- | --- | --- | --- |
| GSE78220 | One public FPKM matrix with 28 columns. Read-only header-to-SOFT audit matched all columns; 27 were pre-treatment pembrolizumab samples with 15 CR/PR and 12 PD, and one was on-treatment. | External bulk direction check only | Auditable baseline response association, but tumor bulk RNA cannot replicate a single-cell cell-state edge. The source metadata alone do not resolve whether labels such as Pt27A/Pt27B are independent participants. |
| GSE244983 | Four melanoma scRNA-seq samples: two progression/resistant lesions and two ICB-naïve samples | Context only | No audited pre-treatment responder/non-responder cohort; progression and naïve specimens cannot support baseline response replication. |
| GSE273718 | Temporal scRNA+TCR profiling across anti-PD-1, anti-CTLA-4, and combination therapy | Context only pending audit | Treatment mixture and currently unaudited patient-level baseline response mapping. |
| GSE211504 | Peripheral CD8 scRNA/TCR from two melanoma patients receiving checkpoint blockade | Context only | Peripheral compartment, two-patient sample size, and treatment heterogeneity. |

The registry admits GSE78220 only as `external_direction_check_only`; it remains locked to `same_measurement_replication_eligible: false`. The other three remain locked to `baseline_ici_response_association_eligible: false` and `same_measurement_replication_eligible: false`. None may produce a same-measurement cross-cohort replication edge without a future metadata audit and explicit version bump.

Sources: [GSE78220](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE78220), [GSE244983](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE244983), [GSE273718](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE273718), and [GSE211504](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE211504).
