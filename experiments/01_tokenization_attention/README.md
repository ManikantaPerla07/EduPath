# Practical 01: Tokenization and Scaled Dot-Product Attention Visualization
**Academic Subject:** CSE473 — Major Project\
**Initiative:** UN SDG 4 — Quality Education\
**Project:** EduPath — Personalized Tutoring Agent

---

## 1. Problem Statement & Learning Objectives
Language models do not process raw text strings directly; they process sequences of discrete numerical tokens mapped into continuous vector spaces. When computing contextual representations, the self-attention mechanism determines which parts of the input sequence are most relevant to each other.

### Learning Objectives:
1. Understand tokenization, vocabulary mapping, and token ID generation.
2. Formulate the Query ($Q$), Key ($K$), and Value ($V$) linear projections.
3. Compute Scaled Dot-Product Attention:
   $$\text{Attention}(Q, K, V) = \text{softmax}\left(\frac{QK^T}{\sqrt{d_k}}\right)V$$
4. Visualize attention weights as an attention map and interpret contextual relevance.

---

## 2. Core Mathematical Concept
For an input sequence of tokens with embedding dimension $d_{\text{model}}$ and sequence length $N$:
1. $Q = X W_Q$, where $W_Q \in \mathbb{R}^{d_{\text{model}} \times d_k}$
2. $K = X W_K$, where $W_K \in \mathbb{R}^{d_{\text{model}} \times d_k}$
3. $V = X W_V$, where $W_V \in \mathbb{R}^{d_{\text{model}} \times d_v}$
4. Raw alignment scores: $S = Q K^T \in \mathbb{R}^{N \times N}$
5. Scaling factor $\frac{1}{\sqrt{d_k}}$ prevents dot-product values from growing excessively large in high dimensions, which would push softmax into regions with vanishingly small gradients.
6. Attention matrix: $A = \text{softmax}\left(\frac{S}{\sqrt{d_k}}\right)$ where each row sums to $1.0$.
7. Contextual output: $O = A V \in \mathbb{R}^{N \times d_v}$.

---

## 3. How to Run
```bash
python experiments/01_tokenization_attention/experiment.py
```
Dependencies: Pure Python 3 + `numpy`. No GPU or paid APIs required.

---

## 4. Key Observations & Results
- Punctuation and subwords receive distinct token IDs.
- In the attention matrix, each row $i$ represents token $i$'s distribution of focus across all tokens $j$ in the sequence.
- Scaling by $\sqrt{d_k}$ ensures numerical stability in the exponential sum of softmax.

---

## 5. Limitations & Distinctions
- **Toy vs Pre-trained Model:** This experiment uses synthetic projection matrices $W_Q, W_K, W_V$ to illustrate the exact algebraic mechanics without needing a 7-billion parameter transformer download.
- **Production Context in EduPath:** EduPath uses Google Gemini Embedding 2 ($d=768$) for vector embeddings and pgvector for semantic cosine retrieval over curriculum chunks.

---

## 6. Interview Preparation Q&A
- **Q: Why do we divide by $\sqrt{d_k}$ in scaled dot-product attention?**\
  *A:* For large projection dimensions $d_k$, the dot products grow large in magnitude, driving the softmax function into regions with extremely small gradients (gradient saturation). Dividing by $\sqrt{d_k}$ preserves unit variance assuming $Q$ and $K$ components are independent random variables with zero mean and unit variance.
- **Q: What is the computational complexity of standard self-attention?**\
  *A:* $O(N^2 \cdot d)$, where $N$ is sequence length and $d$ is embedding dimension. The quadratic dependence on sequence length $N^2$ comes from the $QK^T$ matrix multiplication.
