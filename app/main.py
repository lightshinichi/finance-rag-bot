from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
from langchain.docstore.document import Document 
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain.chains.question_answering import load_qa_chain
from langchain.prompts import PromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import FAISS
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

app = FastAPI()

# Configuration
MD_STORAGE_DIR = "stored_md_files"
FAISS_INDEX_DIR = "faiss_index"
class QuestionRequest(BaseModel):
    question: str

class SourceDocument(BaseModel):
    text: str
    source: str

class AnswerResponse(BaseModel):
    answer: str
    sources: list[SourceDocument]


def get_md_content():
    
    documents = []
    if not os.path.exists(MD_STORAGE_DIR):
        os.makedirs(MD_STORAGE_DIR)
    
    for filename in os.listdir(MD_STORAGE_DIR):
        if filename.endswith(".md"):
            filepath = os.path.join(MD_STORAGE_DIR, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                text = f.read()
                documents.append(Document(
                    page_content=text,
                    metadata={"source": filename}
                ))
    return documents


def create_vector_store():
   
    raw_text = get_md_content()
    if not raw_text:
        raise ValueError("No markdown files found in storage directory")
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=10000,
        chunk_overlap=1000
    )
    text_chunks = text_splitter.split_documents(raw_text)
    
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    vector_store = FAISS.from_documents(text_chunks, embedding=embeddings)
    vector_store.save_local(FAISS_INDEX_DIR)
    return len(text_chunks)

def get_answer_chain():
    prompt_template = """**Market Research Analysis Task**
    
Analyze the question using document contexts below. Follow these rules:

1. **Source Attribution**:
   - Always cite using format: "[Doc Name] (pX)"
   - Use ➤ for single doc insights
   - Use ✓ when both docs agree

2. **Response Types**:
   A) Direct answer exists:
      - Lead with concise answer
      - Add supporting points
      
   B) Needs comparison:
      - Create comparison table format:
        | Aspect       | [Doc1] | [Doc2] |
        |--------------|--------|--------|
        | [Category]   | Value  | Value  |
      
   C) No direct match:
      - "No exact match. Related insights:"
      - Bullet points from relevant doc(s)

**Context**:
{context}

**Question**: {question}

**Required Format**:
[Answer/Insights]
[Comparison Table (if needed)]
Sources:
- [Doc Name] citations for all claims"""

    model = ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=0.3)
    prompt = PromptTemplate(
        template=prompt_template,
        input_variables=["context", "question"]
    )
    return load_qa_chain(model, chain_type="stuff", prompt=prompt)

@app.on_event("startup")
async def startup_event():
    try:
        create_vector_store()
    except Exception as e:
        print(f"Error during startup processing: {str(e)}")
        
@app.get("/")
def health_check():
    return {"status": "running", "version": "1.0.0"}

@app.post("/process-documents/")
async def process_documents_endpoint():
    """Endpoint to process stored markdown files"""
    try:
        chunk_count = create_vector_store()
        return {
            "status": "success",
            "message": f"Processed documents into {chunk_count} chunks",
            "index_location": FAISS_INDEX_DIR
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ask-question/", response_model=AnswerResponse)
async def ask_question_endpoint(request: QuestionRequest):  # Changed request model
   
    try:
   
        embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
        if not os.path.exists(FAISS_INDEX_DIR):
            raise HTTPException(
                status_code=404,
                detail="Documents not processed. Please process documents first."
            )
            
        vector_store = FAISS.load_local(
            FAISS_INDEX_DIR,
            embeddings,
            allow_dangerous_deserialization=True
        )
        
        
        docs = vector_store.similarity_search(request.question)
        
        
        chain = get_answer_chain()
        response = chain(
            {"input_documents": docs, "question": request.question},
            return_only_outputs=True
        )

        
        answer_text = response.get("output_text", "Answer not available in the context")
        
        
        sources = [
            SourceDocument(
                text=doc.page_content,
                source=doc.metadata.get("source", "unknown")
            )
            for doc in docs
        ]

        return AnswerResponse(
            answer=answer_text,
            sources=sources
        )
    
        
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)