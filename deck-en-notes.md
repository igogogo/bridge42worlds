# Discovery Machine — Speaker Notes & Technical Reference
### Companion document to `deck-en.html` (7 slides)

*Every number in the deck is a measurement on our own data, taken between 9 and 13 August 2026.
This document gives, per slide: what it is for, what to say, the technical detail behind it,
and the questions to expect.*

---

## Slide 1 — Title

**Purpose.** Establish that this is an engineering architecture, not a demonstration.

**Say.** “We built an orchestrated multi-model system. The domain shown is science, but
nothing in the architecture is domain-specific — the same stack applies wherever there is
a large document corpus and the question is what is *missing* rather than what is present.”

**Do not say.** Anything implying we have made discoveries. We have not, and slide 5 states
this deliberately.

**Backing facts.**
- Working prototype: multilingual science publication, 3 809 analysed papers, 5 languages
  (ru / en / es / ar / fr), automated nightly pipeline in production.
- Vector field: 1 556 983 arXiv abstracts, physics and adjacent natural science, 1991–2026.
- The four analogies are not decoration. Each is accurate about one thing and stated,
  in the companion material, to be wrong about another.

---

## Slide 2 — Problem and reframe

**Purpose.** Reframe the objective and immediately expose the hard limit — before the
audience finds it.

**Say.** “The attractive idea is to look for empty space in the embedding. That idea is
provably dead, and not for want of data.”

### The reframe

The original objective was **comparative**: our corpus against the world corpus, two
densities over the same partition. “We have zero works here” is a fact — it is either
true or false, and it needs no statistical defence.

The new objective is **counterfactual**: one density, and a claim that its value is lower
than it *should have been*. Those words have no referent in the data. A null model must be
supplied by hand, and the entire content of any result depends on how honestly it is built.
This is the single most important conceptual point in the deck.

### The density wall — arithmetic

| quantity | value |
|---|---|
| formal dimension of the embedding | 1024 |
| intrinsic dimension (Levina–Bickel MLE, stable for k = 10…80) | ≈ 34 (our corpus) / 41.5 (arXiv sample) |
| points per axis at N = 1 556 983, d = 40 | **1.43** |
| shrinkage of nearest-neighbour distance when the corpus doubles | **2%** (2<sup>−1/34</sup>) |
| corpus multiplier required to halve neighbour distance | **2<sup>34</sup> ≈ 1.7 × 10<sup>10</sup>** |

Reference for the underlying phenomenon: Beyer, Goldstein, Ramakrishnan & Shaft, *When Is
“Nearest Neighbor” Meaningful?*, ICDT 1999 — distance concentration in high dimension.

**Consequence.** Absolute emptiness is not observable in this space and never will be.
Waiting for more data is not a strategy. Three observable signals replace it: **frontier**,
**bridges**, **temporal stalls**.

### The live example

Our own pipeline queried only `astro-ph` for two years — a default set once and thereafter
invisible, because nothing from the excluded sections ever arrived to remind anyone.
The map surfaced it in one pass. With no date restriction the top drilling target was
`cond-mat/0509330` — Novoselov & Geim, *Two-Dimensional Gas of Massless Dirac Fermions in
Graphene*, the Nobel-winning paper. Our coverage of graphene: **zero papers**.

**Expect.** *“Isn’t this just clustering?”* — No: clustering describes what exists.
The map compares two densities over a partition built on the world corpus, and reports
where one is zero while the other is not.

---

## Slide 3 — Architecture

**Purpose.** Show the layering and why merging layers destroys the system.

**Say.** “Facts live in the environment, where they are checkable and refreshed daily.
Optics live in the weights. Reasoning lives in the language model. Put facts into weights
and the model invents them with no way to check. Ask the vector to rank and it cannot —
we violated that rule four times before accepting it.”

### Layer detail

**Environment.** Append-only `float16` memmap store, 1 556 983 × 1024, 3.19 GB (2.97 GiB).
Key-addressable with last-write-wins semantics, so updating one work is an append, never a
rewrite. Content-verifiable: a separate tool re-embeds random rows and compares against
what is stored — file lengths do not prove correctness. Brute-force scan of the full field
is 32 s for a single query and **1.5 s per query when batched twenty at a time** — the cost
is disk read, not arithmetic, so no ANN index is required at this scale.

