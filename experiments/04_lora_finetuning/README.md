# Practical 04: Low-Rank Adaptation (LoRA) for Parameter-Efficient Fine-Tuning
**Academic Subject:** CSE473 — Major Project\
**Initiative:** UN SDG 4 — Quality Education\
**Project:** EduPath — Personalized Tutoring Agent

---

## 1. Problem Statement & Learning Objectives
Full fine-tuning of modern Large Language Models (LLMs) requires updating billions of dense parameters, demanding immense GPU VRAM and incurring prohibitive compute costs that violate the project's ₹0 operating budget. **LoRA (Low-Rank Adaptation)** hypothesizes that updates during model adaptation have a low "intrinsic dimension".

### Learning Objectives:
1. Formulate the low-rank decomposition:
   $$W' = W_0 + \Delta W = W_0 + \frac{\alpha}{r}(B \cdot A)$$
   where $W_0 \in \mathbb{R}^{d \times k}$ is frozen, $B \in \mathbb{R}^{d \times r}$ is initialized to zeros, $A \in \mathbb{R}^{r \times k}$ is initialized with Gaussian noise, and rank $r \ll \min(d, k)$.
2. Prove parameter reduction metrics (>99% savings for standard 7B models).
3. Demonstrate gradient backpropagation targeting only adapter matrices $A$ and $B$.

---

## 2. Theoretical Formulation & Parameter Reduction
For a standard 7-billion parameter transformer ($d_{\text{model}} = 4096$, 32 attention layers, rank $r = 16$):
- **Full Fine-Tuning Attention Weights:**\
  $$32 \text{ layers} \times 4 \text{ matrices} \times (4096 \times 4096) = 2,147,483,648 \text{ parameters}$$
- **LoRA Adapter Parameters:**\
  $$32 \text{ layers} \times 4 \text{ matrices} \times 2 \times (4096 \times 16) = 16,777,216 \text{ parameters}$$
- **Reduction:** **99.22% reduction in trainable parameters!**

### Initialization Rule:
- Adapter $A \sim \mathcal{N}(0, \sigma^2)$
- Adapter $B = 0$
- This guarantees $\Delta W = B \cdot A = 0$ at the initial step $t=0$, meaning the model begins with the exact behavior of the base pre-trained model without random degradation.

---

## 3. How to Run
```bash
python experiments/04_lora_finetuning/experiment.py
```
Dependencies: Pure Python 3 + `numpy`. No GPU or paid APIs required.

---

## 4. Key Results & Observations
- In the simulation experiment, MSE loss on Python Q&A classification dropped by **92.29%** across 50 gradient descent steps.
- The base pre-trained weight matrix $W_0$ had **0.0000** change (strictly frozen).
- All task adaptation was captured in the low-rank delta matrix $\Delta W = \frac{\alpha}{r}(B \cdot A)$.

---

## 5. Distinction from Production Architecture
- **In EduPath Production:** The runtime operates on a ₹0 budget using in-context few-shot learning (`services/few_shot_prompting_service.py`) and RAG retrieval over curriculum materials via Google Gemini.
- LoRA remains an academic PEFT experiment to demonstrate how domain-specific local models can be fine-tuned if dedicated GPU infrastructure becomes available in the future.

---

## 6. Interview Preparation Q&A
- **Q: Why is matrix $B$ initialized to zero while $A$ is randomly initialized?**\
  *A:* If both were zero, gradients would vanish. If both were random, $\Delta W$ would be non-zero, corrupting the pre-trained weights prior to any training steps. Setting $B=0$ ensures $\Delta W = 0$ at $t=0$, preserving pre-trained knowledge until training updates begin.
- **Q: Does LoRA introduce inference latency?**\
  *A:* No. During deployment, the adapter weights can be pre-merged directly into the base weights: $W_{\text{deployed}} = W_0 + \frac{\alpha}{r}(B \cdot A)$, resulting in identical inference latency to the unadapted model.
