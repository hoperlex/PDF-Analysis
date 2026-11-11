# `findings` boundary

Finding stable identity, run-specific FindingObservation, review read models and evidence links.

Create subfolders/classes only when a real use case requires them. Keep internal APIs private by default.

## Citation reader and block findings

`citation_reader.read_verified_citations` reads a run's certified citation partitions. It takes the stage an observation may come from
from the observation's `grounding_kind`: a `text_span` observation comes from `text_analysis`; a `portal_block` observation (a block finding
of a `one_list` run, written by `publish_candidate_groups`) from `block_analysis` or `finding_merge`. A block observation has an empty
partition: no citation row, no required/stated value, a count of NULL or 0 and the category `drawing_discrepancy` or `cross_source`. The
reader returns it with a count of 0 and refuses any other shape of such a row. The run header, the pin, the profile, prompt bundle and
provider checks are the same for both kinds. `tests/unit/findings/test_citation_reader_block_vocabulary.py` keeps the reader's stage and
category lists equal to the publisher's.
