# OpenStax Dataset, Licensing & Permission Audit — EduPath

**Course:** CSE473 — Major Project\
**Initiative:** Google Solution Challenge\
**Sustainable Development Goal:** UN SDG 4 — Quality Education\
**Lead Developer:** Perla Manikanta (Group G22)\
**Date:** November 14, 2026

---

## 1. Executive Summary & Compliance Status

The official CSE473 assignment allocation specifies the use of open textbooks from **OpenStax** for RAG-based educational retrieval.

In accordance with academic integrity and intellectual property standards, EduPath conducted an independent licensing and legal audit of the assigned OpenStax textbook. This audit revealed an **explicit contractual restriction prohibiting unauthorized LLM ingestion**.

| Requirement | Current Status | Compliance Action |
| :--- | :--- | :--- |
| **Assigned Textbook** | *Introduction to Python Programming* (1st Edition, OpenStax) | Audited license and terms of use |
| **Ingestion into Vector DB** | **BLOCKED — AWAITING WRITTEN PERMISSION** | No OpenStax text is scraped, embedded, or stored in Neon PostgreSQL |
| **Generative AI Ingestion** | **PROHIBITED WITHOUT WRITTEN PERMISSION** | No OpenStax passages are sent to Google Gemini prompts |
| **Production Knowledge Base** | **11 Original EduPath Notes (47 Chunks)** | 100% original authored curriculum (`rights_basis = 'original'`) |
| **External Reading Link** | **COMPLIANT & ACTIVE** | External reading link provided in Learner Resources UI |
| **Permission Request** | **DRAFTED & READY FOR SUBMISSION** | Formal application prepared for Rice University Licensing |

> [!IMPORTANT]
> **Defensible Academic Stance:** EduPath refuses to circumvent or violate open textbook licenses. We do not misrepresent original curriculum notes as OpenStax content, nor do we disguise OpenStax text via paraphrasing. OpenStax RAG ingestion remains an **external assignment-compliance blocker** pending written institutional authorization.

---

## 2. Textbook Details & Official Links

- **Book Title:** *Introduction to Python Programming*
- **Publisher:** OpenStax, Rice University
- **Edition:** 1st Edition (Published 2023–2024)
- **Primary Authors:** Kenneth A. Lambert, Martin Osborne
- **Official Textbook Link:** [https://openstax.org/books/introduction-python-programming/pages/1-introduction](https://openstax.org/books/introduction-python-programming/pages/1-introduction)
- **Official Preface & Attribution:** [https://openstax.org/books/introduction-python-programming/pages/preface](https://openstax.org/books/introduction-python-programming/pages/preface)
- **Permission Request Portal:** [https://riceuniversity.tfaforms.net/52](https://riceuniversity.tfaforms.net/52)

---

## 3. Textbook License & AI-Use Restrictions

While OpenStax textbooks are generally published under a **Creative Commons Attribution 4.0 International (CC BY 4.0)** license for human reading and classroom distribution, Rice University / OpenStax enforce specific proprietary terms regarding artificial intelligence:

### 3.1 Contractual AI Ingestion Prohibition
The official OpenStax attribution and terms page explicitly states:
> *"The OpenStax name, OpenStax logo, OpenStax book covers, OpenStax CNX name, and OpenStax CNX logo are not subject to the creative commons license and may not be reproduced without the prior and express written consent of Rice University.*
>
> *Further, this textbook may **not be used for large language model (LLM) training, fine-tuning, or ingested into generative AI tools or retrieval-augmented generation offerings without prior express written permission from Rice University**."*

### 3.2 Legal & Ethical Implications for EduPath
1. **Zero Unauthorized Ingestion:** Downloading the PDF, extracting its text, generating 768-dimensional embeddings via Google Gemini, and storing those chunks in `document_chunks` for LLM prompt augmentation constitutes automated generative AI ingestion.
2. **Current Permission Status:** As of November 14, 2026, **no written permission has been granted** to the EduPath student team.
3. **Engineering Decision:** OpenStax text has **NOT** been embedded or ingested into the production Neon database. The production database operates strictly on 11 original educational notes authored for EduPath (`rights_basis = 'original'`, `source_license = 'Original — EduPath project'`).

---

## 4. Formal Permission Request Draft

Below is the formal written permission request drafted for submission to the Rice University / OpenStax Intellectual Property Office via [https://riceuniversity.tfaforms.net/52](https://riceuniversity.tfaforms.net/52):

```
To: OpenStax Rights & Licensing Office, Rice University
Subject: Academic Permission Request: Educational RAG Tutoring Project (UN SDG 4 / CSE473)

Dear OpenStax Rights & Licensing Team,

I am writing to respectfully request permission to ingest selected chapters of "Introduction to Python Programming" (1st Edition) into an educational, non-profit academic prototype called EduPath.

1. Applicant Identity & Context:
- Lead Developer: Perla Manikanta
- Academic Context: CSE473 Major Project, Academic Evaluation Submission
- Initiative: Google Solution Challenge (UN SDG 4: Quality Education)
- Institutional Setting: Undergraduate Computer Science Degree Project

2. Nature of the System (EduPath):
EduPath is a personalized, non-profit AI tutoring companion designed to assist novice learners with beginner Python programming. It operates under a strict ₹0 operating budget, using Google's free-tier APIs and Neon serverless PostgreSQL.

3. Technical Use of Text:
- The text will NOT be used for pre-training or fine-tuning foundation weights.
- The text will be parsed into bounded pedagogical chunks (~150 words) with source metadata.
- 768-dimensional vector embeddings will be generated solely for similarity search.
- When a student asks a Python question, top-k chunks will be retrieved and supplied as read-only reference data to Google Gemini.
- All AI responses strictly cite source anchors [S1], [S2] with title and page number attribution.
- Students cannot extract raw bulk textbook text through the interface.

4. Public Availability & Monetization:
- EduPath is strictly non-commercial and free for students (₹0 cost).
- Code is hosted on GitHub under an academic educational repository.

We request your written permission to ingest Chapters 1 through 9 (Python Fundamentals, Conditionals, Loops, Functions, and Sequences) into this academic prototype.

Sincerely,
Perla Manikanta
Lead Developer, EduPath Project (Group G22)
```

---

## 5. Architectural Safeguards Implemented

1. **Learner Resource Library Link:** [ui/learning_resources.py](file:///c:/Users/Mani/EduPath/ui/learning_resources.py) provides a prominent external link to the OpenStax textbook, clearly demarcated as *external supplementary reading* not ingested into the vector database.
2. **Auditable Ingestion Gate:** In [services/document_service.py](file:///c:/Users/Mani/EduPath/services/document_service.py), documents require `rights_basis = 'original'` or `rights_basis = 'permission_obtained'` with explicit verification before chunking or embedding is permitted.
3. **Experiment 08 Honesty:** [experiments/08_rag/experiment.py](file:///c:/Users/Mani/EduPath/experiments/08_rag/experiment.py) uses clearly designated *Illustrative Synthetic Notes* rather than misrepresenting verbatim OpenStax passages.

---

## 6. Academic Conclusion

EduPath demonstrates a mature, legally defensible, and academically rigorous approach to open educational resources. We provide complete technical readiness to ingest OpenStax upon receipt of written institutional authorization, while maintaining zero legal risk in the current production release.
