"""
E2E тесты агента с детерминированными evaluators

Пять быстрых тестов (match-based evaluators из agentevals).
Не требуют дорогих LLM вызовов, работают с любой моделью.

Рекомендуется запускать для быстрой проверки:
    make test-deterministic
    # или
    pytest tests/test_agent_deterministic.py -v
"""
import pytest
import sys
import logging
from pathlib import Path
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from agentevals.trajectory.match import create_trajectory_match_evaluator
from tests.helpers import extract_trajectory, print_trajectory

# Импортируем config для доступа к настройкам
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

logger = logging.getLogger(__name__)


@pytest.mark.deterministic
@pytest.mark.asyncio
async def test_rag_search_superset(agent_fixture):
    """
    Тест 1: RAG Search Tool (Superset)
    
    Проверяет что агент вызывает rag_search при вопросах о документах из PDF.
    Evaluator: superset - агент должен минимум вызвать rag_search,
    но может делать дополнительные вызовы.
    """
    agent = agent_fixture
    
    # Вопрос о документах из PDF
    user_message = "Какие условия потребительского кредита?"
    
    # Запускаем агента и получаем траекторию
    actual_trajectory = await extract_trajectory(agent, "test_rag_1", user_message)
    
    # Для отладки выводим траекторию
    print_trajectory(actual_trajectory)
    
    # Создаем референсную траекторию - минимальные ожидания
    # Важно: это минимум что должен сделать агент
    reference_trajectory = [
        HumanMessage(content=user_message),
        AIMessage(
            content="",
            tool_calls=[{
                "name": "rag_search",
                "args": {"query": "условия потребительского кредита"},
                "id": "call_1"
            }]
        ),
        ToolMessage(
            content='{"sources": [{"source": "doc.pdf", "page_content": "..."}]}',
            name="rag_search",
            tool_call_id="call_1"
        ),
        AIMessage(content="Потребительский кредит предоставляется...")
    ]
    
    # Создаем evaluator
    # mode="superset" - агент должен минимум вызвать инструменты из reference
    # tool_args_match_mode="ignore" - аргументы не важны (LLM может переформулировать)
    evaluator = create_trajectory_match_evaluator(
        trajectory_match_mode="superset",
        tool_args_match_mode="ignore"
    )
    
    # Проверяем траекторию
    result = evaluator(
        outputs=actual_trajectory,
        reference_outputs=reference_trajectory
    )
    
    # Выводим результат evaluator в лог
    logger.info("=" * 60)
    logger.info("📊 EVALUATOR RESULT")
    logger.info(f"   Score: {result['score']}")
    logger.info(f"   Comment: {result.get('comment', 'No comment')}")
    logger.info(f"   Trajectory length: {len(actual_trajectory)}")
    logger.info("=" * 60)
    
    # Assert с информативным сообщением
    assert result["score"], (
        f"Expected agent to call rag_search (superset match failed).\n"
        f"Comment: {result.get('comment', 'No comment')}\n"
        f"Actual trajectory length: {len(actual_trajectory)}"
    )


@pytest.mark.deterministic
@pytest.mark.asyncio
async def test_mcp_search_products_subset(agent_fixture):
    """
    Тест 2: MCP Search Products (Subset)
    
    Проверяет что агент НЕ вызывает лишние инструменты при запросе актуальных данных.
    Evaluator: subset - агент не должен вызывать инструменты, которых нет в reference.
    Для актуальных ставок должен использовать только search_products (НЕ rag_search).
    """
    agent = agent_fixture
    
    # Вопрос об актуальных данных (не из PDF)
    user_message = "Покажи актуальные ставки по вкладам"
    
    # Запускаем агента и получаем траекторию
    actual_trajectory = await extract_trajectory(agent, "test_mcp_2", user_message)
    
    # Для отладки выводим траекторию
    print_trajectory(actual_trajectory)
    
    # Создаем референсную траекторию - только search_products
    reference_trajectory = [
        HumanMessage(content=user_message),
        AIMessage(
            content="",
            tool_calls=[{
                "name": "search_products",
                "args": {"product_type": "deposit"},
                "id": "call_1"
            }]
        ),
        ToolMessage(
            content='[{"name": "Вклад", "rate": "16%"}]',
            name="search_products",
            tool_call_id="call_1"
        ),
        AIMessage(content="Актуальные ставки по вкладам...")
    ]
    
    # Создаем evaluator
    # mode="subset" - агент НЕ должен вызывать инструменты, которых нет в reference
    # tool_args_match_mode="ignore" - аргументы не важны
    evaluator = create_trajectory_match_evaluator(
        trajectory_match_mode="subset",
        tool_args_match_mode="ignore"
    )
    
    # Проверяем траекторию
    result = evaluator(
        outputs=actual_trajectory,
        reference_outputs=reference_trajectory
    )
    
    # Выводим результат evaluator в лог
    logger.info("=" * 60)
    logger.info("📊 EVALUATOR RESULT")
    logger.info(f"   Score: {result['score']}")
    logger.info(f"   Comment: {result.get('comment', 'No comment')}")
    logger.info(f"   Trajectory length: {len(actual_trajectory)}")
    logger.info("=" * 60)
    
    # Assert с информативным сообщением
    assert result["score"], (
        f"Expected agent to use ONLY search_products (subset match failed).\n"
        f"Agent should NOT call rag_search for current data.\n"
        f"Comment: {result.get('comment', 'No comment')}\n"
        f"Actual trajectory length: {len(actual_trajectory)}"
    )


