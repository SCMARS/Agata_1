import pytest

from app.utils.question_controller import QuestionController
from app.graph.pipeline import AgathaPipeline


def test_question_controller_frequency_basic():
    qc = QuestionController(max_frequency=3)
    user = "u1"

    # Первые два сообщения — избегаем вопроса
    assert qc.should_avoid_question(user) is True
    qc.increment_counter(user)
    assert qc.should_avoid_question(user) is True
    qc.increment_counter(user)

    # Третье сообщение — можно задавать вопрос
    assert qc.should_avoid_question(user) is False
    qc.increment_counter(user)

    # Цикл повторяется: снова два избегания, затем разрешение
    assert qc.should_avoid_question(user) is True
    qc.increment_counter(user)
    assert qc.should_avoid_question(user) is True
    qc.increment_counter(user)
    assert qc.should_avoid_question(user) is False


@pytest.mark.asyncio
async def test_pipeline_stage_calculation(monkeypatch):
    pipeline = AgathaPipeline()

    class DummyMemory:
        def get_user_stats(self):
            return {"days_since_start": 2}

    # Подменяем получение памяти, чтобы не зависеть от внешних сервисов
    monkeypatch.setattr(pipeline, "_get_memory", lambda user_id: DummyMemory())

    async def run_case(num_messages: int):
        state = {
            "user_id": "u1",
            "messages": [{"role": "user", "content": "hi"}] * num_messages,
        }
        state = await pipeline._ingest_input(state)  # type: ignore
        return state

    # 1-5 -> stage 1
    s1 = await run_case(1)
    assert s1["stage_number"] == 1
    assert s1["day_number"] == 2
    assert s1.get("stage_prompt")

    s2 = await run_case(5)
    assert s2["stage_number"] == 1

    # 6-15 -> stage 2
    s3 = await run_case(6)
    assert s3["stage_number"] == 2

    s4 = await run_case(15)
    assert s4["stage_number"] == 2

    # 16+ -> stage 3
    s5 = await run_case(16)
    assert s5["stage_number"] == 3


