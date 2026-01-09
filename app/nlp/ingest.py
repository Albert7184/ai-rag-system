import os
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings 
from langchain_community.vectorstores import FAISS

# Xác định đường dẫn gốc để không bị lỗi file not found trên Render
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def get_embeddings():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is missing in Environment Variables")
    return GoogleGenerativeAIEmbeddings(
        model="models/embedding-001",
        google_api_key=api_key
    )

def create_vector_db(user_id: str):
    data_path = os.path.join(BASE_DIR, "data", user_id)
    db_save_path = os.path.join(BASE_DIR, "faiss_index", user_id)

    # Tạo thư mục nếu chưa có để tránh lỗi loader
    os.makedirs(data_path, exist_ok=True)

    if not os.listdir(data_path):
        print(f"No PDF files found for user: {user_id}")
        return None

    loader = DirectoryLoader(data_path, glob="*.pdf", loader_cls=PyPDFLoader)
    documents = loader.load()
    
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    texts = text_splitter.split_documents(documents)
    
    embeddings = get_embeddings()
    db = FAISS.from_documents(texts, embeddings)
    db.save_local(db_save_path)
    
    return db
