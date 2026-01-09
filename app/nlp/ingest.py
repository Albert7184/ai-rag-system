import os
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings  # Cập nhật thư viện mới
from langchain_community.vectorstores import FAISS

# 1. Cấu hình đường dẫn động để chạy được cả Local và Docker
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "data")
DB_SAVE_PATH = os.path.join(BASE_DIR, "faiss_index")

# 2. Khởi tạo Embedding (Để ở ngoài để dùng chung)
# Sử dụng CPU để tránh lỗi Out of Memory trên Render/Local
embeddings = HuggingFaceEmbeddings(
    model_name='sentence-transformers/all-MiniLM-L6-v2',
    model_kwargs={'device': 'cpu'},
    encode_kwargs={'normalize_embeddings': True}
)

def create_vector_db():
    """Hàm xử lý PDF và tạo kho Vector"""
    if not os.path.exists(DATA_PATH):
        os.makedirs(DATA_PATH)
        print(f"Thư mục {DATA_PATH} mới được tạo, hãy bỏ file PDF vào đó.")
        return None

    # Tải tài liệu
    loader = DirectoryLoader(DATA_PATH, glob="*.pdf", loader_cls=PyPDFLoader)
    documents = loader.load()
    
    if not documents:
        print(f"❌ Không tìm thấy tài liệu PDF nào trong {DATA_PATH}")
        return None
    
    # Chia nhỏ văn bản
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    texts = text_splitter.split_documents(documents)
    
    # Tạo và lưu Vector Store
    db = FAISS.from_documents(texts, embeddings)
    db.save_local(DB_SAVE_PATH)
    print(f"✅ AI đã học xong! Dữ liệu lưu tại: {DB_SAVE_PATH}")
    return db

# QUAN TRỌNG: Không để các lệnh chạy logic ở đây ngoài hàm
# Chỉ chạy khi thực thi trực tiếp file này
if __name__ == "__main__":
    create_vector_db()