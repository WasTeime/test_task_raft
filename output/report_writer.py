import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class ReportWriter:
    def __init__(self, output_dir: str = "."):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def save(self, context: dict) -> tuple[Path, Path]:
        json_path = self._save_json(context)
        md_path = self._save_markdown(context)
        return json_path, md_path

    def _save_json(self, context: dict) -> Path:
        path = self.output_dir / "report.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(context, f, ensure_ascii=False, indent=2)
        logger.info("JSON сохранён: %s", path)
        return path

    def _save_markdown(self, context: dict) -> Path:
        path = self.output_dir / "report.md"
        md = self._build_markdown(context)
        with open(path, "w", encoding="utf-8") as f:
            f.write(md)
        logger.info("Markdown сохранён: %s", path)
        return path

    def _build_markdown(self, ctx: dict) -> str:
        role = ctx.get("role", "Неизвестная роль")
        generated_at = ctx.get("generated_at", "")
        skill_map = ctx.get("skill_map", {})
        salary_table = ctx.get("salary_table", {})
        learning_path = ctx.get("learning_path", {})
        critic = ctx.get("critic_result", {})

        level_order = {"critical": 0, "important": 1, "nice-to-have": 2}
        trend_order = {"growing": 0, "stable": 1, "declining": 2}
        level_labels = {"critical": "необходимый", "important": "есть большой спрос", "nice-to-have": "небольшой спрос"}
        trend_labels = {"growing": "постоянно требуется", "stable": "стабильно", "declining": "снижается"}

        def skill_sort_key(s):
            return (level_order.get(s.get("level", ""), 9), trend_order.get(s.get("trend", ""), 9))

        lines = [
            f"# Карьерный отчёт: {role}",
            f"\n_Сгенерировано: {generated_at}_\n",
            "---\n",
            "## Карта навыков\n",
        ]

        category_names = {
            "languages": "Языки программирования",
            "frameworks": "Фреймворки и библиотеки",
            "infrastructure": "Инфраструктура",
            "soft_skills": "Soft skills",
        }

        for key, title in category_names.items():
            skills = skill_map.get(key, [])
            if skills:
                skills = sorted(skills, key=skill_sort_key)
                lines.append(f"### {title}\n")
                lines.append("| Навык | Востребованность | Тренд |")
                lines.append("|-------|-----------------|-------|")
                for s in skills:
                    lvl = s.get("level", "")
                    trnd = s.get("trend", "")
                    lines.append(f"| {s.get('name')} | {level_labels.get(lvl, lvl)} | {trend_labels.get(trnd, trnd)} |")
                lines.append("")

        lines.append("## Зарплатная таблица\n")
        trend = salary_table.get("market_trend", "")
        reason = salary_table.get("market_trend_reason", "")
        lines.append(f"**Тренд рынка:** {trend_labels.get(trend, trend)}")
        lines.append(f"\n_{reason}_\n")
        lines.append("| Грейд | Москва (тыс. ₽) | Регионы (тыс. ₽) | Remote (USD) |")
        lines.append("|-------|----------------|-----------------|--------------|")
        def fmt(r: dict) -> str:
            mn, med, mx = int(r.get("min", 0)), int(r.get("median", 0)), int(r.get("max", 0))
            return f"{mn}–{mx} (средняя: {med})"

        for grade in ["junior", "middle", "senior", "lead"]:
            data = salary_table.get(grade, {})
            lines.append(
                f"| {grade.capitalize()} "
                f"| {fmt(data.get('moscow', {}))} "
                f"| {fmt(data.get('regions_rub', {}))} "
                f"| {fmt(data.get('remote_usd', {}))} |"
            )

        employers = salary_table.get("top_employers", [])
        if employers:
            lines.append("\n**Топ работодателей:**\n")
            sorted_employers = sorted(employers, key=lambda e: (0 if e.get("type") == "российская" else 1))
            for e in sorted_employers:
                lines.append(f"- **{e.get('name')}** ({e.get('type')}) — {e.get('description')}")
            lines.append("")

        lines.append("## План обучения (90 дней)\n")
        for i, phase in enumerate(learning_path.get("phases", []), 1):
            lines.append(f"### Фаза {i}: {phase.get('name')} ({phase.get('duration_days')} дней)\n")
            lines.append("**Маршрут:**")
            for step in phase.get("path", []):
                lines.append(f"- {step}")
            lines.append(f"\n**Milestone:** {phase.get('milestone')}\n")
            projects = phase.get("practice_projects", [])
            if projects:
                lines.append("\n**Практика:**")
                for p in projects:
                    lines.append(f"- **{p.get('name')}** — {p.get('description')}")
            lines.append("")
            lines.append("**Темы:**")
            for topic in phase.get("topics", []):
                lines.append(f"- {topic}")
            lines.append("\n**Ресурсы:**")
            for res in phase.get("resources", []):
                url = res.get("url")
                name = res.get("name")
                link = f"[{name}]({url})" if url else name
                lines.append(f"- {link} _{res.get('type')}_")
            lines.append("")

        lines.append("## Gap-анализ\n")
        gap = learning_path.get("gap_analysis", {})
        lines.append("### Quick Wins (2–4 недели)\n")
        for item in gap.get("quick_wins", []):
            lines.append(f"- {item}")
        lines.append("\n### Long Term (3+ месяца)\n")
        for item in gap.get("long_term", []):
            lines.append(f"- {item}")
        lines.append("")

        project = learning_path.get("portfolio_project", {})
        lines.append("## Портфолио-проект\n")
        lines.append(f"### {project.get('name', '')}\n")
        lines.append(project.get("description", ""))
        skills_used = project.get("skills_demonstrated", [])
        if skills_used:
            lines.append(f"\n**Технологии:** {', '.join(skills_used)}\n")

        lines.append("## Оценка качества\n")
        score = critic.get("quality_score", 0)
        is_ok = critic.get("is_consistent", False)
        lines.append(f"**Оценка:** {score}/100 ({'OK' if is_ok else 'требует внимания'})")
        lines.append(f"\n_{critic.get('quality_score_reason', '')}_\n")
        for w in critic.get("warnings", []):
            lines.append(f"- {w}")

        return "\n".join(lines)