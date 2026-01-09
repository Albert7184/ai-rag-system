from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os, shutil, sqlite3, hashlib
import google.generativeai as genai
from langchain_community.vectorstores import FAISS
# Import từ file ingest.py cùng thư mục nlp
from app.nlp.ingest import create_vector_db as run_ingest, get_embeddings

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# --- CẤU HÌNH ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# Đưa database ra ngoài folder app để tránh bị xóa khi redeploy (nếu dùng đĩa cứng gắn ngoài)
DB_PATH = os.path.join(os.path.dirname(CURRENT_DIR), "users.db") 
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
gemini_model = genai.GenerativeModel('gemini-1.5-flash')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT)')
    cursor.execute('''CREATE TABLE IF NOT EXISTS chat_history 
                      (username TEXT, role TEXT, content TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

init_db()

def hash_pass(password: str): return hashlib.sha256(password.encode()).hexdigest()
class UserAuth(BaseModel): username: str; password: str
class UserInput(BaseModel): message: str; user_id: str

@app.post("/predict")
def predict(data: UserInput):
    # Đường dẫn trỏ đúng vào folder faiss_index trong nlp
    user_db_path = os.path.join(CURRENT_DIR, "nlp", "faiss_index", data.user_id)
    
    if not os.path.exists(user_db_path):
        return {"reply": "Bạn chưa tải tài liệu nào lên. Hãy upload PDF trước nhé!"}
    
    try:
        embeddings = get_embeddings()
        db = FAISS.load_local(user_db_path, embeddings, allow_dangerous_deserialization=True)
        docs = db.similarity_search(data.message, k=3)
        context = "\n".join([d.page_content for d in docs])
        
        prompt = f"Dựa vào văn bản đã tải lên:\n{context}\n\nCâu hỏi: {data.message}"
        response = gemini_model.generate_content(prompt)
        
        # Lưu lịch sử chat
        conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
        cur.execute("INSERT INTO chat_history (username, role, content) VALUES (?, 'user', ?)", (data.user_id, data.message))
        cur.execute("INSERT INTO chat_history (username, role, content) VALUES (?, 'assistant', ?)", (data.user_id, response.text))
        conn.commit(); conn.close()
        
        return {"reply": response.text}
    except Exception as e:
        return {"reply": f"Lỗi xử lý: {str(e)}"}

@app.post("/upload")
async def upload(user_id: str, file: UploadFile = File(...)):
    path = os.path.join(CURRENT_DIR, "nlp", "data", user_id)
    os.makedirs(path, exist_ok=True)
    file_path = os.path.join(path, file.filename)
    
    with open(file_path, "wb") as f: 
        shutil.copyfileobj(file.file, f)
    
    # Chạy hàm học tài liệu
    run_ingest(user_id=user_id)
    return {"message": f"Hệ thống đã học xong tài liệu: {file.filename}"}

# --- KHỞI CHẠY ---
if __name__ == "__main__":
    import uvicorn
    # Render yêu cầu dùng Port từ biến môi trường
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