**Compass.** BAAI/bge-m3: XLM-RoBERTa-large backbone, 568M parameters, 1024-dimensional
dense head, 8192-token context, MIT licence. Chosen over higher-scoring alternatives on
three grounds: Arabic retrieval (MIRACL nDCG@10 **78.4**, above 7B-class e5-mistral at 73.3),
permissive licence, and measurement invariance — swapping the encoder invalidates the map,
the intrinsic-dimension estimate, and every threshold derived from them.

**Reasoning.** Qwen3-Reranker-8B as cross-encoder; DeepSeek-V3.1 for generation and judging.

**Orchestrator.** Routing, state, and the explicit human decision points.

### Why a registry of domain compasses, not one model

A generic encoder places a genuinely related paper at **rank 2 704 of 918 297**; only 11.2%
land in the top 100. A single model knows everything a little and nothing sufficiently.
Domain optics do not *add* to generic optics — within their domain they *replace* them.
Therefore the number of compasses equals the number of domains, and each carries its own
version, its own evaluation, and its own owner. Updating the clinical compass must not
break the subsurface one.

### The privacy statement — deliver it unprompted

“De-identified vectors” are **not** anonymous. Embedding inversion recovers substantial
source text (Song & Raghunathan, 2020; Morris et al., *Text Embeddings Reveal (Almost) As
Much As Text*, 2023). Mitigations we implement:

- contribute **aggregates** — region centroids and counts — rather than per-document vectors;
- reduce dimensionality before sharing: PCA 1024 → 256 retains **99.4%** of true neighbours
  when the shortlist is re-scored exactly against full vectors held privately
  (single-stage without re-scoring: 70.3%; naive truncation: 48.8% — bge-m3 is not a
  Matryoshka model, and we verified that rather than assuming it);
- keep full vectors inside the perimeter; export queries, not the field.

Correct phrasing: *disclosure is reduced, not eliminated; the level is selected per data class,
and the cost of each option is calculable.*

---

## Slide 4 — Method stack

**Purpose.** Demonstrate depth, and — more importantly — that failed methods are discarded.

**Say.** “The right-hand column is the point. Four of these are dead, and we killed them
ourselves, with controls rather than taste.”

### Production components

| component | detail |
|---|---|
| **Map** | Spherical k-means, 600 regions, fixed seed. Partitioned on the **world** corpus. Partitioning on one’s own corpus produces regions centred on one’s own topics and therefore 100% coverage by construction — a self-fulfilling result. |
| **Selection** | Two stages. The bi-encoder removes “already covered” and “off-profile”; the cross-encoder ranks by interest. Measured over 20 production days and 153 picks: the reranker’s top half retains **82%** of an expensive LLM’s selections against **52%** for a random half. Loss is 18%, i.e. roughly one pick in 5.6. |
| **Hubness** | In 1024 dimensions some concepts become neighbours of everything: `instanton`, `squeezed_state`, `quintessence` had mean corpus similarity 0.546 against a median of 0.475. Full mean-similarity subtraction fixes the tail but destroys the head — the top tag for a gravitational-wave paper became `antennas`, and cited-pair separation fell from AUC 0.787 to 0.676. Correction is therefore applied **only to ranks below the first**. |

### Fine-tuning specification (blocked on data, not on compute)

LoRA r = 16, α = 32, dropout 0.05, on `query` / `key` / `value` / `attention.output.dense` —
**3 145 728 trainable parameters, 0.55% of the model**. The 256M-parameter embedding table
(45% of the model, carrier of 100+ languages) is frozen absolutely. Loss: InfoNCE
(MultipleNegativesRankingLoss) via GradCache at effective batch 1024, τ = 0.05 rather than
the factory 0.02 — a harder temperature collapses neighbourhoods into near-duplicate
detection, and this system needs broad, meaningful neighbourhoods. Precision bf16: fp16
requires loss scaling, and loss scaling combined with GradCache’s cached logit gradients
produces NaN. Static memory 1.19 GB; batch 128 fits in 24 GB with gradient checkpointing.

