# REE reproducibility report

2026-09-09 · Software 0.2.0 · Reference 0.1.0

**PASS for the explicitly declared comparison.** This is not a byte-identical reissue of the v0.1.0
software or every export. No reference inputs or expected values were regenerated.

| Check | Expected / result |
| --- | --- |
| Frozen input canonical SHA-256 | fe448abfb48081e8335d778715881da9857c8669b53addc7decf4b3df883a93c |
| Reference dataset SHA-256 | 30ab2d817c01197c3bc2b83c9b8e3bdd0531c3422deb70cc9977704b615032de |
| Input fixture matches | PASS |
| Counts | 4 documents; 5 claims; 4 candidate events; 12 pending reviews |
| Map geometry | 2 point representations; 2 null; Noto marked representational |
| Sylhet occurrence time | Unknown, with competing location candidates retained |
| Reference files vs original Git baseline | Unchanged |
| Software version | Current 0.2.0; reference 0.1.0, explicitly reported |
| Raw current dataset hash | Different because actual field provenance records current software version |
| Comparison dataset hash | PASS after normalizing only transformation.ree_version in a comparison copy |
| Mutation detection | Test changing a claim statement still fails reference digest comparison |
| Saved run validation | PASS for complete inventory, counts, database/schema, category/link/geometry and provenance checks |

The original digest includes the software version embedded in transformation metadata. The comparison
copy changes that one string to 0.1.0 while stored outputs retain 0.2.0. It changes no source, text,
claim ID, event, place, date, assessment, configuration, evidence rule, input hash or target-field hash.
The CLI records raw_dataset_matches separately and names the tolerance in reproduction_check.json.
It must not be described as an exact raw-hash match across software versions. Install the preserved
v0.1.0 wheel if the original version's full raw digest is required.

New review HTML/JSON, acquisition checkpoints, timing and environment metadata are additional outputs.
Run IDs/timestamps and container-format binary encodings are not part of the original semantic digest.
CSV/JSON/GeoJSON have current programmatic checks. Parquet/GeoPackage and actual QGIS/R still require
current-environment validation; earlier successful Python GIS reads are historical evidence.

Run after installation:

```bash
ree reproduce flagship
ree validate --run RUN
```

Replace RUN with the printed directory. The release contains one verified frozen run under
`verified-example/`. Its own manifest inventories files and records installed package provenance.
`ree compare RUN_A RUN_B` helps inspect two complete runs. Saved-run mutation/replay requires its
original software version; validation remains read-only.

Live collection is a different operation. Source updates, temporal defaults, availability and query
budgets can change results. Cache hits retain their original retrieval time and response hash. Preserve
an entire live run for offline replay; do not promise that a new live query will recreate it. This audit
has no successful real USGS acquisition and does not convert a mocked test into such evidence.
