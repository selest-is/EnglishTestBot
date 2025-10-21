#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import csv
from datetime import datetime
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler,
    ConversationHandler
)

# 🔑 Укажи свой токен бота (или установи переменную окружения BOT_TOKEN)
BOT_TOKEN = os.environ.get("BOT_TOKEN", "ВСТАВЬ_СВОЙ_ТОКЕН_СЮДА")

RESULTS_CSV = "quiz_results.csv"
LOGFILE = "quiz_bot.log"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    filename=LOGFILE
)
logger = logging.getLogger(__name__)

QUESTIONS = [
    ("1. My name ___ John.", ["a) are", "b) am", "c) is"]),
    ("2. Where ___ you from?", ["a) are", "b) is", "c) be"]),
    ("3. I usually ___ breakfast at 8 o’clock.", ["a) have", "b) has", "c) having"]),
    ("4. She can ___ the guitar.", ["a) play", "b) playing", "c) plays"]),
    ("5. There ___ any apples on the table.", ["a) isn’t", "b) aren’t", "c) don’t"]),
    ("6. I go to school ___ bus.", ["a) in", "b) on", "c) by"]),
    ("7. Where ___ they live?", ["a) do", "b) does", "c) is"]),
    ("8. There is ___ apple on the table.", ["a) an", "b) a", "c) the"]),
    ("9. My father ___ in a bank.", ["a) works", "b) work", "c) working"]),
    ("10. I have lived here ___ five years.", ["a) since", "b) for", "c) from"]),
    ("11. He doesn’t like coffee, and I don’t like it ___.", ["a) too", "b) either", "c) also"]),
    ("12. If it ___ tomorrow, we will stay at home.", ["a) rains", "b) will rain", "c) rain"]),
    ("13. I was very tired because I ___ all day.", ["a) worked", "b) have worked", "c) had worked"]),
    ("14. This movie is ___ interesting than the last one.", ["a) most", "b) more", "c) much"]),
    ("15. We have to go now, there isn’t ___ time left.", ["a) much", "b) many", "c) few"]),
    ("16. I was tired, so I ___ to bed early.", ["a) go", "b) went", "c) going"]),
    ("17. He ___ speak English very well.", ["a) cans", "b) can", "c) can to"]),
    ("18. I’m ___ than my brother.", ["a) taller", "b) the tallest", "c) more tall"]),
    ("19. She asked me if I ___ help her with her homework.", ["a) can", "b) could", "c) will"]),
    ("20. I wish I ___ more time to travel.", ["a) have", "b) had", "c) would have"]),
    ("21. He’s used to ___ up early every morning.", ["a) get", "b) getting", "c) got"]),
    ("22. By the time we arrived, the film ___.", ["a) already started", "b) had already started", "c) has already started"]),
    ("23. If I ___ you, I’d take that job.", ["a) am", "b) was", "c) were"]),
    ("24. You ___ smoke here - it’s not allowed.", ["a) don’t have to", "b) mustn’t", "c) can"]),
    ("25. She said she ___ call me later.", ["a) will", "b) would", "c) can"])
]

ANSWER_KEY = {
    1: "c",2: "a",3: "a",4: "a",5: "b",
    6:"c",7:"a",8:"a",9:"a",10:"b",
    11:"b",12:"a",13:"b",14:"b",15:"a",
    16:"b",17:"b",18:"a",19:"b",20:"b",
    21:"b",22:"b",23:"c",24:"b",25:"b"
}

META = {
  1:  {"topic":"to be / subject-verb agreement","expl":"Используется 'is' с именем и с He/She/It.","link":"https://learnenglish.britishcouncil.org/grammar/intermediate-to-upper-intermediate/to-be"},
  2:  {"topic":"questions with to be","expl":"Вопросы с 'you' требуют 'are'.","link":"https://www.perfect-english-grammar.com/questions-with-to-be.html"},
  3:  {"topic":"present simple: verb forms","expl":"Для 'I' используем 'have breakfast'.","link":"https://learnenglish.britishcouncil.org/grammar/english-grammar-reference/present-simple"},
  4:  {"topic":"modal + base verb","expl":"После 'can' идёт инфинитив без 'to'.","link":"https://www.englishpage.com/modals/modalhelp.html"},
  5:  {"topic":"there is/there are","expl":"Для множественного числа: 'There aren't any apples.'","link":"https://www.perfect-english-grammar.com/there-is-there-are.html"},
}

ASKING = 1

def build_keyboard(options):
    keyboard = []
    for opt in options:
        letter = opt.strip()[0].lower()
        keyboard.append([InlineKeyboardButton(opt, callback_data=letter)])
    return InlineKeyboardMarkup(keyboard)

