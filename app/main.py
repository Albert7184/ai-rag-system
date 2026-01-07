from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os, shutil, sqlite3, hashlib
import google.generativeai as genai
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from app.nlp.ingest import create_vector_db as run_ingest

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# --- CẤU HÌNH HỆ THỐNG ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(CURRENT_DIR, "users.db")
genai.configure(api_key="AIzaSyBxj-bpDICFQkL-WrZqH9qNseUbfTZaFPQ")
gemini_model = genai.GenerativeModel('gemini-1.5-flash')
embeddings = HuggingFaceEmbeddings(model_name='sentence-transformers/all-MiniLM-L6-v2')

# --- KHỞI TẠO DATABASE ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT)')
    cursor.execute('''CREATE TABLE IF NOT EXISTS chat_history 
                     (username TEXT, role TEXT, content TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

init_db()

# --- UTILS ---
def hash_pass(password: str): return hashlib.sha256(password.encode()).hexdigest()

class UserAuth(BaseModel): username: str; password: str
class UserInput(BaseModel): message: str; user_id: str

# --- API AUTHENTICATION ---
@app.post("/register")
def register(user: UserAuth):
    try:
        conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
        cur.execute("INSERT INTO users VALUES (?, ?)", (user.username, hash_pass(user.password)))
        conn.commit(); conn.close()
        return {"message": "Thành công"}
    except: raise HTTPException(400, "Tên tài khoản đã tồn tại")

@app.post("/login")
def login(user: UserAuth):
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username=? AND password=?", (user.username, hash_pass(user.password)))
    if cur.fetchone(): return {"username": user.username}
    raise HTTPException(401, "Sai tài khoản hoặc mật khẩu")

# --- API CHAT & RAG ---
@app.post("/predict")
def predict(data: UserInput):
    user_db_path = os.path.join(CURRENT_DIR, "nlp", "faiss_index", data.user_id)
    if not os.path.exists(user_db_path):
        return {"reply": "Vui lòng upload tài liệu trước khi đặt câu hỏi."}
    
    # RAG Logic
    db = FAISS.load_local(user_db_path, embeddings, allow_dangerous_deserialization=True)
    docs = db.similarity_search(data.message, k=3)
    context = "\n".join([d.page_content for d in docs])
    
    response = gemini_model.generate_content(f"Dựa vào: {context}\nTrả lời: {data.message}")
    
    # Lưu lịch sử
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    cur.execute("INSERT INTO chat_history (username, role, content) VALUES (?, 'user', ?)", (data.user_id, data.message))
    cur.execute("INSERT INTO chat_history (username, role, content) VALUES (?, 'assistant', ?)", (data.user_id, response.text))
    conn.commit(); conn.close()
    
    return {"reply": response.text}

@app.get("/history/{user_id}")
def get_history(user_id: str):
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    cur.execute("SELECT role, content FROM chat_history WHERE username=? ORDER BY timestamp", (user_id,))
    res = [{"role": r[0], "content": r[1]} for r in cur.fetchall()]
    conn.close(); return res

# --- API FILE MANAGEMENT ---
@app.post("/upload")
async def upload(user_id: str, file: UploadFile = File(...)):
    path = os.path.join(CURRENT_DIR, "nlp", "data", user_id)
    os.makedirs(path, exist_ok=True)
    with open(os.path.join(path, file.filename), "wb") as f: shutil.copyfileobj(file.file, f)
    run_ingest(user_id=user_id)
    return {"message": "Đã học tài liệu"}

@app.get("/files/{user_id}")
def list_files(user_id: str):
    path = os.path.join(CURRENT_DIR, "nlp", "data", user_id)
    return {"files": os.listdir(path) if os.path.exists(path) else []}

@app.delete("/files/{user_id}/{name}")
def delete_file(user_id: str, name: str):
    os.remove(os.path.join(CURRENT_DIR, "nlp", "data", user_id, name))
    run_ingest(user_id=user_id)
    return {"message": "Đã xóa"}