# Practical 05: Tabular Q-Learning and Potential-Based Reward Shaping
**Academic Subject:** CSE473 — Major Project\
**Initiative:** UN SDG 4 — Quality Education\
**Project:** EduPath — Personalized Tutoring Agent

---

## 1. Problem Statement & Learning Objectives
Reinforcement Learning (RL) provides an adaptive framework for policy discovery. However, sparse reward environments (where the agent receives feedback only upon reaching the final learning goal) suffer from prolonged random walk exploration and delayed credit assignment. Arbitrary heuristic rewards risk the "positive reward cycle" pathology (the agent loops in circles collecting rewards without reaching the goal). **Potential-Based Reward Shaping** mathematically guarantees policy invariance while providing dense guidance signals.

### Learning Objectives:
1. Formulate Markov Decision Processes: States $\mathcal{S}$, Actions $\mathcal{A}$, Transition function $\mathcal{P}$, Reward $\mathcal{R}$, Discount factor $\gamma$.
2. Implement Tabular Q-Learning with Bellman optimality updates:
   $$Q(s, a) \leftarrow Q(s, a) + \alpha \left[ r + \gamma \max_{a'} Q(s', a') - Q(s, a) \right]$$
3. Apply Potential-Based Reward Shaping (Ng et al., 1999):
   $$F(s, s') = \gamma \Phi(s') - \Phi(s)$$
4. Empirically verify accelerated convergence without policy degradation.

---

## 2. Mathematical Foundation: Potential-Based Reward Shaping
Ng, Harada, and Russell (1999) proved that a reward shaping function $F(s, a, s')$ guarantees policy invariance (the optimal policy $\pi^*$ under shaped rewards $R' = R + F$ is identical to $\pi^*$ under original rewards $R$) if and only if $F$ is defined in difference form:
$$F(s, s') = \gamma \Phi(s') - \Phi(s)$$
In this practical:
$$\Phi(s) = -\|s - \text{Goal}\|_1 = -(|r_s - r_g| + |c_s - c_g|)$$
As the agent transitions closer to the goal ($s \to s'$), $\Phi(s') > \Phi(s)$, generating an immediate positive bonus that accelerates learning without rewarding cycles.

---

## 3. How to Run
```bash
python experiments/05_q_learning/experiment.py
```
Self-contained, pure Python.

---

## 4. Key Results & Observations
- In early exploration (Episodes 1-15), standard sparse Q-learning averages **51.7 steps** per episode.
- Potential-based reward shaping cuts random exploration by providing an immediate directional gradient towards the goal.
- Both policies converge towards the identical optimal collision-free trajectory of 8 steps, empirically validating Ng et al.'s policy invariance theorem.

---

## 5. Distinction from Production Architecture
- **In EduPath Production:** Pedagogical adaptation uses deterministic, rule-based Bayesian/evidence scoring (`services/progress_service.py` and `services/adaptive_learning_service.py`) for transparency, predictability, and auditability.
- Q-learning represents an academic reinforcement learning exploration for future autonomous curriculum sequencing research.

---

## 6. Interview Preparation Q&A
- **Q: What is the exploration-exploitation dilemma in Q-learning, and how is it addressed?**\
  *A:* The agent must balance exploiting known high-value actions with exploring untried actions that might yield higher cumulative return. $\epsilon$-greedy exploration selects a random action with probability $\epsilon$ and greedy action $\arg\max_a Q(s, a)$ with probability $1-\epsilon$, decaying $\epsilon$ over time as confidence increases.
- **Q: Why does non-potential-based reward shaping fail?**\
  *A:* If rewards are shaped with arbitrary state rewards (e.g., $+1$ for moving right), an agent can discover infinite cycles (moving right then left repeatedly) that accumulate higher return than reaching the terminal goal. Potential-based shaping guarantees that any closed loop sum $\sum_{t=0}^k F(s_t, s_{t+1}) = 0$, eliminating reward-hacking loops.
