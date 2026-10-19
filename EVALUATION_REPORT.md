# RAG Report: Baseline Retrieval vs. Cross-Encoder Re-Ranking

## Setup

- **Document:** GDPR (Regulation (EU) 2016/679), 88 pages, split into 537 chunks of about 200 words with a 40-word overlap.
- **Bi-Encoder:** `BAAI/bge-base-en-v1.5`
- **Cross-Encoder:** `BAAI/bge-reranker-base`
- **LLM:** `google/gemini-2.5-flash-lite` through OpenRouter, temperature 0. Both pipelines use the same prompt, which tells the model to answer only from the given chunks and to say "Not found in context." otherwise.
- **Hardware:** CPU only.

The full prompt and the raw response of every LLM call quoted below are saved in `llm_prompts_and_responses.md` (and `.json`).

The test questions were picked by first checking retrieval ranks (without the LLM) and keeping cases that show each failure type. So they illustrate how the baseline fails; they don't measure how often it fails.

---

## 1. Architecture comparison

A bi-encoder encodes every chunk into a vector once, ahead of time. When a question comes in, only the question is encoded, and chunks are ranked by cosine similarity with it. The question and the chunk never see each other; each one is squeezed into a single vector on its own. This is fast, but it is not very robust. A sentence that allows something and a sentence that forbids it share almost all of their words, so their embeddings end up very close. Words like "not", "except" or "shall no longer" only move the vector a little, even though they flip the meaning.

A cross-encoder takes the question and the chunk together as one input. Every word of the question can attend to every word of the chunk, so the model judges relevance in context. A small part of the text, like an exception clause or a negation, can affect the score as much as it actually matters. The cost is that nothing can be precomputed: every (question, chunk) pair needs its own full pass through the model.

---

## 2. Qualitative and rank shift analysis

### Rank changes

| Query | Type | Chunk (where in GDPR) | Baseline rank | Re-ranked rank |
|---|---|---|---|---|
| Breach communication encryption exemption | Exception | 351 (Art. 34(3)) | #6 | **#1** |
| | | 350 (Art. 34(3)) | #5 | **#3** |
| Direct marketing objection | Negation | 314 (Art. 21(3)) | #4 | **#3** |
| | | 91 (Recitals 69–70) | #5 | **#2** |
| Maximum administrative fine | Keyword trap | 514 (Art. 83(5), €20M / 4%) | #6 | **#1** |
| When a DPIA is mandatory | Buried chunk | 353 (Art. 35(1)–(3)) | #6 | **#2** |
| Storage limitation | Re-rank regression | 84 (Recital 65, useful) | #3 | #5 (dropped out) |
| | | 78 (Recital 61, irrelevant) | #8 | #3 (pulled in) |
| Erasure refused because of a legal obligation | Exception (retention) | 306 (Art. 17(3)(b)) | #9 | **#2** |
| 72-hour breach deadline | Control | 347 (Art. 33(1)) | #1 | #1 |

In 5 of the 7 queries the chunk that actually answers the question was outside the baseline top 3 (ranks 4–9) and re-ranking moved it into the top 3.

### Answer 1 vs. Answer 2

**Exception: "When is a controller excused from communicating a personal data breach to the affected individuals because of encryption?"**
- **Baseline top 3:** Recitals 85–87. They repeat "personal data breach", "notify" and "communicate" many times but never mention the exemption.
- **Answer 1:** "Not found in context."
- **Answer 2:** gave the correct rule from Art. 34(3)(a). Communication is not required if protection measures such as encryption make the data unintelligible to anyone not authorised to access it.

The baseline answer was not wrong, but it was useless. The key clause sat at #5/#6, just outside what the LLM got to see.

**Negation: "Can a company continue sending marketing emails by claiming legitimate interest if a customer objects?"**
- **Baseline top 3:** general legitimate-interest recitals (Recital 47). One of them says direct marketing "may be regarded as carried out for a legitimate interest".
- **Answer 1:** repeated that marketing can be a legitimate interest and talked about balancing interests. It never said that an objection stops the processing, so a reader would come away thinking the company can probably continue.
- **Answer 2:** "No, a company cannot continue sending marketing emails if a customer objects." It quoted Art. 21(3): "the personal data shall no longer be processed for such purposes".

This is the clearest case of the baseline misstating the rule. The "allowed" passage and the "not allowed" passage look almost the same to the bi-encoder, and it picked the wrong one.

**Keyword trap: "What penalties can a company face for violating the regulation?"**
- **Baseline top 3:** Recital 148 (which literally talks about "penalties"), the factors used to decide a fine, and the €10M / 2% tier.
- **Answer 1:** said fines go up to €10,000,000 or 2% of turnover. That is the lower tier, so it understates the maximum by half.
- **Answer 2:** gave the correct maximum, €20,000,000 or 4% of worldwide turnover, and also mentioned the €10M tier for other infringements.

