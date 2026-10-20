import os
import json
import uuid
import streamlit as st
from openai import OpenAI

# 1. Cấu hình giao diện tối ưu cho cả Mobile & PC
st.set_page_config(
    page_title="GDU CodeMentor Workspace", 
    page_icon="👨‍💻", 
    layout="wide",
    initial_sidebar_state="auto"
)

# 2. Thiết lập thư mục lưu trữ ngầm
HISTORY_DIR = "GDU_Chat_History"
if not os.path.exists(HISTORY_DIR):
    os.makedirs(HISTORY_DIR)

# Khởi tạo API Client qua OpenRouter
api_key = "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"
client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")

# --- CÁC HÀM XỬ LÝ LÔ-GIC ---

def get_system_prompt():
    return """Bạn là GDU_OOM_CodeMentor, một Chuyên gia Kỹ thuật Phần mềm kiêm Giảng viên thực hành tại ĐH Gia Định. 
QUY TẮC NỀN TẢNG:
1. GIỚI HẠN CHỦ ĐỀ: BẠN CHỈ HỖ TRỢ VỀ LẬP TRÌNH VÀ CODE. Kiên quyết từ chối các chủ đề ngoài lề lịch sự.
2. NẾU NGƯỜI DÙNG GỬI CODE TRỐNG KHÔNG (không kèm yêu cầu): BẠN BẮT BUỘC PHẢI DỪNG LẠI và hỏi 3 thông tin: (1) Năm học/trình độ? (2) Ngôn ngữ lập trình? (3) Mục tiêu cần hỗ trợ là gì?
3. NẾU CÓ YÊU CẦU RÕ RÀNG HOẶC DÙNG NÚT GỢI Ý: Phân tích, giải quyết code hoặc khởi tạo mã nguồn mới ngay lập tức theo phong cách giảng viên tận tâm.
4. TỰ ĐỘNG HÓA NGỮ CẢNH: Hệ thống tự động ghi nhớ và nén ngữ cảnh xuyên suốt phiên làm việc."""

def init_new_session():
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.chat_title = "Cuộc trò chuyện mới"
    st.session_state.messages = [{"role": "system", "content": get_system_prompt()}]
    st.session_state.context_summary = ""

def save_chat_to_disk():
    user_msgs = [m for m in st.session_state.messages if m["role"] == "user"]
    if not user_msgs:
        return
        
    file_path = os.path.join(HISTORY_DIR, f"{st.session_state.session_id}.json")
    data = {
        "title": st.session_state.chat_title,
        "summary": st.session_state.context_summary,
        "messages": st.session_state.messages
    }
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_chat_from_disk(session_id):
    file_path = os.path.join(HISTORY_DIR, f"{session_id}.json")
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            st.session_state.session_id = session_id
            st.session_state.chat_title = data.get("title", "Lịch sử chat")
            st.session_state.context_summary = data.get("summary", "")
            st.session_state.messages = data.get("messages", [])

def delete_chat(session_id):
    file_path = os.path.join(HISTORY_DIR, f"{session_id}.json")
    if os.path.exists(file_path):
        os.remove(file_path)
    if st.session_state.session_id == session_id:
        init_new_session()

def generate_smart_title(first_user_msg):
    clean_msg = first_user_msg.strip()
    if not clean_msg:
        return "Gỡ lỗi mã nguồn"
    try:
        res = client.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=[{"role": "user", "content": f"Tóm tắt câu sau thành 1 tiêu đề ngắn gọn (3-5 từ): '{clean_msg[:100]}''"}],
            temperature=0.3
        )
        return res.choices[0].message.content.replace('"', '').replace("'", "")
    except:
        return "Gỡ lỗi mã nguồn"

