# Engineering Constitution

1. Evidence before merge: every requirement maps to an automated check or named human review.
2. Least privilege: services, agents, CI jobs, and credentials receive only required permissions.
3. Contract stability: backward-incompatible API or event changes require versioning and a migration note.
4. Supply-chain integrity: dependencies are justified, locked, verified, scanned, and represented in an SBOM when applicable.
5. Human accountability: an engineer owns architecture, risk acceptance, review, and release.
6. Small batches: each task produces a reviewable, revertible increment.