**Blocker, stated first.** 2 102 domain pairs exist (232 direct citations + 1 870
bibliographic couplings at ≥3 shared references). Between 150 000 and 200 000 are required.
Training on two thousand is not training. The unblocking step is citation-graph ingestion,
which costs time and not money.

### Discarded, with reasons

- **Persistent homology.** `ripser`, Betti numbers, calibrated against sphere, torus and
  Klein bottle point clouds — the instrument distinguishes them correctly. But our corpus was
  projected to 3–4 dimensions, and projection destroys topology by construction. The result
  validates the tool, not the claim. Concede this immediately if raised.
- **δ-hyperbolicity.** Gromov four-point condition. The synthetic tree baseline proved
  indistinguishable from random noise at d = 1024 — random directions are near-orthogonal
  and branching is erased by dimension. Instrument failure, reported as such.
- **Geometric bridge ranking.** Four threshold-based definitions of “between two regions”
  produced 80% of the corpus, then zero, then zero again. Thresholds do not survive distance
  concentration. Working version: geometry proposes candidates cheaply, the model judges.

---

## Slide 5 — Validation

**Purpose.** Show evaluation discipline. This is what separates the work from a demonstration.

**Say.** “Every claim has a control. And the honest line is the last one.”

### Controls are built into the instruments

- **Blind A/B with a sealed key.** Two shortlists printed unlabelled; the key is written to
  a separate ignored file and revealed only after scoring. Result: 7 of 8 days favoured the
  filtered shortlist. My own A/B choices split 3–3 by label, which is what an unbiased blind
  judgement looks like when a real effect is present. Single judge, and that judge authored
  the change — stated as a limitation; independent repetition requested.
- **Foreign-anchor control** in every reasoning-cycle run.
- **Known-positive calibration pairs** mixed into every judging batch. A judge that refuses
  even on pairs with hundreds of real intersecting works is broken, and this is visible
  immediately rather than inferred.
- **Baselines printed beside every result**: random half, random pair, foreign anchor.
- **An instrument that answers *always* is treated as broken.** Both extremes are equally
  uninformative: our first bridge-judging prompt refused 30 of 30, the second returned
  identical confidence for all 19 answers.

### What cannot be claimed

No confirmed discoveries. The gap-finding pipeline runs end to end, and its output cannot
presently be separated from plausible noise: the judge passes controls 8/8 and still returns
a template — “apply quantum simulators to astrophysics” appeared in 10 of 11 findings.
Falsification against the field did not discriminate either: claimed gaps sat at 0.60–0.68
similarity to their nearest real work, which is the ordinary similarity between any two
physics texts (random pair 0.451, cited pair 0.586).

**One experiment settles it.** Rebuild the field as of 2015, run the pipeline blind, compare
its outputs against what actually happened in 2016–2026. The data exists — the field spans
1991 onward — and it costs nothing but time. Until then the pipeline is presented as
mechanism, not as findings.

---

## Slide 6 — Cycle closure

**Purpose.** The strongest idea in the deck, and the one most likely to be remembered.

**Say.** “Chess engines work because a game has a terminal signal — win or loss. Exploratory
gap-finding had none, and that was the hole in every tree-search framing. Cycle closure
supplies it. We stopped asking the model whether something is *true* — it has no access to
truth — and started asking whether the chain *returns*.”

### Mechanism

From a real paper: three moves, each accepted **as fact** and never evaluated; then an
attempt to close back onto the origin. Closure is measured geometrically — how near the
closing statement lands to the starting point — not by the model’s own assertion.

This is formally Swanson’s A → B → C → A. Swanson’s 1986 result (fish oil / Raynaud’s
syndrome) rested on two complementary literatures that did not cite each other; the weakness
of the ABC model as usually implemented is that a chain of length two need not return, and
such chains are exponentially abundant. **The return requirement is what makes the search
selective.**

### First measurement — 9 games, cost $0.005