@pytest.mark.deterministic
@pytest.mark.asyncio
async def test_currency_converter_called(agent_fixture):
    """
    Тест 3: MCP currency_converter (конкретный инструмент).

    Проверяет вызов currency_converter при запросе курса валют (MCP).
    Evaluator: superset — минимум вызов этого инструмента, лишние вызовы допустимы.
    """
    agent = agent_fixture
    user_message = "Какой сейчас курс доллара к рублю?"

    actual_trajectory = await extract_trajectory(agent, "test_currency_3", user_message)
    print_trajectory(actual_trajectory)

    reference_trajectory = [
        HumanMessage(content=user_message),
        AIMessage(
            content="",
            tool_calls=[{
                "name": "currency_converter",
                "args": {},
                "id": "call_1",
            }],
        ),
        ToolMessage(
            content="1 USD = 97.00 RUB",
            name="currency_converter",
            tool_call_id="call_1",
        ),
        AIMessage(content="Курс доллара к рублю..."),
    ]

    evaluator = create_trajectory_match_evaluator(
        trajectory_match_mode="superset",
        tool_args_match_mode="ignore",
    )
    result = evaluator(
        outputs=actual_trajectory,
        reference_outputs=reference_trajectory,
    )

    logger.info("=" * 60)
    logger.info("📊 EVALUATOR RESULT")
    logger.info(f"   Score: {result['score']}")
    logger.info(f"   Comment: {result.get('comment', 'No comment')}")
    logger.info(f"   Trajectory length: {len(actual_trajectory)}")
    logger.info("=" * 60)

    assert result["score"], (
        f"Expected agent to call currency_converter (superset match failed).\n"
        f"Comment: {result.get('comment', 'No comment')}\n"
        f"Actual trajectory length: {len(actual_trajectory)}"
    )


@pytest.mark.deterministic
@pytest.mark.asyncio
async def test_mcp_converter_and_products_unordered(agent_fixture):
    """
    Тест 4: Набор инструментов без учёта порядка (trajectory unordered).

    В agentevals `unordered` = двусторонний superset по списку tool_calls: те же
    инструменты с тем же числом вызовов, без лишних (порядок в траектории не важен).

    Запрос сочетает актуальный курс (MCP) и каталог вкладов (MCP) — без PDF/RAG,
    чтобы набор был стабильным.
    """
    agent = agent_fixture
    user_message = (
        "Конвертируй 50 USD в рубли по курсу ЦБ и покажи актуальные ставки по вкладам"
    )

    actual_trajectory = await extract_trajectory(agent, "test_unordered_4", user_message)
    print_trajectory(actual_trajectory)

    reference_trajectory = [
        HumanMessage(content=user_message),
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "currency_converter",
                    "args": {
                        "from_currency": "USD",
                        "to_currency": "RUB",
                        "amount": 50,
                    },
                    "id": "call_1",
                },
                {
                    "name": "search_products",
                    "args": {"product_type": "deposit"},
                    "id": "call_2",
                },
            ],
        ),
        ToolMessage(
            content="50 USD = ... RUB",
            name="currency_converter",
            tool_call_id="call_1",
        ),
        ToolMessage(
            content='[{"name": "Вклад", "rate": "16%"}]',
            name="search_products",
            tool_call_id="call_2",
        ),
        AIMessage(content="Курс и ставки по вкладам:"),
    ]

    evaluator = create_trajectory_match_evaluator(
        trajectory_match_mode="unordered",
        tool_args_match_mode="ignore",
    )
    result = evaluator(
        outputs=actual_trajectory,
        reference_outputs=reference_trajectory,
    )

    logger.info("=" * 60)
    logger.info("📊 EVALUATOR RESULT")
    logger.info(f"   Score: {result['score']}")
    logger.info(f"   Comment: {result.get('comment', 'No comment')}")
    logger.info(f"   Trajectory length: {len(actual_trajectory)}")
    logger.info("=" * 60)

    assert result["score"], (
        "Expected exactly currency_converter + search_products "
        "(unordered / bidirectional superset).\n"
        f"Comment: {result.get('comment', 'No comment')}\n"
        f"Actual trajectory length: {len(actual_trajectory)}"
    )


@pytest.mark.deterministic
@pytest.mark.asyncio
async def test_currency_converter_args_superset(agent_fixture):
    """
    Тест 5: Корректность аргументов инструмента.

    Вызывает currency_converter; фактические args должны включать ключи референса
    (tool_args_match_mode=superset для USD→RUB).
    """
    agent = agent_fixture
    user_message = "Переведи 100 долларов в рубли"

    actual_trajectory = await extract_trajectory(agent, "test_args_5", user_message)
    print_trajectory(actual_trajectory)

    reference_trajectory = [
        HumanMessage(content=user_message),
        AIMessage(
            content="",
            tool_calls=[{
                "name": "currency_converter",
                "args": {"from_currency": "USD", "to_currency": "RUB"},
                "id": "call_1",
            }],
        ),
        ToolMessage(
            content="100.00 USD = 9 700.00 RUB",
            name="currency_converter",
            tool_call_id="call_1",
        ),
        AIMessage(content="Это составляет около ... рублей."),
    ]

    evaluator = create_trajectory_match_evaluator(
        trajectory_match_mode="superset",
        tool_args_match_mode="superset",
    )
    result = evaluator(
        outputs=actual_trajectory,
        reference_outputs=reference_trajectory,
    )

    logger.info("=" * 60)
    logger.info("📊 EVALUATOR RESULT")
    logger.info(f"   Score: {result['score']}")
    logger.info(f"   Comment: {result.get('comment', 'No comment')}")
    logger.info(f"   Trajectory length: {len(actual_trajectory)}")
    logger.info("=" * 60)

    assert result["score"], (
        "Expected currency_converter with from_currency=USD and to_currency=RUB "
        "(args superset match failed).\n"
        f"Comment: {result.get('comment', 'No comment')}\n"
        f"Actual trajectory length: {len(actual_trajectory)}"
    )