def force_summarize():
    if len(st.session_state.messages) < 3: 
        return
        
    with st.spinner("🔄 Đang tự động đóng gói ngữ cảnh..."):
        messages_to_summarize = st.session_state.messages[1:]
        prompt = f"Ngữ cảnh cũ: {st.session_state.context_summary}\n\nHội thoại:\n"
        for msg in messages_to_summarize:
            if msg["role"] in ["user", "assistant"]:
                prompt += f"{msg['role'].upper()}: {msg['content']}\n"
        
        prompt += "\nGộp chung ngữ cảnh cũ và hội thoại này thành 1 đoạn tóm tắt duy nhất (dưới 150 chữ)."
        try:
            res = client.chat.completions.create(
                model="openai/gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            new_summary = res.choices[0].message.content
            st.session_state.context_summary = new_summary
            
            new_messages = [st.session_state.messages[0]]
            new_messages.append({"role": "system", "content": f"[TÓM TẮT NGỮ CẢNH BẮT BUỘC]: {new_summary}"})
            new_messages.extend(st.session_state.messages[-2:])
            st.session_state.messages = new_messages
        except:
            pass

# --- KHỞI TẠO STATE ---
if "session_id" not in st.session_state:
    init_new_session()

if "renaming_id" not in st.session_state:
    st.session_state.renaming_id = None

# --- GIAO DIỆN SIDEBAR (Tối ưu cho cảm ứng & mobile) ---
with st.sidebar:
    if st.button("➕ Bắt đầu Chủ đề mới", use_container_width=True, type="primary"):
        init_new_session()
        st.session_state.renaming_id = None
        st.rerun()
    
    st.markdown("### 📂 Lịch sử trò chuyện")
    
    files = [f for f in os.listdir(HISTORY_DIR) if f.endswith(".json")]
    
    if not files:
        st.caption("Chưa có lịch sử trò chuyện nào.")
    else:
        sorted_files = sorted(files, key=lambda x: os.path.getmtime(os.path.join(HISTORY_DIR, x)), reverse=True)
        for f in sorted_files:
            session_id = f.replace(".json", "")
            file_path = os.path.join(HISTORY_DIR, f)
            try:
                with open(file_path, "r", encoding="utf-8") as file:
                    data = json.load(file)
                    title = data.get("title", "Lịch sử chat")
            except:
                continue
            
            # Kiểm tra xem đoạn chat này có đang ở chế độ đổi tên hay không
            if st.session_state.renaming_id == session_id:
                new_title_input = st.text_input("Tên mới:", value=title, key=f"input_rename_{session_id}")
                col_save, col_cancel = st.columns(2)
                with col_save:
                    if st.button("Lưu", key=f"save_rename_{session_id}", use_container_width=True):
                        data["title"] = new_title_input.strip() if new_title_input.strip() else "Đoạn chat"
                        with open(file_path, "w", encoding="utf-8") as file:
                            json.dump(data, file, ensure_ascii=False, indent=4)
                        if st.session_state.session_id == session_id:
                            st.session_state.chat_title = data["title"]
                        st.session_state.renaming_id = None
                        st.rerun()
                with col_cancel:
                    if st.button("Hủy", key=f"cancel_rename_{session_id}", use_container_width=True):
                        st.session_state.renaming_id = None
                        st.rerun()
            else:
                # Bố cục 3 cột tỷ lệ chuẩn [3.2 : 0.9 : 0.9] với nút tràn viền co giãn hoàn hảo
                col_chat, col_rename, col_del = st.columns([3.2, 0.9, 0.9])
                with col_chat:
                    btn_type = "primary" if session_id == st.session_state.session_id else "secondary"
                    if st.button(f"💬 {title}", key=f"load_{session_id}", use_container_width=True, type=btn_type):
                        load_chat_from_disk(session_id)
                        st.session_state.renaming_id = None
                        st.rerun()
                with col_rename:
                    if st.button("✏️", key=f"rename_btn_{session_id}", use_container_width=True, help="Đổi tên đoạn chat này"):
                        st.session_state.renaming_id = session_id
                        st.rerun()
                with col_del:
                    if st.button("🗑️", key=f"del_{session_id}", use_container_width=True, help="Xóa đoạn chat này"):
                        delete_chat(session_id)
                        st.session_state.renaming_id = None
                        st.rerun()

    st.markdown("---")
    with st.expander("📌 Cẩm nang & Hỗ trợ (Quan trọng)"):
        st.warning("⚠️ **Lưu ý Tự Động Hóa:**\n\n1. **Đổi chủ đề:** Bấm 'Bắt đầu Chủ đề mới' để làm sạch ngữ cảnh.\n2. **Tự động lưu (Auto-Save):** Hệ thống tự động lưu mọi tiến trình vào bộ nhớ ngầm, bạn có thể đóng trình duyệt bất cứ lúc nào.\n3. **Tải file code:** Sử dụng công cụ đính kèm file ngay bên dưới khung chat để AI đọc code trực tiếp.")
        st.markdown("**Kênh Hỗ trợ & Báo lỗi:**")
        st.link_button("✈️ Telegram Admin", "https://t.me/hkha45", use_container_width=True)
        st.link_button("👾 Server Discord", "https://discord.gg/dXMjFUXeJj", use_container_width=True)

# --- GIAO DIỆN CHÍNH ---
st.title("👨‍💻 GDU_OOM_CodeMentor Workspace")
st.markdown(f"### *{st.session_state.chat_title}*")

# Thanh Gợi ý thao tác nhanh (Đã bổ sung nút Khởi tạo code mới)
st.markdown("**Gợi ý thao tác nhanh:**")
col1, col2, col3, col4 = st.columns(4)
trigger_prompt = None
with col1:
    if st.button("🔍 Rà soát lỗi", use_container_width=True):
        trigger_prompt = "Tôi có một đoạn code đang bị lỗi. Hãy rà soát giúp tôi."
with col2:
    if st.button("💡 Giải thích luồng", use_container_width=True):
        trigger_prompt = "Hãy đóng vai trò giảng viên giải thích chi tiết hoạt động của code."
with col3:
    if st.button("🚀 Tối ưu hiệu suất", use_container_width=True):
        trigger_prompt = "Hãy đánh giá và đề xuất giải pháp tối ưu hóa đoạn code này."
with col4:
    if st.button("✨ Khởi tạo code", use_container_width=True):
        trigger_prompt = "Hãy giúp tôi viết một đoạn mã nguồn đơn giản theo yêu cầu mới."

st.divider()

# TÍNH NĂNG MỚI: Tải lên file mã nguồn trực tiếp
uploaded_file = st.file_uploader("📂 Tải lên file mã nguồn (.py, .txt, .cpp, .lua)", type=["py", "txt", "cpp", "lua", "js", "java"])
file_content_text = ""
if uploaded_file is not None:
    try:
        file_content_text = uploaded_file.read().decode("utf-8")
        st.success(f"Đã tải lên thành công file: **{uploaded_file.name}** ({len(file_content_text)} ký tự)")
    except Exception as e:
        st.error(f"Lỗi đọc file: {e}")

# Hiển thị các tin nhắn trong phiên
for msg in st.session_state.messages:
    if msg["role"] != "system":
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

def process_ai_response(user_message):
    # Nếu có đính kèm file, tự động gộp nội dung file vào tin nhắn gửi cho AI
    final_message = user_message
    if file_content_text:
        final_message = f"{user_message}\n\n[NỘI DUNG MÃ NGUỒN TỪ FILE ĐÍNH KÈM]:\n```python\n{file_content_text}\n```"

    if st.session_state.chat_title == "Cuộc trò chuyện mới":
        st.session_state.chat_title = generate_smart_title(user_message)
    
    st.session_state.messages.append({"role": "user", "content": final_message})
    with st.chat_message("user"):
        st.markdown(user_message)
        if file_content_text:
            st.caption(f"📎 Đã đính kèm nội dung từ file code.")

    api_messages = list(st.session_state.messages)

    # Gọi API AI phản hồi
    with st.chat_message("assistant"):
        with st.spinner("Đang phân tích mã nguồn..."):
            try:
                res = client.chat.completions.create(
                    model="openai/gpt-4o-mini", 
                    messages=api_messages, 
                    temperature=0.2
                )
                raw_reply = res.choices[0].message.content
                
                professional_footer = (
                    "\n\n---\n"
                    "*💡 **Gợi ý học tập:** Bạn đã nắm rõ logic của đoạn code này chưa? Nếu có điểm nào còn mơ hồ, hãy hỏi lại tôi ngay nhé!*\n\n"
                    "*⚠️ **Lưu ý kỹ thuật:** Tôi là trợ lý trí tuệ nhân tạo, kết quả phân tích có thể có sai số. Hãy luôn tự kiểm tra lại mã nguồn trước khi áp dụng thực tế. "
                    "Nếu phát hiện lỗi hệ thống hoặc cần hỗ trợ chuyên sâu, vui lòng liên hệ Quản trị viên qua mục **Cẩm nang & Hỗ trợ** ở thanh bên.*"
                )
                
                reply = raw_reply + professional_footer
                st.markdown(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply})
                
                # Tự động nén ngữ cảnh và tự động lưu ngầm (Auto-Save)
                if len(st.session_state.messages) > 10:
                    force_summarize()
                    st.toast("🧠 Hệ thống đã tự động nén gọn ngữ cảnh để duy trì độ mượt mà!", icon="✅")
                
                save_chat_to_disk()
            except Exception as e:
                st.error(f"Lỗi kết nối API: {e}")

if trigger_prompt:
    process_ai_response(trigger_prompt)
    st.rerun()

if user_input := st.chat_input("Dán mã nguồn hoặc nhập câu hỏi trực tiếp..."):
    process_ai_response(user_input)
    st.rerun()
