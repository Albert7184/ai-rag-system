import os
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

# Đường dẫn gốc của folder nlp
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def create_vector_db(user_id="user_default"):
    # 1. Định nghĩa đường dẫn riêng biệt theo user_id
    data_path = os.path.join(BASE_DIR, "data", user_id)
    db_save_path = os.path.join(BASE_DIR, "faiss_index", user_id)

    # Kiểm tra thư mục data của user
    if not os.path.exists(data_path):
        os.makedirs(data_path)
        print(f"Thư mục trống, hãy upload PDF cho user: {user_id}")
        return

    # 2. Tải tài liệu PDF từ thư mục riêng của user
    loader = DirectoryLoader(data_path, glob='*.pdf', loader_cls=PyPDFLoader)
    documents = loader.load()

    if not documents:
        print(f"Không tìm thấy tài liệu PDF nào trong {data_path}")
        return

    # 3. Chia nhỏ văn bản
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500, chunk_overlap=50)
    texts = text_splitter.split_documents(documents)

    # 4. Embedding
    # Thay thế dòng cũ bằng dòng này để ép mô hình chạy trên CPU và không cache quá nhiều
embeddings = HuggingFaceEmbeddings(
    model_name='sentence-transformers/all-MiniLM-L6-v2',
    model_kwargs={'device': 'cpu'},
    encode_kwargs={'normalize_embeddings': True}
)

# 5. Lưu trữ kho Vector vào thư mục riêng của user
db = FAISS.from_documents(texts, embeddings)
db.save_local(db_save_path)
print(f"✅ AI đã học xong cho {user_id}! Lưu tại: {db_save_path}")

if __name__ == "__main__":
    # Mặc định chạy cho user_default nếu chạy file này thủ công
    create_vector_db()
