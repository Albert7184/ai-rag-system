import streamlit as st
import requests
import os

# --- KẾT NỐI BACKEND ---
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="AI RAG Pro", layout="wide")

# Thiết lập mặc định là "guest" nếu chưa có session
if "username" not in st.session_state:
    st.session_state.username = "guest"

# CSS tinh chỉnh giao diện
st.markdown("""
    <style>
    h1 { color: #000 !important; font-weight: 800; }
    .bot-header { font-size: 18px; font-weight: 700; color: #000; border-left: 4px solid #000; padding-left: 10px; margin: 15px 0 5px 0; }
    .stButton>button { width: 100%; }
    .login-box { border: 1px solid #ddd; padding: 20px; border-radius: 10px; background-color: #f9f9f9; }
    </style>
""", unsafe_allow_html=True)

user_id = st.session_state.username

# --- SIDEBAR ---
with st.sidebar:
    st.title("🤖 AI RAG System")
    
    # Hiển thị trạng thái tài khoản
    if user_id == "guest":
        st.warning("⚡ Bạn đang dùng chế độ Khách")
        with st.expander("🔐 Đăng nhập / Đăng ký"):
            tab1, tab2 = st.tabs(["Đăng nhập", "Đăng ký"])
            with tab1:
                u = st.text_input("Tài khoản", key="login_u")
                p = st.text_input("Mật khẩu", type="password", key="login_p")
                if st.button("Xác nhận Đăng nhập"):
                    try:
                        res = requests.post(f"{BACKEND_URL}/login", json={"username": u, "password": p})
                        if res.status_code == 200:
                            st.session_state.username = u
                            st.rerun()
                        else: st.error("Sai thông tin!")
                    except: st.error("Lỗi kết nối!")
            with tab2:
                ur = st.text_input("Tài khoản mới", key="reg_u")
                pr = st.text_input("Mật khẩu mới", type="password", key="reg_p")
                if st.button("Xác nhận Đăng ký"):
                    try:
                        res = requests.post(f"{BACKEND_URL}/register", json={"username": ur, "password": pr})
                        if res.status_code == 200: st.success("Đã đăng ký! Hãy đăng nhập.")
                        else: st.error("Tài khoản đã tồn tại!")
                    except: st.error("Lỗi kết nối!")
    else:
        st.success(f"👤 Xin chào: {user_id}")
        if st.button("Đăng xuất"):
            st.session_state.username = "guest"
            st.rerun()

    st.divider()
    st.subheader("📁 Kho tri thức")
    up = st.file_uploader("Thêm PDF", type="pdf", label_visibility="collapsed")
    if up:
        if st.button("🚀 Tải lên & Học"):
            with st.spinner("Đang học..."):
                try:
                    requests.post(f"{BACKEND_URL}/upload?user_id={user_id}", files={"file": up})
                    st.success("Đã học xong!")
                    st.rerun()
                except: st.error("Lỗi upload!")

    # Danh sách file
    st.divider()
    try:
        files = requests.get(f"{BACKEND_URL}/files/{user_id}").json().get("files", [])
        for f in files:
            col1, col2 = st.columns([4, 1])
            col1.caption(f"📄 {f}")
            if col2.button("🗑️", key=f):
                requests.delete(f"{BACKEND_URL}/files/{user_id}/{f}")
                st.rerun()
    except: pass

# --- VÙNG CHAT CHÍNH (Vào thẳng đây) ---
st.title("🤖 Trợ lý AI RAG")

# Tải lịch sử
if "messages" not in st.session_state:
    try:
        res = requests.get(f"{BACKEND_URL}/history/{user_id}")
        st.session_state.messages = res.json() if res.status_code == 200 else []
    except:
        st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        if m["role"] == "assistant": st.markdown("<div class='bot-header'>PHẢN HỒI:</div>", unsafe_allow_html=True)
        st.write(m["content"])

if prompt := st.chat_input("Hỏi AI về tài liệu của bạn..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.write(prompt)
    
    with st.chat_message("assistant"):
        st.markdown("<div class='bot-header'>PHẢN HỒI:</div>", unsafe_allow_html=True)
        try:
            res = requests.post(f"{BACKEND_URL}/predict", json={"message": prompt, "user_id": user_id}).json()
            reply = res.get("reply", "Tôi không tìm thấy thông tin phù hợp.")
            st.write(reply)
            st.session_state.messages.append({"role": "assistant", "content": reply})
        except:
            st.error("Lỗi kết nối!")
