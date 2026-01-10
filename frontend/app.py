import streamlit as st
import requests
import os

# --- KẾT NỐI BACKEND ---
# Ưu tiên lấy URL từ môi trường Render, nếu không có mới dùng localhost
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="AI RAG Pro", layout="wide")

# CSS tinh chỉnh tiêu đề đen và giao diện chuyên nghiệp
st.markdown("""
    <style>
    h1 { color: #000 !important; font-weight: 800; }
    .bot-header { font-size: 18px; font-weight: 700; color: #000; border-left: 4px solid #000; padding-left: 10px; margin: 15px 0 5px 0; }
    .stButton>button { width: 100%; }
    </style>
""", unsafe_allow_html=True)

# --- XỬ LÝ ĐĂNG NHẬP ---
if "username" not in st.session_state:
    st.title("🤖 AI RAG - Hệ thống tri thức")
    tab1, tab2 = st.tabs(["Đăng nhập", "Đăng ký"])
    
    with tab1:
        u = st.text_input("Tài khoản")
        p = st.text_input("Mật khẩu", type="password")
        if st.button("Vào hệ thống"):
            try:
                # Gọi đến URL Backend trên Render
                res = requests.post(f"{BACKEND_URL}/login", json={"username": u, "password": p})
                if res.status_code == 200:
                    st.session_state.username = u
                    st.rerun()
                else: 
                    st.error("Sai thông tin đăng nhập hoặc tài khoản không tồn tại")
            except requests.exceptions.ConnectionError:
                st.error(f"Không thể kết nối tới Backend tại: {BACKEND_URL}. Hãy kiểm tra cấu hình Render.")

    with tab2:
        ur = st.text_input("Tài khoản mới")
        pr = st.text_input("Mật khẩu mới", type="password")
        if st.button("Tạo tài khoản"):
            try:
                requests.post(f"{BACKEND_URL}/register", json={"username": ur, "password": pr})
                st.success("Đã đăng ký, mời bạn đăng nhập")
            except:
                st.error("Lỗi đăng ký. Thử lại sau.")
    st.stop()

# --- GIAO DIỆN CHÍNH SAU KHI LOGIN ---
user_id = st.session_state.username

with st.sidebar:
    st.title(f"👤 {user_id}")
    if st.button("Đăng xuất"):
        del st.session_state.username
        st.rerun()
    
    st.divider()
    st.subheader("📁 Kho tri thức")
    up = st.file_uploader("Thêm PDF", type="pdf", label_visibility="collapsed")
    if up:
        if st.button("🚀 Tải lên & Học"):
            with st.spinner("Đang học..."):
                requests.post(f"{BACKEND_URL}/upload?user_id={user_id}", files={"file": up})
                st.success("Đã học xong!")
                st.rerun()

    st.divider()
    # Danh sách file hiện có
    try:
        files_res = requests.get(f"{BACKEND_URL}/files/{user_id}")
        files = files_res.json().get("files", []) if files_res.status_code == 200 else []
        for f in files:
            col1, col2 = st.columns([4, 1])
            col1.caption(f"📄 {f}")
            if col2.button("🗑️", key=f):
                requests.delete(f"{BACKEND_URL}/files/{user_id}/{f}")
                st.rerun()
    except:
        st.sidebar.warning("Không thể tải danh sách file.")

# Vùng Chat chính
st.title("🤖 AI RAG Chat")

# Tải lịch sử chat
if "messages" not in st.session_state:
    try:
        history_res = requests.get(f"{BACKEND_URL}/history/{user_id}")
        st.session_state.messages = history_res.json() if history_res.status_code == 200 else []
    except:
        st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        if m["role"] == "assistant": 
            st.markdown("<div class='bot-header'>PHẢN HỒI:</div>", unsafe_allow_html=True)
        st.write(m["content"])

if prompt := st.chat_input("Hỏi AI về tài liệu của bạn..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): 
        st.write(prompt)
    
    with st.chat_message("assistant"):
        st.markdown("<div class='bot-header'>PHẢN HỒI:</div>", unsafe_allow_html=True)
        try:
            res = requests.post(f"{BACKEND_URL}/predict", json={"message": prompt, "user_id": user_id}).json()
            reply = res.get("reply", "Xin lỗi, tôi gặp lỗi khi xử lý câu hỏi.")
            st.write(reply)
            st.session_state.messages.append({"role": "assistant", "content": reply})
        except:
            st.error("Lỗi kết nối khi gửi câu hỏi.")
