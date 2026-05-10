# Paper Card: LongBench
Source title: LongBench: A Bilingual, Multitask Benchmark for Long Context Understanding
Source URL: https://aclanthology.org/2024.acl-long.172/
License: CC BY 4.0 under the ACL Anthology post-2016 policy.
Attribution: Bai et al., 2024.
Derived note: This card paraphrases source metadata and abstract details for file-reading examples; it is not the full paper.

Study focus: LongBench evaluates long-context understanding in bilingual, multitask settings.
Benchmark scale: LongBench includes 21 datasets across 6 task categories in English and Chinese.
Average length: The paper reports averages of 6,711 English words and 13,386 Chinese characters.
Task coverage: The benchmark covers single-doc QA, multi-doc QA, summarization, few-shot learning, synthetic tasks, and code completion.
Evaluation lesson: The benchmark is useful for testing whether a model can use long inputs rather than short snippets.
Good Contract2Agent task fit: Use LongBench-style examples for needle_in_corpus, summary_with_citations, and multi_file_qa tasks.
