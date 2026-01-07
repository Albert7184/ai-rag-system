import streamlit as st
import requests

API_URL = "http://127.0.0.1:8000"

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
            res = requests.post(f"{API_URL}/login", json={"username": u, "password": p})
            if res.status_code == 200:
                st.session_state.username = u
                st.rerun()
            else: st.error("Sai thông tin đăng nhập")
    with tab2:
        ur = st.text_input("Tài khoản mới")
        pr = st.text_input("Mật khẩu mới", type="password")
        if st.button("Tạo tài khoản"):
            requests.post(f"{API_URL}/register", json={"username": ur, "password": pr})
            st.success("Đã đăng ký, mời bạn đăng nhập")
    st.stop()

# --- GIAO DIỆN CHÍNH SAU KHI LOGIN ---
user_id = st.session_state.username

# Sidebar: Profile & File Management
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
                requests.post(f"{API_URL}/upload?user_id={user_id}", files={"file": up})
                st.rerun()

    st.divider()
    # Danh sách file hiện có
    files = requests.get(f"{API_URL}/files/{user_id}").json().get("files", [])
    for f in files:
        col1, col2 = st.columns([4, 1])
        col1.caption(f"📄 {f}")
        if col2.button("🗑️", key=f):
            requests.delete(f"{API_URL}/files/{user_id}/{f}")
            st.rerun()

# Vùng Chat chính
st.title("🤖 AI RAG")

# Tải lịch sử chat
if "messages" not in st.session_state:
    st.session_state.messages = requests.get(f"{API_URL}/history/{user_id}").json()

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        if m["role"] == "assistant": st.markdown("<div class='bot-header'>PHẢN HỒI:</div>", unsafe_allow_html=True)
        st.write(m["content"])

if prompt := st.chat_input("Hỏi AI về tài liệu của bạn..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.write(prompt)
    
    with st.chat_message("assistant"):
        st.markdown("<div class='bot-header'>PHẢN HỒI:</div>", unsafe_allow_html=True)
        res = requests.post(f"{API_URL}/predict", json={"message": prompt, "user_id": user_id}).json()
        st.write(res["reply"])
        st.session_state.messages.append({"role": "assistant", "content": res["reply"]})