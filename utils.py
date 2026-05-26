from telegram import User

from locales import t


def display_name(user: User) -> str:
    if user.username:
        return f"@{user.username}"
    parts = [user.first_name or "", user.last_name or ""]
    name = " ".join(p for p in parts if p).strip()
    return name or str(user.id)


def test_deep_link(bot_username: str, test_id: int) -> str:
    return f"https://t.me/{bot_username}?start=test_{test_id}"


def format_results(lang: str, test_name: str, participants: list, total_q: int) -> str:
    if not participants:
        return t(lang, "results_title", name=test_name, count=0) + t(lang, "no_participants")

    lines = [t(lang, "results_title", name=test_name, count=len(participants))]
    medals = ["medal_1", "medal_2", "medal_3"]
    for i, p in enumerate(participants):
        if i < 3:
            lines.append(
                t(
                    lang,
                    medals[i],
                    name=p["display_name"],
                    score=p["score"],
                    total=total_q,
                )
            )
        else:
            lines.append(
                t(
                    lang,
                    "place_n",
                    n=i + 1,
                    name=p["display_name"],
                    score=p["score"],
                    total=total_q,
                )
            )
    return "\n".join(lines)