| | |
|---|---|
| closure to **own** anchor | **0.465** |
| closure to **foreign** anchor | **0.330** |
| judge declared closure, own anchor | 5 / 9 |
| judge declared closure, foreign anchor | **0 / 9** |

The same judge had previously assigned confidence 4-of-5 to all 19 answers in a row.
Here it refused nine times out of nine on a foreign anchor. That is discrimination.

### Conceded without being asked

Nine games. And closing statements sit closer to the corpus centroid (**0.581**) than to
their own anchor (0.465) — regression toward generic phrasing is present and measured.

---

## Slide 7 — Generalisation

**Purpose.** Generalise the pattern and close on a concrete ask.

**Say.** “The domain is interchangeable. What transfers is the pattern: a verifiable
environment, a registry of fine-tuned domain experts, an orchestrator, and evaluation
discipline with controls. That pattern applies to any orchestrated system whose method is
fine-tuned models.”

### Where the drilling analogy is exact, and where it breaks

Exact: decades of textual reports are effectively unsearchable because search is lexical and
vocabulary drifted — «поглощение промывочной жидкости» and “lost circulation” denote one
phenomenon and share no tokens. The field places them adjacent.

Broken: in science an empty region means “not studied”. In exploration it frequently means
**“drilled and dry”**, and that report is in the archive. The system must distinguish *not
drilled* from *drilled without result* — and negative results are the least well documented
data any operator holds. This is settled before a pilot, not after.

### Roadmap — measurement first, model second

1. Significance test on the 74 empty regions. With 3 723 of our works over 600 regions the
   expectation is ~6 per region; for a small region a zero arises by chance with probability
   around 15%. Until this is computed the list cannot be handed to a human as “74 addresses”.
   Free.
2. Temporal signals per region — the cheapest unused resource. Dates exist for all
   1 556 983 works. Free. *(Note: these are v1 submission dates, not journal publication
   dates — the difference is often a year.)*
3. Retrospective validation at a 2015 cut. Free, and decisive.
4. Citation-graph ingestion: 2 102 pairs → 200 000–500 000.
5. Compass fine-tuning. Success criterion fixed in advance: **median rank falls fourfold**.

### The ask

Not belief — a corpus. Four to six weeks from data handover to a coverage map with named
regions, addresses, and a completeness figure, delivered against criteria agreed before
the pilot begins.

---

## Anticipated questions

**“How is this different from RAG?”** RAG answers a question you asked, over documents it
retrieved. This answers a question nobody has asked yet: where the corpus is empty while its
surroundings are dense. RAG works with what is there; the map works with what is not.
They share vector search as a component and nothing else.

**“Why not train from scratch?”** Pre-training an XLM-R-large-class encoder is tens of
thousands of GPU-hours. Fine-tuning an open model is the correct engineering choice, not a
compromise.

**“Why not a graph neural network on the citation graph?”** Because the graph is known only
for the past. A paper posted yesterday has no citations and will have none for a year — and
recent work is exactly what matters. A text encoder works from day one. A graph model is the
right next step for retrospective analysis, not a replacement.

**“Why k-means, and why 600?”** Because a reproducible partition with a fixed seed can be
argued about. 600 regions give roughly 2 600 works per region. This is a genuine weakness:
the map depends on the number of regions, and stability of conclusions across 300 / 600 /
1200 has not yet been tested. Stated, not hidden.

**“How do you distinguish an unexplored niche from an impossible one?”** We do not, and the
instrument does not claim to. It reports “empty amid density”; a human decides. What the map
adds is that it **remembers the cause** of emptiness — two thirds of our own blind spots
resolved to a single decision made once and then forgotten.

**“Show me a discovery.”** We have none. We have a working pipeline, a measured coverage
map, and a first list of targets. Claiming otherwise would not survive the following
question, and this audience would ask it.

---

*Method note worth stating aloud: over four days our own verification instruments produced
false results nine times — the frontier measure twice, the tree baseline, a file parser, a
cosine threshold, the bridge measure three times, the judge twice. Each case is recorded in
the code beside its correction. This is not an admission of weakness; it is the only known
way to avoid building a machine that confidently displays what is not there.*
