"""Парсер массовой загрузки вопросов одним сообщением."""

from __future__ import annotations

import re
from dataclasses import dataclass


QUESTION_RE = re.compile(r"^(\d+)\s*[\.\)\:]\s*(.+?)\s*$")
# +A. текст / +A) текст / A. текст / +С. текст (кириллица)
OPTION_RE = re.compile(
    r"^(\+)?\s*([A-Za-zА-Яа-яЁё])\s*[\.\)\:]\s*(.+?)\s*$"
)


@dataclass
class ParsedQuestion:
    number: int
    text: str
    options: list[str]
    correct_index: int


@dataclass
class ParseError:
    code: str
    kwargs: dict


@dataclass
class ParseResult:
    questions: list[ParsedQuestion]
    error: ParseError | None = None


def parse_questions_bulk(raw: str) -> ParseResult:
    """
    Формат:
      1. Вопрос
      A. вариант
      +B. правильный
      C. вариант

      2. Следующий вопрос
      +A. верный
      B. нет
    """
    text = (raw or "").strip()
    if not text:
        return ParseResult([], ParseError("questions_empty", {}))

    lines = text.splitlines()
    questions: list[ParsedQuestion] = []
    current_num: int | None = None
    current_text_parts: list[str] = []
    current_options: list[str] = []
    correct_index: int | None = None

    def flush() -> ParseError | None:
        nonlocal current_num, current_text_parts, current_options, correct_index
        if current_num is None:
            return None

        q_text = "\n".join(p for p in current_text_parts if p.strip()).strip()
        if not q_text:
            return ParseError("question_empty_text", {"n": current_num})
        if len(current_options) < 2:
            return ParseError(
                "question_min_options",
                {"n": current_num, "count": len(current_options)},
            )
        if correct_index is None:
            return ParseError("question_no_correct", {"n": current_num})

        questions.append(
            ParsedQuestion(
                number=current_num,
                text=q_text,
                options=list(current_options),
                correct_index=correct_index,
            )
        )
        current_num = None
        current_text_parts = []
        current_options = []
        correct_index = None
        return None

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        q_match = QUESTION_RE.match(line)
        if q_match:
            err = flush()
            if err:
                return ParseResult([], err)
            current_num = int(q_match.group(1))
            current_text_parts = [q_match.group(2).strip()]
            current_options = []
            correct_index = None
            continue

        opt_match = OPTION_RE.match(line)
        if opt_match and current_num is not None:
            is_correct = opt_match.group(1) == "+"
            opt_text = opt_match.group(3).strip()
            if not opt_text:
                return ParseResult(
                    [], ParseError("option_empty", {"n": current_num})
                )
            # «+» в конце текста варианта на всякий случай не считаем
            if is_correct:
                if correct_index is not None:
                    return ParseResult(
                        [],
                        ParseError("question_many_correct", {"n": current_num}),
                    )
                correct_index = len(current_options)
            current_options.append(opt_text)
            continue

        # Продолжение текста вопроса (многострочный)
        if current_num is not None and not current_options:
            current_text_parts.append(line)
            continue

        if current_num is None:
            return ParseResult([], ParseError("questions_bad_format", {}))

        return ParseResult(
            [],
            ParseError("questions_bad_line", {"n": current_num, "line": line[:80]}),
        )

    err = flush()
    if err:
        return ParseResult([], err)

    if not questions:
        return ParseResult([], ParseError("questions_empty", {}))

    # Перенумеруем по порядку в сообщении (1..N)
    for i, q in enumerate(questions, start=1):
        q.number = i

    return ParseResult(questions)


def format_questions_preview(questions: list[ParsedQuestion], *, limit: int = 12) -> str:
    lines: list[str] = []
    shown = questions[:limit]
    for q in shown:
        lines.append(f"{q.number}. {q.text}")
        for i, opt in enumerate(q.options):
            mark = "+" if i == q.correct_index else ""
            letter = chr(ord("A") + i) if i < 26 else str(i + 1)
            lines.append(f"{mark}{letter}. {opt}")
        lines.append("")
    if len(questions) > limit:
        lines.append(f"… и ещё {len(questions) - limit}")
    return "\n".join(lines).strip()
