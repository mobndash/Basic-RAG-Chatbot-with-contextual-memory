import os
import uuid
from dotenv import load_dotenv

from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.chat_models import ChatOpenAI
from langchain_core.runnables import RunnableMap, RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain.memory import ConversationBufferMemory
# from langchain.memory.chat_message_histories import InMemoryChatMessageHistory
from langchain_community.chat_message_histories.in_memory import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory

# Load environment variables
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")

if not openai_api_key:
    raise ValueError("OPENAI_API_KEY not found in environment variables.")

# Initialize LLM and Embeddings
llm = ChatOpenAI(api_key=openai_api_key,
                 temperature=0.2, model="gpt-3.5-turbo")
embeddings = OpenAIEmbeddings(api_key=openai_api_key)

# Load FAISS retriever
vectorstore_path = "my_faiss_vector_store"
retriever = FAISS.load_local(
    folder_path=vectorstore_path,
    embeddings=embeddings,
    allow_dangerous_deserialization=True
).as_retriever()

CHITCHAT_KEYWORDS = ["hello", "hi", "hey",
                     "how are you", "what's up", "greetings", "Thank you"]

# Define prompt
prompt_template = PromptTemplate(
    input_variables=["context", "question"],
    template="""
You are a teaching assistant for students of some school and are responsible for quesition-answer taks.
If you are not aware of the answer, simply respond like I dont know the answer or similar. Use 10 sentences maximum to answer the question.
Question : {question}
Context : {context}
Answer : """
)

# Helper to format documents


def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)


# Define full RAG chain
full_chain = (
    RunnableMap({
        "question": RunnablePassthrough(),
        "context": lambda x: [] if x["question"].lower().strip() in CHITCHAT_KEYWORDS else retriever.invoke(x["question"])
    }) |
    RunnableMap({
        "question": lambda x: x["question"],
        "context": lambda x: format_docs(x["context"]),
        "source_docs": lambda x: x["context"]
    }) |
    RunnableMap({
        "answer": prompt_template | llm | StrOutputParser(),
        "source_docs": lambda x: x["source_docs"]
    })
)

# Memory store
memory_store = {}

# Function to manage memory per session


def get_session_history(session_id: str) -> BaseChatMessageHistory:
    if session_id not in memory_store:
        memory_store[session_id] = ChatMessageHistory()
    return memory_store[session_id]


# Wrap the full_chain with memory support
chain_with_memory = RunnableWithMessageHistory(
    full_chain,
    get_session_history,
    input_messages_key="question",
    history_messages_key="messages"
)

# Main loop
if __name__ == "__main__":
    import sys

    print("=== RAG Chat with Contextual Memory ===")
    session_id = str(uuid.uuid4())  # Temporary session for each run
    print(f"Session ID: {session_id[:8]}... (for debugging)")

    try:
        while True:
            user_question = input("\nYou: ").strip()
            if user_question.lower() in ["exit", "quit"]:
                print("Exiting. Goodbye!")
                break

            result = chain_with_memory.invoke(
                {"question": user_question},
                config={"configurable": {"session_id": session_id}}
            )

            print("\nAssistant:", result["answer"])
            print("\nSources:")
            for doc in result["source_docs"]:
                print(
                    f"- Document: {doc.metadata.get('source', 'Unknown')}, Page: {doc.metadata.get('page', '?')}")

    except KeyboardInterrupt:
        print("\nInterrupted. Session ended.")
