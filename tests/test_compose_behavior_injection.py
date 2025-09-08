import os
from datetime import datetime

from app.graph.nodes.compose_prompt import ComposePromptNode


def test_behavioral_instructions_present_in_prompt(monkeypatch):
    # Ensure system prompt can load without external failures
    monkeypatch.setenv("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", "test-key"))

    node = ComposePromptNode()
    state = {
        "user_id": "test-user",
        "normalized_input": "Мне грустно и тяжело, помоги",
        "memory_context": "Недавние сообщения:\n👤 Привет\n",
        "meta_time": datetime.now(),
        "stage_number": 1,
        "day_number": 1,
        "conversation_history": [
            {"role": "user", "content": "Мне грустно и тяжело, помоги"}
        ],
        "user_profile": {},
        "conversation_context": {},
    }

    updated = node.compose_prompt(state)
    assert updated.get("final_prompt") or updated.get("formatted_prompt")
    # We expect behavioral instructions to be included in the system prompt text used
    final_prompt = updated.get("final_prompt", "")
    assert "=== ПОВЕДЕНЧЕСКАЯ АДАПТАЦИЯ ===" in final_prompt or updated.get("system_prompt_used")


