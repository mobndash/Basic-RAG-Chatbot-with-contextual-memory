import streamlit as st
import requests
import uuid

st.set_page_config(page_title="RAG Chatbot", page_icon="💬")
st.title("💬 RAG Chatbot with Contextual Memory")

if st.button("🔁 New Chat"):
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.messages = []
    st.rerun()


# Initialize session_id and chat history
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []  # stores (role, content)

# Show chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Input box at the bottom
if prompt := st.chat_input("Ask something..."):
    # Show user message
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = requests.post(
                "http://localhost:8000/ask-question",
                json={
                    "question": prompt,
                    "session_id": st.session_state.session_id
                }
            )

            if response.ok:
                data = response.json()
                answer = data["answer"]
                sources = data["sources"]

                # Format sources into markdown
                if sources:
                    source_text = "\n\n**Sources:**\n" + "\n".join(
                        f"- 📄 *{src['document']}*, page {src['page']}"
                        for src in sources
                    )
                else:
                    source_text = ""

                final_answer = answer + source_text
                st.markdown(final_answer)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": final_answer
                })
            else:
                st.error("❌ Failed to get response from API.")
