import os
from datetime import datetime, timedelta

from app.graph.nodes.compose_prompt import ComposePromptNode
from langchain_openai import ChatOpenAI


class FakeMemoryManager:
    def get_last_activity_time(self):
        # 2 days ago
        return datetime.utcnow() - timedelta(days=2, hours=1)


def main():
    # Ensure API key exists
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")

    node = ComposePromptNode()

    state = {
        "user_id": "test-user",
        "normalized_input": "Привет, я вернулся!",
        # Non-empty memory_context to force dynamic path
        "memory_context": "Недавние сообщения:\n👤 Привет!\n🤖 Как дела?\n\nВажные факты:\nИмя пользователя неизвестно",
        "meta_time": datetime.utcnow(),
        "stage_number": 1,
        "day_number": 3,
        # Inject fake memory with last activity 2 days ago
        "memory_manager": FakeMemoryManager(),
    }

    updated = node.compose_prompt(state)
    formatted = updated.get("formatted_prompt")
    assert formatted, "formatted_prompt is missing"

    llm = ChatOpenAI(api_key=api_key, model=os.getenv("LLM_MODEL", "gpt-4o-mini"), temperature=0.6)
    resp = llm.invoke(formatted)
    print("=== MODEL RESPONSE ===")
    print(resp.content)


if __name__ == "__main__":
    main()


