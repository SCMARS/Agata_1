import os
from datetime import datetime

from app.graph.nodes.compose_prompt import ComposePromptNode
from langchain_openai import ChatOpenAI


CASES = [
    ("caring", "Мне грустно сегодня, тяжело на душе"),
    ("playful", "У меня отличное настроение! Ура!!! 😄"),
    ("supportive", "Не понимаю, что делать? Посоветуй, как быть")
]


def run_case(label: str, user_text: str):
    node = ComposePromptNode()
    state = {
        "user_id": f"test-{label}",
        "normalized_input": user_text,
        "memory_context": "Недавние сообщения:\n👤 Привет\n",
        "meta_time": datetime.now(),
        "stage_number": 1,
        "day_number": 1,
        "conversation_history": [{"role": "user", "content": user_text}],
        "user_profile": {},
        "conversation_context": {},
    }

    updated = node.compose_prompt(state)
    formatted = updated.get("formatted_prompt")
    final_prompt = updated.get("final_prompt")
    assert formatted or final_prompt, "No prompt produced"

    llm = ChatOpenAI(api_key=os.getenv("OPENAI_API_KEY"), model=os.getenv("LLM_MODEL", "gpt-4o-mini"), temperature=0.7)
    resp = llm.invoke(formatted or final_prompt)
    print(f"=== {label.upper()} RESPONSE ===")
    print(resp.content)
    print()


def main():
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY not set")
    for label, txt in CASES:
        run_case(label, txt)


if __name__ == "__main__":
    main()


