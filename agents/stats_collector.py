import json
import logging
import os
from datetime import datetime, timezone
from agents.base_agent import BaseAgent
from core.llm_client import LLMClient

logger = logging.getLogger(__name__)

DEFAULT_STATS_PATH = "stats.json"

class StatsCollectorAgent(BaseAgent):
    name = "stats_collector"

    def __init__(self, llm_client: LLMClient, stats_path: str = DEFAULT_STATS_PATH):
        self.llm = llm_client
        if os.path.isdir(stats_path):
            self.stats_path = os.path.join(stats_path, "stats.json")
        else:
            self.stats_path = stats_path

    def _load_history(self) -> list[dict]:
        """Загружает историю предыдущих запусков."""
        if not os.path.exists(self.stats_path):
            return []
        try:
            with open(self.stats_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            logger.warning("stats.json повреждён, начинаю с чистого листа")
            return []

    def _save_history(self, history: list[dict]) -> None:
        """Сохраняет историю запусков."""
        with open(self.stats_path, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)

    def _compute_summary(self, history: list[dict]) -> dict:
        """Считает агрегированную статистику по всей истории."""
        if not history:
            return {}

        successful = [r for r in history if r.get("success")]
        failed = [r for r in history if not r.get("success")]

        # Самая долгая роль
        slowest = max(successful, key=lambda r: r.get("total_elapsed_sec", 0), default=None)

        # Самая дорогая роль по токенам
        most_tokens = max(successful, key=lambda r: r.get("tokens", {}).get("total_tokens", 0), default=None)

        # Среднее время по всем успешным запускам
        elapsed_list = [r["total_elapsed_sec"] for r in successful if "total_elapsed_sec" in r]
        avg_elapsed = round(sum(elapsed_list) / len(elapsed_list), 2) if elapsed_list else None

        # Среднее токенов
        tokens_list = [r["tokens"]["total_tokens"] for r in successful if r.get("tokens")]
        avg_tokens = round(sum(tokens_list) / len(tokens_list)) if tokens_list else None

        return {
            "total_runs": len(history),
            "successful_runs": len(successful),
            "failed_runs": len(failed),
            "success_rate_pct": round(len(successful) / len(history) * 100, 1),
            "avg_elapsed_sec": avg_elapsed,
            "avg_total_tokens": avg_tokens,
            "slowest_role": {
                "role": slowest["role"],
                "elapsed_sec": slowest["total_elapsed_sec"],
            } if slowest else None,
            "most_tokens_role": {
                "role": most_tokens["role"],
                "total_tokens": most_tokens["tokens"]["total_tokens"],
            } if most_tokens else None,
        }

    def run(self, context: dict) -> dict:
        role = context["role"]
        logger.info("Собираю статистику для роли: %s", role)

        timings = context.get("_agent_timings", {})
        total_elapsed = context.get("_pipeline_elapsed", 0)
        token_usage = self.llm.get_total_usage()
        critic_result = context.get("critic_result", {})

        # Запись текущего запуска
        run_record = {
            "role": role,
            "generated_at": context.get("generated_at", datetime.now(timezone.utc).isoformat()),
            "success": True,
            "total_elapsed_sec": round(sum(timings.values()), 2),
            "agent_timings_sec": timings,
            "agent_tokens": context.get("_agent_tokens", {}),
            "tokens": token_usage,
            "quality_score": critic_result.get("quality_score"),
            "is_consistent": critic_result.get("is_consistent"),
        }

        history = self._load_history()
        history.append(run_record)
        self._save_history(history)

        summary = self._compute_summary(history)

        logger.info(
            "Статистика: %.2f сек, %d токенов, quality_score=%s",
            total_elapsed,
            token_usage.get("total_tokens", 0),
            critic_result.get("quality_score", "—"),
        )
        logger.info(
            "История: %d запусков, успешных %.1f%%",
            summary.get("total_runs", 0),
            summary.get("success_rate_pct", 0),
        )

        return {
            "run_stats": run_record,
            "stats_summary": summary,
        }