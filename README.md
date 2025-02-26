# Financial RAG (Retrieval-Augmented Generation) Bot

A sophisticated question-answering system for financial documents, leveraging advanced PDF parsing and AI-powered analysis.

## 🛠️ Technologies Used

| Component          | Technologies                                                                 |
|--------------------|------------------------------------------------------------------------------|
| **Frontend**       | Streamlit, Requests                                                          |
| **Backend**        | FastAPI, Uvicorn, LangChain                                                  |
| **NLP/ML**         | Google Gemini Pro/1.5-Pro, FAISS                                             |
| **Vector Storage** | FAISS (Facebook AI Similarity Search)                                        |
| **PDF Processing** | Marker (Modified for financial docs)                                         |
| **Infrastructure** | Heroku (Backend), Streamlit Community Cloud (Frontend)                       |

## 📄 Document Preprocessing Methodology

### 1. **PDF Parsing & Structure Extraction**
```mermaid
graph TD
    A[Raw PDF] --> B[Marker Processing]
    B --> C{Content Type}
    C -->|Text| D[Clean Markdown]
    C -->|Table| E[CSV Conversion]
    C -->|Image| F[Image Extraction]
    D --> G[Structured MD File]
    E --> G
    F --> H[Image Description]
    H --> G
