from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
from langchain_community.docstore.document import Document 
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain.chains.question_answering import load_qa_chain
from langchain.prompts import PromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
import google.generativeai as genai
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        os.getenv("FRONTEND_URL", "http://localhost:8501"),  
        "http://localhost:8000"  
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
MD_STORAGE_DIR = os.getenv("MD_STORAGE_DIR", "stored_md_files")
FAISS_INDEX_DIR = os.getenv("FAISS_INDEX_DIR", "faiss_index")

class QuestionRequest(BaseModel):
    question: str

class SourceDocument(BaseModel):
    text: str
    source: str

class AnswerResponse(BaseModel):
    answer: str
    sources: list[SourceDocument]

def get_md_content():
    """Load markdown files with error handling"""
    documents = []
    try:
        if not os.path.exists(MD_STORAGE_DIR):
            logger.warning(f"Storage directory {MD_STORAGE_DIR} not found")
            return documents
            
        for filename in os.listdir(MD_STORAGE_DIR):
            if filename.endswith(".md"):
                filepath = os.path.join(MD_STORAGE_DIR, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        text = f.read()
                        documents.append(Document(
                            page_content=text,
                            metadata={"source": filename}
                        ))
                except Exception as e:
                    logger.error(f"Error reading {filename}: {str(e)}")
        return documents
    except Exception as e:
        logger.error(f"Error loading documents: {str(e)}")
        raise

def create_vector_store():
    """Create FAISS index with retry logic"""
    try:
        raw_text = get_md_content()
        if not raw_text:
            logger.error("No markdown files available for processing")
            raise ValueError("No markdown files found in storage directory")
        
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=10000,
            chunk_overlap=1000
        )
        text_chunks = text_splitter.split_documents(raw_text)
        
        embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
        vector_store = FAISS.from_documents(text_chunks, embedding=embeddings)
        vector_store.save_local(FAISS_INDEX_DIR)
        logger.info(f"Created FAISS index with {len(text_chunks)} chunks")
        return len(text_chunks)
    except Exception as e:
        logger.error(f"Vector store creation failed: {str(e)}")
        raise

def get_answer_chain():
    """Configure QA chain with fallback model"""
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
    
    try:
        model = ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=0.3)
    except Exception as e:
        logger.warning(f"Falling back to default model: {str(e)}")
        model = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0.3)
    
    prompt = PromptTemplate(
        template=prompt_template,
        input_variables=["context", "question"]
    )
    return load_qa_chain(model, chain_type="stuff", prompt=prompt)

@app.on_event("startup")
async def startup_event():
    """Initialize application with retry logic"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            logger.info(f"Initializing vector store (attempt {attempt+1})")
            create_vector_store()
            return
        except Exception as e:
            logger.error(f"Startup attempt {attempt+1} failed: {str(e)}")
            if attempt == max_retries - 1:
                logger.critical("Failed to initialize vector store")
                raise

@app.get("/")
def health_check():
    return {
        "status": "running",
        "version": "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "development")
    }

@app.post("/process-documents/")
async def process_documents_endpoint():
    """Endpoint to process documents with async support"""
    try:
        chunk_count = create_vector_store()
        return {
            "status": "success",
            "message": f"Processed documents into {chunk_count} chunks",
            "index_location": FAISS_INDEX_DIR
        }
    except Exception as e:
        logger.error(f"Document processing error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ask-question/", response_model=AnswerResponse)
async def ask_question_endpoint(request: QuestionRequest):
    """Improved question handling with better error messages"""
    try:
        if not request.question.strip():
            raise HTTPException(status_code=400, detail="Empty question submitted")
            
        embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
        
        if not os.path.exists(FAISS_INDEX_DIR):
            logger.warning("FAISS index not found during question request")
            raise HTTPException(
                status_code=404,
                detail="Document index not ready. Please process documents first."
            )
            
        vector_store = FAISS.load_local(
            FAISS_INDEX_DIR,
            embeddings,
            allow_dangerous_deserialization=True
        )
        
        docs = vector_store.similarity_search(request.question, k=5)
        
        if not docs:
            logger.info(f"No documents found for question: {request.question}")
            return AnswerResponse(
                answer="No relevant documents found",
                sources=[]
            )
            
        chain = get_answer_chain()
        response = chain(
            {"input_documents": docs, "question": request.question},
            return_only_outputs=True
        )

        answer_text = response.get("output_text", "Answer not available in the context")
        
        sources = [
            SourceDocument(
                text=doc.page_content[:500] + "...",  # Truncate for response
                source=doc.metadata.get("source", "unknown")
            )
            for doc in docs
        ]

        return AnswerResponse(
            answer=answer_text,
            sources=sources
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Question processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host=os.getenv("HOST", "0.0.0.0"), 
        port=int(os.getenv("PORT", 8000))
    )