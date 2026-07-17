TEXTS = {
    "ru": {
        "choose_lang": "Выберите язык / Tilni tanlang:",
        "lang_ru": "🇷🇺 Русский",
        "lang_uz": "🇺🇿 O'zbek",
        "welcome": "Добро пожаловать! Я помогу создать тест для вашего канала.\n\nНажмите /start чтобы начать.",
        "enter_test_name": "Введите название теста:",
        "enter_questions_bulk": (
            "Отправьте вопросы одним или несколькими сообщениями (2–3 и больше) в формате:\n\n"
            "1. Текст вопроса\n"
            "A. вариант\n"
            "B. вариант\n"
            "+C. правильный вариант\n\n"
            "2. Следующий вопрос\n"
            "+A. правильный\n"
            "B. другой\n\n"
            "Правильный ответ — знак + перед буквой (+A. …).\n"
            "Когда все куски отправлены — нажмите «Готово» или напишите: готово"
        ),
        "btn_questions_done": "✅ Готово — сохранить вопросы",
        "questions_chunk_ok": (
            "✅ Кусок принят. Собрано вопросов: {count}.\n"
            "Можете отправить ещё сообщение или нажмите «Готово»."
        ),
        "questions_chunk_ok_partial": (
            "✅ Кусок принят. Целиком собрано: {count}.\n"
            "Последний вопрос ещё неполный — дошлите продолжение, затем «Готово»."
        ),
        "questions_chunk_partial": (
            "✅ Кусок принят (вопрос ещё неполный).\n"
            "Дошлите продолжение, затем нажмите «Готово»."
        ),
        "questions_waiting_more": (
            "Сейчас собрано вопросов: {count}.\n"
            "Дошлите исправление/продолжение или нажмите «Готово», когда всё готово."
        ),
        "questions_continue_hint": (
            "Исправьте и отправьте этот кусок снова.\n"
            "Уже принятые сообщения сохранены."
        ),
        "questions_accepted": "✅ Принято вопросов: {count}. Проверьте:",
        "questions_empty": "Не удалось найти вопросы. Проверьте формат.",
        "questions_bad_format": "Сообщение должно начинаться с номера вопроса, например: 1. Текст",
        "questions_bad_line": "Вопрос {n}: непонятная строка «{line}».",
        "question_empty_text": "Вопрос {n}: пустой текст вопроса.",
        "question_min_options": "Вопрос {n}: нужно минимум 2 варианта (сейчас {count}).",
        "question_no_correct": "Вопрос {n}: отметьте правильный ответ знаком +, например: +A. ответ",
        "question_many_correct": "Вопрос {n}: отмечен больше одного правильного ответа (+).",
        "option_empty": "Вопрос {n}: пустой вариант ответа.",
        "questions_save_error": "Не удалось сохранить вопросы. Попробуйте ещё раз или /cancel.",
        "invalid_number": "Пожалуйста, введите целое число больше 0.",
        "choose_time": "Выберите время на каждый вопрос:",
        "time_none": "Без ограничения",
        "time_10": "10 сек",
        "time_15": "15 сек",
        "time_20": "20 сек",
        "time_25": "25 сек",
        "time_30": "30 сек",
        "choose_results_delay": "Когда отправить результаты?",
        "delay_manual": "Без таймера (/results)",
        "delay_10m": "10 минут",
        "delay_1h": "1 час",
        "delay_5h": "5 часов",
        "delay_10h": "10 часов",
        "delay_15h": "15 часов",
        "delay_20h": "20 часов",
        "test_ready": "✅ Тест «{name}» создан!\n\nОтправьте это сообщение в канал:\n\n⏱ Результаты придут автоматически по истечении выбранного времени.",
        "test_ready_manual": "✅ Тест «{name}» создан!\n\nОтправьте сообщение со ссылкой в канал.\n\n📋 Результаты — когда вы напишете /results",
        "answer_options": "Варианты ответа:",
        "choose_answer_btn": "Нажмите букву ответа на кнопках ниже:",
        "enter_full_name": "Введите ваше полное ФИО (фамилия, имя, отчество):",
        "invalid_full_name": "Укажите полное ФИО — минимум имя и фамилия (например: Иванова Мария Сергеевна).",
        "test_link_text": "📝 Пройдите тест «{name}»\n\n{link}",
        "test_finished": "Тест «{name}» завершён. Новые участники не принимаются.",
        "already_participated": "Вы уже проходили этот тест.",
        "test_not_found": "Тест не найден или уже завершён.",
        "test_invite": "📝 Тест «{name}»\n\nВопросов: {total}\n\nНажмите «Начать», когда будете готовы.",
        "btn_start": "▶️ Начать",
        "questions_missing": "В этом тесте нет вопросов. Попросите создателя сделать тест заново.",
        "test_start_error": "Не удалось начать тест. Нажмите /start и откройте ссылку снова.",
        "start_test": "Начинаем тест «{name}»!\n\nВопрос 1 из {total}:",
        "question_header": "Вопрос {n} из {total}:",
        "time_left": "⏱ Осталось: {sec} сек",
        "time_up": "Время вышло!",
        "test_complete_participant": "Вы завершили тест! Результаты будут объявлены позже.",
        "results_title": "🏆 Результаты теста «{name}»\n\nУчастников: {count}\n",
        "no_participants": "Никто не прошёл тест.",
        "medal_1": "🥇 1 место — {name} ({score}/{total}, {time})",
        "medal_2": "🥈 2 место — {name} ({score}/{total}, {time})",
        "medal_3": "🥉 3 место — {name} ({score}/{total}, {time})",
        "place_n": "{n}. {name} ({score}/{total}, {time})",
        "time_format_min_sec": "{min} мин {sec} сек",
        "time_format_sec": "{sec} сек",
        "ranking_by_time_note": "При одинаковом счёте выше тот, кто быстрее прошёл тест.",
        "cancelled": "Создание теста отменено.",
        "session_restart": "Сессия создания сброшена. Нажмите /start и создайте тест заново.",
        "callback_error": "Не удалось обработать нажатие. Нажмите /start и попробуйте снова.",
        "create_new": "Создать новый тест",
        "no_active_tests": "У вас нет активных тестов. Создайте тест через /start",
        "choose_test_for_results": "Выберите тест для досрочной выдачи результатов:",
        "choose_test_for_progress": "Выберите тест для промежуточных результатов:",
        "results_sent_early": "Тест «{name}» завершён. Результаты отправлены выше.",
        "interim_results_title": "📊 Промежуточные результаты «{name}»\n\nЗавершили тест: {count}\n",
        "interim_results_note": "ℹ️ Тест ещё идёт — новые участники могут проходить. Для финала: /results",
        "interim_in_progress": "Сейчас проходят (не закончили): {count}",
        "interim_results_sent": "Промежуточные результаты по тесту «{name}» отправлены выше.",
        "progress_wait": "⏳ Собираю промежуточные результаты…",
        "progress_error": "Не удалось отправить результаты. Попробуйте через 2–3 минуты или напишите /progress с номером теста.",
        "results_send_error": "Не удалось отправить результаты. Тест ещё открыт — подождите минуту и снова напишите /results",
        "results_resent": "✅ Полный список результатов отправлен выше (все участники).",
        "progress_fallback": "Полный список слишком длинный — отправила краткую сводку выше.",
        "interim_stats_short": "📊 «{name}»\n\n✅ Закончили: {finished}\n⏳ Ещё решают: {in_progress}\n📝 Вопросов в тесте: {total}\n\nℹ️ Тест продолжается. Для финала: /results",
        "results_truncated": "… и ещё {count} участник(ов) (список сокращён из‑за лимита Telegram).",
        "test_already_finished": "Этот тест уже завершён.",
        "test_not_active": "Этот тест не активен (уже завершён или не найден).",
        "not_test_creator": "Вы не являетесь создателем этого теста.",
        "reopen_usage": "Чтобы возобновить закрытый тест, напишите: /reopen ID\nНапример: /reopen 15",
        "reopen_done": "✅ Тест «{name}» снова открыт.\n\nСсылка прежняя: https://t.me/Testlaruz1Bot?start=test_{id}\n\nАвто-таймер результатов отключён. Для финала снова напишите /results.",
        "reopen_already_active": "Тест «{name}» уже активен.",
        "reopen_error": "Не удалось возобновить тест. Попробуйте ещё раз через минуту.",
    },
    "uz": {
        "choose_lang": "Tilni tanlang / Выберите язык:",
        "lang_ru": "🇷🇺 Rus",
        "lang_uz": "🇺🇿 O'zbek",
        "welcome": "Xush kelibsiz! Kanalingiz uchun test yaratishga yordam beraman.\n\nBoshlash uchun /start bosing.",
        "enter_test_name": "Test nomini kiriting:",
        "enter_questions_bulk": (
            "Savollarni bitta yoki bir nechta xabarda (2–3 va undan ko'p) yuboring:\n\n"
            "1. Savol matni\n"
            "A. variant\n"
            "B. variant\n"
            "+C. to'g'ri variant\n\n"
            "2. Keyingi savol\n"
            "+A. to'g'ri\n"
            "B. boshqa\n\n"
            "To'g'ri javob — harf oldidan + (+A. …).\n"
            "Hammasi yuborilgach «Tayyor» tugmasini bosing yoki yozing: tayyor"
        ),
        "btn_questions_done": "✅ Tayyor — savollarni saqlash",
        "questions_chunk_ok": (
            "✅ Qism qabul qilindi. Jami savollar: {count}.\n"
            "Yana xabar yuborishingiz yoki «Tayyor» bosishingiz mumkin."
        ),
        "questions_chunk_ok_partial": (
            "✅ Qism qabul qilindi. To'liq yig'ilgan: {count}.\n"
            "Oxirgi savol hali to'liq emas — davomini yuboring, so'ng «Tayyor»."
        ),
        "questions_chunk_partial": (
            "✅ Qism qabul qilindi (savol hali to'liq emas).\n"
            "Davomini yuboring, so'ng «Tayyor» bosing."
        ),
        "questions_waiting_more": (
            "Hozir yig'ilgan savollar: {count}.\n"
            "Tuzatish/davom yuboring yoki hammasi tayyor bo'lsa «Tayyor» bosing."
        ),
        "questions_continue_hint": (
            "Shu qismni tuzatib qayta yuboring.\n"
            "Oldingi qabul qilingan xabarlar saqlanadi."
        ),
        "questions_accepted": "✅ Qabul qilingan savollar: {count}. Tekshiring:",
        "questions_empty": "Savollar topilmadi. Formatni tekshiring.",
        "questions_bad_format": "Xabar savol raqami bilan boshlanishi kerak, masalan: 1. Matn",
        "questions_bad_line": "Savol {n}: tushunarsiz qator «{line}».",
        "question_empty_text": "Savol {n}: savol matni bo'sh.",
        "question_min_options": "Savol {n}: kamida 2 ta variant kerak (hozir {count}).",
        "question_no_correct": "Savol {n}: to'g'ri javobni + bilan belgilang, masalan: +A. javob",
        "question_many_correct": "Savol {n}: bir nechta to'g'ri javob (+) belgilangan.",
        "option_empty": "Savol {n}: javob varianti bo'sh.",
        "questions_save_error": "Savollarni saqlab bo'lmadi. Qayta urinib ko'ring yoki /cancel.",
        "invalid_number": "Iltimos, 0 dan katta butun son kiriting.",
        "choose_time": "Har bir savol uchun vaqtni tanlang:",
        "time_none": "Cheklovsiz",
        "time_10": "10 son",
        "time_15": "15 son",
        "time_20": "20 son",
        "time_25": "25 son",
        "time_30": "30 son",
        "choose_results_delay": "Natijalar qachon yuborilsin?",
        "delay_manual": "Vaqt yo'q (/results)",
        "delay_10m": "10 daqiqa",
        "delay_1h": "1 soat",
        "delay_5h": "5 soat",
        "delay_10h": "10 soat",
        "delay_15h": "15 soat",
        "delay_20h": "20 soat",
        "test_ready": "✅ «{name}» testi yaratildi!\n\nUshbu xabarni kanalga yuboring:\n\n⏱ Natijalar tanlangan vaqtdan keyin avtomatik keladi.",
        "test_ready_manual": "✅ «{name}» testi yaratildi!\n\nHavolani kanalga yuboring.\n\n📋 Natijalar — /results buyrug'i bilan",
        "answer_options": "Javob variantlari:",
        "choose_answer_btn": "Quyidagi tugmalardan javob harfini bosing:",
        "enter_full_name": "To'liq F.I.O. ingizni kiriting (familiya, ism, otasining ismi):",
        "invalid_full_name": "To'liq F.I.O. kiriting — kamida familiya va ism (masalan: Karimova Dilnoza Sardor qizi).",
        "test_link_text": "📝 «{name}» testini yeching\n\n{link}",
        "test_finished": "«{name}» testi tugadi. Yangi ishtirokchilar qabul qilinmaydi.",
        "already_participated": "Siz bu testni allaqachon yechgansiz.",
        "test_not_found": "Test topilmadi yoki allaqachon tugagan.",
        "test_invite": "📝 «{name}» testi\n\nSavollar: {total}\n\nTayyor bo'lgach «Boshlash» tugmasini bosing.",
        "btn_start": "▶️ Boshlash",
        "questions_missing": "Bu testda savollar yo'q. Yaratuvchidan testni qayta yaratishni so'rang.",
        "test_start_error": "Testni boshlab bo'lmadi. /start bosing va havolani qayta oching.",
        "start_test": "«{name}» testi boshlanmoqda!\n\nSavol 1 / {total}:",
        "question_header": "Savol {n} / {total}:",
        "time_left": "⏱ Qoldi: {sec} son",
        "time_up": "Vaqt tugadi!",
        "test_complete_participant": "Testni tugatdingiz! Natijalar keyinroq e'lon qilinadi.",
        "results_title": "🏆 «{name}» testi natijalari\n\nIshtirokchilar: {count}\n",
        "no_participants": "Hech kim testni yechmadi.",
        "medal_1": "🥇 1-o'rin — {name} ({score}/{total}, {time})",
        "medal_2": "🥈 2-o'rin — {name} ({score}/{total}, {time})",
        "medal_3": "🥉 3-o'rin — {name} ({score}/{total}, {time})",
        "place_n": "{n}. {name} ({score}/{total}, {time})",
        "time_format_min_sec": "{min} daq {sec} son",
        "time_format_sec": "{sec} son",
        "ranking_by_time_note": "Ball teng bo'lsa, tezroq yechgan yuqorida turadi.",
        "cancelled": "Test yaratish bekor qilindi.",
        "session_restart": "Yaratish sessiyasi tozalandi. /start bosing va testni qaytadan yarating.",
        "callback_error": "Tugmani qayta ishlab bo'lmadi. /start bosing va qayta urinib ko'ring.",
        "create_new": "Yangi test yaratish",
        "no_active_tests": "Sizda faol testlar yo'q. /start orqali test yarating",
        "choose_test_for_results": "Natijalarni erta olish uchun testni tanlang:",
        "choose_test_for_progress": "Oraliq natijalar uchun testni tanlang:",
        "results_sent_early": "«{name}» testi tugadi. Natijalar yuqorida yuborildi.",
        "interim_results_title": "📊 «{name}» oraliq natijalari\n\nTugatganlar: {count}\n",
        "interim_results_note": "ℹ️ Test hali davom etmoqda — yangi ishtirokchilar kira oladi. Yakun: /results",
        "interim_in_progress": "Hozir yechmoqda (tugatmagan): {count}",
        "interim_results_sent": "«{name}» bo'yicha oraliq natijalar yuqorida yuborildi.",
        "progress_wait": "⏳ Oraliq natijalar yig'ilmoqda…",
        "progress_error": "Natijalarni yuborib bo'lmadi. 2–3 daqiqadan keyin qayta urinib ko'ring yoki /progress <test_id> yozing.",
        "results_send_error": "Natijalarni yuborib bo'lmadi. Test hali ochiq — 1 daqiqa kutib, /results ni qayta yuboring",
        "results_resent": "✅ To'liq natijalar ro'yxati yuqorida yuborildi (barcha ishtirokchilar).",
        "progress_fallback": "To'liq ro'yxat juda uzun — qisqa xulosa yuqorida.",
        "interim_stats_short": "📊 «{name}»\n\n✅ Tugatganlar: {finished}\n⏳ Hali yechmoqda: {in_progress}\n📝 Savollar: {total}\n\nℹ️ Test davom etmoqda. Yakun: /results",
        "results_truncated": "… va yana {count} ishtirokchi (ro'yxat Telegram limiti tufayli qisqartirildi).",
        "test_already_finished": "Bu test allaqachon tugagan.",
        "test_not_active": "Bu test faol emas (tugagan yoki topilmagan).",
        "not_test_creator": "Siz bu testning yaratuvchisi emassiz.",
        "reopen_usage": "Yopilgan testni qayta ochish uchun yozing: /reopen ID\nMasalan: /reopen 15",
        "reopen_done": "✅ «{name}» testi qayta ochildi.\n\nHavola avvalgidek: https://t.me/Testlaruz1Bot?start=test_{id}\n\nNatijalar avto-taymeri o'chirildi. Yakunlash uchun yana /results yozing.",
        "reopen_already_active": "«{name}» testi allaqachon faol.",
        "reopen_error": "Testni qayta ochib bo'lmadi. Bir daqiqadan keyin qayta urinib ko'ring.",
    },
}


def t(lang: str, key: str, **kwargs) -> str:
    text = TEXTS.get(lang, TEXTS["ru"]).get(key, key)
    return text.format(**kwargs) if kwargs else text
