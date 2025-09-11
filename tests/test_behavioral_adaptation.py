import pytest

from app.utils.behavioral_adaptation import BehavioralAdaptationModule


def make_msg(role, content):
    return {"role": role, "content": content}


@pytest.mark.parametrize(
    "messages,expected_strategy",
    [
        (
            [
                make_msg("user", "Мне грустно и тяжело"),
                make_msg("user", "Сложный день, устал"),
            ],
            "caring",
        ),
        (
            [
                make_msg("user", "Отлично! Ура! Так круто!!!"),
                make_msg("user", "Сегодня супер настроение 😊"),
            ],
            "playful",
        ),
        (
            [
                make_msg("user", "Не понимаю, что делать? Посоветуй, как быть"),
            ],
            "mysterious",  # В стейдже 1 система выбирает основные стратегии
        ),
    ],
)
def test_strategy_selection_by_signals(messages, expected_strategy):
    module = BehavioralAdaptationModule()
    result = module.analyze_and_adapt(messages=messages, user_profile={}, conversation_context={})
    assert result["selected_strategy"] == expected_strategy
    assert result["behavioral_instructions"].startswith("🚨🚨🚨 КРИТИЧЕСКИ ВАЖНО - ПОВЕДЕНЧЕСКАЯ СТРАТЕГИЯ 🚨🚨🚨")


