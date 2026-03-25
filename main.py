import argparse
import logging
import sys

from dotenv import load_dotenv

from agents.career_advisor import CareerAdvisorAgent
from agents.critic import CriticAgent
from agents.market_analyst import MarketAnalystAgent
from agents.salary_estimator import SalaryEstimatorAgent
from core.llm_client import LLMClient
from core.pipeline import Pipeline
from output.report_writer import ReportWriter


def setup_logging(verbose: bool, log_prompts: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("groq").setLevel(logging.WARNING)
    if log_prompts and not verbose:
        logging.getLogger("core.llm_client").setLevel(logging.DEBUG)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Мультиагентная система анализа карьерного рынка IT",
        epilog="""
Примеры:
  uv run main.py --role "Backend Python Developer"
  uv run main.py --role "ML Engineer" --output ./results
  uv run main.py --role "iOS Developer (Swift)" --verbose
  uv run main.py --role "iOS Developer (Swift)" --log-prompts
        """,
    )
    parser.add_argument("--role", required=True, help="Название специальности")
    parser.add_argument("--output", default=".", help="Директория для отчётов")
    parser.add_argument("--verbose", action="store_true", help="Подробное логирование")
    parser.add_argument("--log-prompts", action="store_true", help="Логировать промпты и ответы LLM")
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()
    setup_logging(args.verbose, args.log_prompts)

    logger = logging.getLogger(__name__)
    logger.info("Старт анализа: %s", args.role)

    try:
        llm = LLMClient(log_prompts=args.log_prompts)

        pipeline = (
            Pipeline(role=args.role)
            .add_agent(MarketAnalystAgent(llm))
            .add_agent(SalaryEstimatorAgent(llm))
            .add_agent(CareerAdvisorAgent(llm))
            .add_agent(CriticAgent(llm))
        )

        context = pipeline.run()

        writer = ReportWriter(output_dir=args.output)
        json_path, md_path = writer.save(context)

        critic = context.get("critic_result", {})
        score = critic.get("quality_score", 0)
        is_ok = critic.get("is_consistent", False)

        print("\n" + "=" * 50)
        print(f"Анализ завершён: {args.role}")
        print(f"   Оценка качества: {score}/100 ({'OK' if is_ok else 'требует внимания'})")
        print(f"   JSON:     {json_path}")
        print(f"   Markdown: {md_path}")
        print("=" * 50)

        for w in critic.get("warnings", []):
            print(f"   [!] {w}")

    except ValueError as e:
        logger.error("Ошибка конфигурации: %s", e)
        sys.exit(1)
    except RuntimeError as e:
        logger.error("Ошибка выполнения: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()