def letter_from_choice(text):
    if not text:
        return ""
    s = str(text).strip().lower()
    return s[0] if s[0] in ("a","b","c") else ""

def grade_answers(normalized_list):
    correct_count = 0
    feedback = []
    topics_count = {}
    for i, letter in enumerate(normalized_list, start=1):
        correct = ANSWER_KEY.get(i)
        is_cor = (letter == correct)
        if is_cor:
            correct_count += 1
            status = "✅ OK"
        else:
            status = "❌ WRONG"
            meta = META.get(i, {})
            topics_count[ meta.get("topic", "General") ] = topics_count.get(meta.get("topic","General"), 0) + 1
        meta = META.get(i, {})
        entry = f"Q{i}: {status}  (you: {letter or '—'}  |  correct: {correct})\n• {meta.get('topic','')}"
        feedback.append(entry)
    score = correct_count
    if score <= 10:
        level = "A1"
    elif score <= 15:
        level = "A2"
    elif score <= 20:
        level = "B1"
    else:
        level = "B2"
    sorted_topics = sorted(topics_count.items(), key=lambda x: x[1], reverse=True)
    top3 = [t for t,c in sorted_topics[:3]]
    top3_str = "; ".join(top3) if top3 else "None"
    return {"score": score, "level": level, "feedback_list": feedback, "top_topics": top3_str}

def save_result_to_csv(rowdict):
    header = ["timestamp","chat_id","username","normalized_answers","score","level","top_topics"]
    file_exists = os.path.isfile(RESULTS_CSV)
    with open(RESULTS_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            "timestamp": rowdict.get("timestamp"),
            "chat_id": rowdict.get("chat_id"),
            "username": rowdict.get("username"),
            "normalized_answers": ",".join(rowdict.get("normalized", [])),
            "score": rowdict.get("score"),
            "level": rowdict.get("level"),
            "top_topics": rowdict.get("top_topics")
        })

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (
        f"👋 Привет, {user.first_name or 'друг'}!\n\n"
        "🎯 Это — English Placement Bot.\n\n"
        "Команды:\n"
        "• /test — пройти быстрый тест (25 вопросов)\n"
        "• /cancel — отменить текущий тест\n\n"
        "Нажми /test, чтобы начать. Удачи! 🚀"
    )
    await update.message.reply_text(text)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🛑 Тест отменён. Напиши /test, чтобы начать снова.")
    context.user_data.clear()
    return ConversationHandler.END

async def test_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["answers"] = []
    context.user_data["q_index"] = 0
    context.user_data["started_at"] = datetime.utcnow().isoformat()
    q_text, opts = QUESTIONS[0]
    intro = f"✅ Начинаем тест!\n\n{q_text}"
    await update.message.reply_text(intro, reply_markup=build_keyboard(opts))
    return ASKING

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    letter = letter_from_choice(data)
    answers = context.user_data.get("answers", [])
    answers.append(letter)
    context.user_data["answers"] = answers
    q_idx = context.user_data.get("q_index", 0) + 1
    context.user_data["q_index"] = q_idx

    if q_idx >= len(QUESTIONS):
        res = grade_answers(context.user_data["answers"])
        score = res["score"]
        level = res["level"]
        top = res["top_topics"]
        feedback_short = f"🏁 Готово!\n\n📊 Score: {score}/25   |   Level: {level}\n\n📚 Top topics: {top}"
        await query.edit_message_text(feedback_short)
        row = {
            "timestamp": context.user_data.get("started_at"),
            "chat_id": update.effective_user.id,
            "username": update.effective_user.username or "",
            "normalized": context.user_data.get("answers", []),
            "score": score,
            "level": level,
            "top_topics": top
        }
        save_result_to_csv(row)
        context.user_data.clear()
        return ConversationHandler.END
    else:
        q_text, opts = QUESTIONS[q_idx]
        await query.edit_message_text(f"{q_text}", reply_markup=build_keyboard(opts))
        return ASKING

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Не понял команду. Используй /test чтобы начать или /cancel чтобы выйти.")

def main():
    if not BOT_TOKEN or BOT_TOKEN == "ВСТАВЬ_СВОЙ_ТОКЕН_СЮДА":
        print("❌ ERROR: Укажи BOT_TOKEN в коде или переменной окружения.")
        return

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler("test", test_start)],
        states={ASKING: [CallbackQueryHandler(button_handler)]},
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv)
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("unknown", unknown))
    print("🚀 Bot started. Press Ctrl+C to stop.")
    app.run_polling()

if __name__ == "__main__":
    main()
