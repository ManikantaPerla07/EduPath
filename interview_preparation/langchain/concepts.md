# Interview Prep: LangChain Integration
**EduPath Technical Component:** Prompt Templates, StrOutputParser, BaseRetriever Adapter, Embeddings Adapter\
**Estimated Reproducibility Time:** 15 minutes

---

## 1. Concept Overview
LangChain provides standard interfaces for language model composition:
- `BaseRetriever`: Custom retriever adapter over PostgreSQL pgvector (`NeonPgVectorRetriever`).
- `Embeddings`: Adapter over Gemini Embedding 2 API (`EduPathGeminiEmbeddings`).
- `ChatPromptTemplate` & LCEL Pipe Operator (`|`): Constructs structured pipelines:
  $$\text{Prompt} \mid \text{ChatGoogleGenerativeAI} \mid \text{StrOutputParser}$$

---

## 2. Production Code Reference
- Retriever: `services/langchain_retriever.py`
- Embeddings: `services/langchain_embeddings.py`
- Document Splitting: `services/langchain_document_processing.py`
- LCEL Chain: `services/answer_generation_service.py` (lines 310-345)

---

## 3. Simplified 15-Minute LCEL Pipeline
```python
# interview_preparation/langchain/simple_chain.py
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# LCEL Pipeline Definition: Prompt -> Model -> Output Parser
template = ChatPromptTemplate.from_messages([
    ("system", "You are EduPath tutor. Cite claims with [S1]."),
    ("human", "{question}"),
])

# Test formatting without requiring API key
prompt_val = template.format(question="Explain Python functions.")
print("Formatted Prompt:\n", prompt_val)
```

---

## 4. Mock Interview Questions
- **Q: What is LCEL (LangChain Expression Language), and why is it useful?**\
  *A:* LCEL uses the Unix-style pipe operator (`|`) to compose components into unified `Runnable` objects. It provides native support for streaming, asynchronous execution, batch processing, and standardized input/output validation without manual boilerplate.
- **Q: How does EduPath's `NeonPgVectorRetriever` integrate with LangChain?**\
  *A:* It subclasses `BaseRetriever` and implements `_get_relevant_documents(self, query: str) -> list[Document]`. Inside, it executes our SQL query against Neon pgvector and converts returned rows into LangChain `Document` instances containing page content and metadata.
