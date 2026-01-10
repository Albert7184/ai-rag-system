from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os, shutil, sqlite3, hashlib
import google.generativeai as genai
from langchain_community.vectorstores import FAISS

# Hỗ trợ import linh hoạt cho cả Local và Docker
try:
    from app.nlp.ingest import create_vector_db as run_ingest, get_embeddings
except ImportError:
    from nlp.ingest import create_vector_db as run_ingest, get_embeddings

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# --- CẤU HÌNH ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# Đặt database ngay trong folder app để dễ quản lý local
DB_PATH = os.path.join(CURRENT_DIR, "users.db") 
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
gemini_model = genai.GenerativeModel('gemini-1.5-flash')

# --- DATABASE ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT)')
    cursor.execute('''CREATE TABLE IF NOT EXISTS chat_history 
                      (username TEXT, role TEXT, content TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

init_db()

def hash_pass(password: str): 
    return hashlib.sha256(password.encode()).hexdigest()

class UserAuth(BaseModel): 
    username: str
    password: str

class UserInput(BaseModel): 
    message: str
    user_id: str

# --- AUTH ENDPOINTS ---
@app.post("/register")
def register(user: UserAuth):
    if user.username.lower() == "guest":
        raise HTTPException(status_code=400, detail="Không thể đăng ký với tên guest")
    conn = sqlite3.connect(DB_PATH); cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', 
                       (user.username, hash_pass(user.password)))
        conn.commit()
        return {"message": "Đăng ký thành công"}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Tài khoản đã tồn tại")
    finally:
        conn.close()

@app.post("/login")
def login(user: UserAuth):
    conn = sqlite3.connect(DB_PATH); cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ? AND password = ?', 
                   (user.username, hash_pass(user.password)))
    result = cursor.fetchone()
    conn.close()
    if result:
        return {"message": "Đăng nhập thành công"}
    raise HTTPException(status_code=401, detail="Sai tài khoản hoặc mật khẩu")

# --- DATA & HISTORY ENDPOINTS ---
@app.get("/history/{user_id}")
def get_history(user_id: str):
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    cur.execute("SELECT role, content FROM chat_history WHERE username = ? ORDER BY timestamp ASC", (user_id,))
    rows = cur.fetchall()
    conn.close()
    return [{"role": r, "content": c} for r, c in rows]

@app.get("/files/{user_id}")
def list_files(user_id: str):
    # Đường dẫn nlp/data/user_id
    path = os.path.join(CURRENT_DIR, "nlp", "data", user_id)
    if not os.path.exists(path): return {"files": []}
    return {"files": os.listdir(path)}

@app.delete("/files/{user_id}/{filename}")
def delete_file(user_id: str, filename: str):
    file_path = os.path.join(CURRENT_DIR, "nlp", "data", user_id, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        return {"message": "Xóa thành công"}
    raise HTTPException(status_code=404, detail="File không tồn tại")

# --- CHAT & RAG ENDPOINTS ---
@app.post("/predict")
def predict(data: UserInput):
    # Nếu user_id trống, mặc định là guest
    uid = data.user_id if data.user_id else "guest"
    user_db_path = os.path.join(CURRENT_DIR, "nlp", "faiss_index", uid)
    
    if not os.path.exists(user_db_path):
        return {"reply": "Chế độ Khách: Hãy upload PDF ở sidebar để bắt đầu hỏi nhé!"}
    
    try:
        embeddings = get_embeddings()
        db = FAISS.load_local(user_db_path, embeddings, allow_dangerous_deserialization=True)
        docs = db.similarity_search(data.message, k=3)
        context = "\n".join([d.page_content for d in docs])
        
        prompt = f"Dựa vào văn bản đã tải lên:\n{context}\n\nCâu hỏi: {data.message}"
        response = gemini_model.generate_content(prompt)
        
        # Lưu lịch sử chat (cho cả guest và user)
        conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
        cur.execute("INSERT INTO chat_history (username, role, content) VALUES (?, 'user', ?)", (uid, data.message))
        cur.execute("INSERT INTO chat_history (username, role, content) VALUES (?, 'assistant', ?)", (uid, response.text))
        conn.commit(); conn.close()
        
        return {"reply": response.text}
    except Exception as e:
        return {"reply": f"Lỗi xử lý AI: {str(e)}"}

@app.post("/upload")
async def upload(user_id: str, file: UploadFile = File(...)):
    uid = user_id if user_id else "guest"
    # Tạo folder data/guest hoặc data/user_id
    path = os.path.join(CURRENT_DIR, "nlp", "data", uid)
    os.makedirs(path, exist_ok=True)
    file_path = os.path.join(path, file.filename)
    
    with open(file_path, "wb") as f: 
        shutil.copyfileobj(file.file, f)
    
    # Chạy hàm học tài liệu cho ID tương ứng
    run_ingest(user_id=uid)
    return {"message": f"Hệ thống đã học xong tài liệu: {file.filename}"}

# --- KHỞI CHẠY ---
if __name__ == "__main__":
    import uvicorn
    # Port 8000 cho local, lấy biến môi trường cho Render
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
