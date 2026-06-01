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


def option_label(index: int) -> str:
    """A, B, C, … Z, AA, AB, … for option index 0, 1, 2, …"""
    if index < 0:
        return "?"
    label = ""
    n = index
    while True:
        label = chr(ord("A") + n % 26) + label
        n = n // 26 - 1
        if n < 0:
            break
    return label


def format_duration(seconds: int | None, lang: str) -> str:
    if seconds is None:
        return "—"
    total = max(0, int(seconds))
    minutes, secs = divmod(total, 60)
    if minutes > 0:
        return t(lang, "time_format_min_sec", min=minutes, sec=secs)
    return t(lang, "time_format_sec", sec=secs)


def format_results(
    lang: str,
    test_name: str,
    participants: list,
    total_q: int,
    *,
    interim: bool = False,
) -> str:
    title_key = "interim_results_title" if interim else "results_title"
    if not participants:
        text = t(lang, title_key, name=test_name, count=0) + t(lang, "no_participants")
        if interim:
            text += "\n\n" + t(lang, "interim_results_note")
        return text

    lines = [
        t(lang, title_key, name=test_name, count=len(participants)),
        t(lang, "ranking_by_time_note"),
        "",
    ]
    medals = ["medal_1", "medal_2", "medal_3"]
    for i, p in enumerate(participants):
        time_str = format_duration(p.get("duration_sec"), lang)
        if i < 3:
            lines.append(
                t(
                    lang,
                    medals[i],
                    name=p["display_name"],
                    score=p["score"],
                    total=total_q,
                    time=time_str,
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
                    time=time_str,
                )
            )
    if interim:
        lines.append("")
        lines.append(t(lang, "interim_results_note"))
    return "\n".join(lines)
