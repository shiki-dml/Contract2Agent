# Paper Card: BLT-DP-FTRL
Source title: A Hassle-free Algorithm for Private Learning in Practice: Don't Use Tree Aggregation, Use BLTs
Source URL: https://arxiv.org/abs/2408.08868
License: CC BY 4.0 via the arXiv license link.
Attribution: McMahan, Xu, and Zhang, 2024.
Derived note: This card paraphrases source metadata and abstract-level facts for file-reading examples; it is not the full paper.

Study focus: The paper studies practical private learning for on-device language models.
Deployment setting: The motivating setup combines federated learning with differential privacy through DP-FTRL.
Baseline mechanisms: The paper contrasts tree aggregation and matrix factorization variants of DP-FTRL.
BLT contribution: The paper extends Buffered Linear Toeplitz mechanisms to multi-participation scenarios.
Practical claim: BLT-DP-FTRL keeps tree aggregation's ease of use while approaching matrix factorization utility and privacy.
Evaluation context: The paper reports StackOverflow simulations and four on-device language model tasks in a production FL system.
Good Contract2Agent task fit: Use BLT-style examples for privacy_mechanism_selection, federated_training_privacy, and paper-grounded comparison tasks.
