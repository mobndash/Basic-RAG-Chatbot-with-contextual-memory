from fastapi import FastAPI, Request
from pydantic import BaseModel
from rag_chain import chain_with_memory
import uuid
import traceback

app = FastAPI()


class QuestionRequest(BaseModel):
    question: str
    session_id: str = None


@app.post("/ask-question")
async def ask_question(req: QuestionRequest):
    try:
        print(f"\n[INFO] Incoming question: {req.question}")
        session_id = req.session_id or str(uuid.uuid4())
        print(f"[INFO] Using session_id: {session_id}")

        result = chain_with_memory.invoke(
            {"question": req.question},
            config={"configurable": {"session_id": session_id}}
        )

        print(f"[INFO] Answer generated: {result['answer'][:60]}...")

        return {
            "session_id": session_id,
            "answer": result["answer"],
            "sources": [
                {
                    "document": doc.metadata.get("source", "Unknown"),
                    "page": doc.metadata.get("page", "?")
                }
                for doc in result["source_docs"]
            ]
        }

    except Exception as e:
        print("[ERROR] Exception occurred:")
        traceback.print_exc()
        return {"error": str(e)}