The word "penalties" pulled the general recitals up. The actual answer uses different wording ("administrative fines up to 20 000 000 EUR"), and only the cross-encoder connected the two.

**Buried chunk: "When must a controller carry out a data protection impact assessment?"**
- **Baseline top 3:** Recitals 84 and 90, plus the end of Art. 34 with only the first line of Art. 35.
- **Answer 1:** gave the general "likely to result in a high risk" rule with a vague list taken from the recitals.
- **Answer 2:** gave the same rule plus the three cases where Art. 35(3) makes the assessment mandatory: automated evaluation and profiling with legal effects, large-scale processing of special categories of data, and large-scale monitoring of public areas.

So the baseline left out the most specific part of the answer, because the chunk holding the list was at #6.

**Re-rank regression: "In what circumstances can personal data be retained longer than originally required?"**

I kept this case on purpose, because re-ranking made things worse here.
- **Baseline:** already had the right chunk (Art. 5(1)(e)) at #1. Its third chunk was Recital 65, which lists other lawful reasons to keep data (legal obligation, public interest, legal claims and so on).
- **Re-ranking:** swapped that chunk for Recital 61, which is about informing the data subject and has nothing to do with retention.
- **Effect:** Answer 1 listed both the archiving exception and the extra retention grounds. Answer 2 only had the archiving exception.

So the cross-encoder is not always right. It can push out a useful chunk in favour of one that only looks relevant.

**Exception (retention): "Can a controller refuse an erasure request because a law obliges it to keep the data?"**

This is the same retention topic as the case above, but here re-ranking does what it should.
- **Baseline top 3:** the start of Art. 17(1) (the reasons a controller *must* erase data) and two recitals on data portability. The exception in Art. 17(3) sat at #9.
- **Answer 1:** said "Yes", but for the wrong reason. It took Art. 17(1)(e), "the personal data have to be erased for compliance with a legal obligation", which is a reason the controller has to *delete* data, and twisted it into a reason to *keep* data.
- **Answer 2:** said "Yes" and gave the real basis: Art. 17(3)(b), where erasure does not apply if processing is needed to comply with a legal obligation.

The conclusion happened to match, but Answer 1 misstated the rule. Someone relying on it would cite the wrong clause, one that says the opposite.

**Control: "What is the maximum time limit for notifying the competent supervisory authority after becoming aware of a personal data breach?"** Both pipelines had Art. 33(1) at #1 and both answers correctly said 72 hours.

**Hallucination.** The LLM never invented a rule in these tests. Because the prompt forces it to stay inside the context, a missing chunk showed up in three ways:
- a refusal (exception case);
- a misleading answer built from the wrong passages (negation and keyword trap);
- an incomplete answer (buried chunk);
- the right conclusion with the wrong legal reason (retention exception).

---

## 3. Latency

Each of the 7 queries was run 10 times through both stages, on CPU. LLM time is not included because it is the same for both pipelines.

| Stage | Median (ms) | Mean (ms) | Min (ms) | Max (ms) |
|---|---|---|---|---|
| Pipeline 1: embed query + cosine search (top 10) | 56.2 | 57.3 | 49.9 | 75.6 |
| Re-ranking: cross-encoder on 10 pairs | 1760.5 | 1991.1 | 1534.0 | 3136.8 |
| Pipeline 2 total | 1824.2 | 2048.4 | 1588.8 | 3191.1 |

Pipeline 2 is about **32× slower** (median). The absolute times change between runs depending on how busy the machine is (an earlier run gave about 39 ms vs. 1220 ms), but the ratio stays around 30×.
- **Baseline:** the chunk vectors are already computed, so it only encodes one short question and does one matrix multiplication.
- **Cross-encoder:** has to run the full model 10 separate times, once per (question, chunk) pair, and each pair can be up to 512 tokens long.

On a GPU the re-ranking step would be much faster, but it would still be the slowest part of retrieval.

---

## 4. Scaling question

For the same reason, the cross-encoder can't be used as the first stage. Its scores can't be precomputed, so every chunk would have to go through the model together with the question at query time.

I measured this by scoring all 537 chunks for one question. It took **107.2 s, about 200 ms per pair**. For a collection of 100,000 chunks:

100,000 × 0.200 s ≈ 19,960 s ≈ **333 minutes (about 5.5 hours) for a single question**

The bi-encoder has already embedded those 100,000 chunks offline, so at query time it still only needs one question embedding and a vector search, which takes milliseconds (here, about 60 ms for 537 chunks). That's why the two are combined: the bi-encoder cheaply narrows the collection down to 10 candidates, and the expensive cross-encoder is only used on those 10.
