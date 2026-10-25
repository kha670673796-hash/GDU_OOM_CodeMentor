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
3. NẾU CÓ YÊU CẦU RÕ RÀNG HOẶC DÙNG NÚT GỢI Ý: Phân tích và giải quyết code ngay lập tức theo phong cách giảng viên tận tâm.
4. KẾT NỐI NGỮ CẢNH: Luôn bám sát [TÓM TẮT NGỮ CẢNH] hoặc lệnh !load từ người dùng."""

def init_new_session():
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.chat_title = "Cuộc trò chuyện mới"
    st.session_state.messages = [{"role": "system", "content": get_system_prompt()}]
    st.session_state.full_history = [] 
    st.session_state.context_summary = ""

def save_chat_to_disk():
    if not st.session_state.full_history:
        return
        
    file_path = os.path.join(HISTORY_DIR, f"{st.session_state.session_id}.json")
    data = {
        "title": st.session_state.chat_title,
        "summary": st.session_state.context_summary,
        "messages": st.session_state.messages,
        "full_history": st.session_state.full_history
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
            raw_history = data.get("full_history", data.get("messages", []))
            st.session_state.full_history = [m for m in raw_history if m["role"] != "system"]

def delete_chat(session_id):
    file_path = os.path.join(HISTORY_DIR, f"{session_id}.json")
    if os.path.exists(file_path):
        os.remove(file_path)
    if st.session_state.session_id == session_id:
        init_new_session()

def generate_smart_title(first_user_msg):
    clean_msg = first_user_msg.replace("!load", "").strip()
    if not clean_msg:
        return "Gỡ lỗi mã nguồn"
    try:
        res = client.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=[{"role": "user", "content": f"Tóm tắt câu sau thành 1 tiêu đề ngắn gọn (3-5 từ): '{clean_msg}'"}],
            temperature=0.3
        )
        return res.choices[0].message.content.replace('"', '').replace("'", "")
    except:
        return "Gỡ lỗi mã nguồn"

def force_summarize():
    if len(st.session_state.messages) < 3: 
        return
        
    with st.spinner("🔄 Đang nén toàn bộ ngữ cảnh hệ thống..."):
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

# --- GIAO DIỆN SIDEBAR ---
with st.sidebar:
    if st.button("➕ Bắt đầu Chủ đề mới", use_container_width=True, type="primary"):
        init_new_session()
        st.session_state.renaming_id = None
        st.rerun()
    
    st.markdown("### 🔍 Tìm kiếm")
    search_query = st.text_input("Tìm kiếm", label_visibility="collapsed", placeholder="🔍 Gõ để tìm tin nhắn cũ...")
    
    st.markdown("### 📂 Lịch sử trò chuyện")
    files = [f for f in os.listdir(HISTORY_DIR) if f.endswith(".json")]
    
    if not files:
        st.caption("Chưa có lịch sử trò chuyện nào.")
    else:
        sorted_files = sorted(files, key=lambda x: os.path.getmtime(os.path.join(HISTORY_DIR, x)), reverse=True)
        display_files = []
        
        if search_query:
            search_query_lower = search_query.lower()
            for f in sorted_files:
                file_path = os.path.join(HISTORY_DIR, f)
                try:
                    with open(file_path, "r", encoding="utf-8") as file:
                        data = json.load(file)
                        if search_query_lower in data.get("title", "").lower():
                            display_files.append(f)
                            continue
                        msgs = data.get("full_history", data.get("messages", []))
                        if any(search_query_lower in m.get("content", "").lower() for m in msgs):
                            display_files.append(f)
                except:
                    continue
        else:
            display_files = sorted_files
            
        if not display_files and search_query:
            st.caption("Không tìm thấy kết quả nào.")

        for f in display_files:
            session_id = f.replace(".json", "")
            file_path = os.path.join(HISTORY_DIR, f)
            try:
                with open(file_path, "r", encoding="utf-8") as file:
                    data = json.load(file)
                    title = data.get("title", "Lịch sử chat")
            except:
                continue
            
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
                col_chat, col_rename, col_del = st.columns([3.2, 0.9, 0.9])
                with col_chat:
                    btn_type = "primary" if session_id == st.session_state.session_id else "secondary"
                    if st.button(f"💬 {title}", key=f"load_{session_id}", use_container_width=True, type=btn_type):
                        load_chat_from_disk(session_id)
                        st.session_state.renaming_id = None
                        st.rerun()
                with col_rename:
                    if st.button("✏️", key=f"rename_btn_{session_id}", use_container_width=True):
                        st.session_state.renaming_id = session_id
                        st.rerun()
                with col_del:
                    if st.button("🗑️", key=f"del_{session_id}", use_container_width=True):
                        delete_chat(session_id)
                        st.session_state.renaming_id = None
                        st.rerun()

    st.markdown("---")
    with st.expander("📌 Cẩm nang & Hỗ trợ (Quan trọng)"):
        st.warning("⚠️ **Lưu ý Ngữ Cảnh & Lưu Trữ:**\n\n1. **Đổi chủ đề:** Bấm 'Bắt đầu Chủ đề mới' để tránh AI nhầm lẫn dữ liệu cũ.\n2. **Lưu tiến trình (!save):** Gõ `!save` để đóng gói ngữ cảnh.\n3. **Khôi phục (!load):** Chọn lịch sử, gõ `!load [yêu cầu mới]`.")

# --- GIAO DIỆN CHÍNH ---
st.title("👨‍💻 GDU_OOM_CodeMentor Workspace")
st.markdown(f"### *{st.session_state.chat_title}*")

# Thanh Gợi ý thao tác nhanh
st.markdown("**Gợi ý thao tác nhanh:**")
col1, col2, col3 = st.columns(3)
trigger_prompt = None
with col1:
    if st.button("🔍 Rà soát lỗi Logic", use_container_width=True):
        trigger_prompt = "Tôi có một đoạn code đang bị lỗi logic. Hãy chuẩn bị tinh thần rà soát từng dòng."
with col2:
    if st.button("💡 Giải thích luồng", use_container_width=True):
        trigger_prompt = "Hãy đóng vai trò là một giảng viên giải thích chi tiết hoạt động của code."
with col3:
    if st.button("🚀 Tối ưu hiệu suất", use_container_width=True):
        trigger_prompt = "Hãy đánh giá độ phức tạp thuật toán và đề xuất giải pháp tối ưu code."

st.divider()

# Hiển thị tất cả tin nhắn từ luồng full_history
for msg in st.session_state.full_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

def process_ai_response(user_message):
    is_save_cmd = user_message.strip().lower() == "!save"
    is_load_cmd = user_message.strip().lower().startswith("!load")

    if st.session_state.chat_title == "Cuộc trò chuyện mới" and not is_save_cmd:
        st.session_state.chat_title = generate_smart_title(user_message)
    
    user_obj = {"role": "user", "content": user_message}
    st.session_state.messages.append(user_obj)
    
    if not is_save_cmd: 
        st.session_state.full_history.append(user_obj)
        with st.chat_message("user"):
            st.markdown(user_message)
    
    if is_save_cmd:
        with st.spinner("Đang lưu trữ tiến trình ngữ cảnh..."):
            force_summarize()
            reply = "💾 **Tiến trình đã được lưu an toàn!** Bạn có thể đóng trình duyệt."
            st.session_state.messages.append({"role": "assistant", "content": reply})
            st.session_state.full_history.append({"role": "assistant", "content": reply})
            with st.chat_message("assistant"):
                st.markdown(reply)
            save_chat_to_disk()
            return

    api_messages = list(st.session_state.messages)
    if is_load_cmd:
        api_messages.append({"role": "system", "content": "Kích hoạt !load. Hãy dựa vào TÓM TẮT NGỮ CẢNH để tiếp tục giải quyết."})

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
                    "*⚠️ **Lưu ý kỹ thuật:** Tôi là trợ lý trí tuệ nhân tạo, kết quả phân tích có thể có sai số. Hãy luôn tự kiểm tra lại mã nguồn trước khi áp dụng thực tế.*"
                )
                
                # Nối Footer để hiển thị (không cho vào AI)
                reply_with_footer = raw_reply + professional_footer
                st.markdown(reply_with_footer)
                
                # CHỈ lưu raw vào API để AI không học vẹt Footer
                st.session_state.messages.append({"role": "assistant", "content": raw_reply})
                
                # Lưu đầy đủ có Footer vào UI
                st.session_state.full_history.append({"role": "assistant", "content": reply_with_footer})
                
                # 10 lượt chat = 20 user+bot + 1 system = 21 messages. Khi chạm mốc này sẽ kích hoạt!
                if len(st.session_state.messages) >= 21:
                    force_summarize()
                    # CẢNH BÁO CHO THUYẾT TRÌNH: Dùng st.success nổi bần bật giữa màn hình
                    st.success("✅ **HỆ THỐNG GDU_OOM_CODEMENTOR:** Đã đạt 10 lượt trò chuyện. Bộ nhớ ngữ cảnh (Context Window) đã được nén tự động để chống lỗi OOM. Lịch sử hiển thị vẫn được giữ nguyên!")
                
                save_chat_to_disk()
            except Exception as e:
                st.error(f"Lỗi kết nối API: {e}")

if trigger_prompt:
    process_ai_response(trigger_prompt)
    st.rerun()

if user_input := st.chat_input("Dán mã nguồn hoặc nhập câu hỏi..."):
    process_ai_response(user_input)
    st.rerun()
