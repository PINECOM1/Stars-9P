“””
Stars 9P — Telegram Bot
Сохраняет данные игроков в Google Sheets
Команды: /start, /balance, /stats, /top
“””

import logging
import json
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ══════════════════════════════════════════

# НАСТРОЙКИ

# ══════════════════════════════════════════

BOT_TOKEN   = “8727347320:AAGiDIFkoxEIcLUWqfVYjd4HddBnokhU4_g”
SHEET_ID    = “11HPLIX-kFJ0qVud88DLGpDRuYUmw_oXJiVHZ4g_JT2E”
CREDS_FILE  = “credentials.json”   # файл ключей Google Service Account (см. инструкцию)

# ══════════════════════════════════════════

# GOOGLE SHEETS

# ══════════════════════════════════════════

def get_sheet():
scope = [
“https://spreadsheets.google.com/feeds”,
“https://www.googleapis.com/auth/drive”
]
creds = ServiceAccountCredentials.from_json_keyfile_name(CREDS_FILE, scope)
client = gspread.authorize(creds)
spreadsheet = client.open_by_key(SHEET_ID)

```
# Создаём листы если их нет
sheet_names = [s.title for s in spreadsheet.worksheets()]

if "Players" not in sheet_names:
    ws = spreadsheet.add_worksheet(title="Players", rows=1000, cols=10)
    ws.append_row(["user_id", "username", "first_name", "ton_balance",
                    "stars_balance", "games", "wins", "max_mult",
                    "total_deposited", "last_seen"])
if "Transactions" not in sheet_names:
    ws = spreadsheet.add_worksheet(title="Transactions", rows=5000, cols=6)
    ws.append_row(["timestamp", "user_id", "username", "type", "amount", "currency"])

return spreadsheet
```

def find_player_row(sheet, user_id):
“”“Найти строку игрока по user_id, вернуть номер строки или None”””
try:
cell = sheet.find(str(user_id), in_column=1)
return cell.row
except:
return None

def get_player(sheet, user_id):
“”“Получить данные игрока как словарь”””
row = find_player_row(sheet, user_id)
if not row:
return None
values = sheet.row_values(row)
keys = [“user_id”,“username”,“first_name”,“ton_balance”,“stars_balance”,
“games”,“wins”,“max_mult”,“total_deposited”,“last_seen”]
return dict(zip(keys, values + [””]*(len(keys)-len(values))))

def upsert_player(sheet, user_id, username, first_name, data: dict):
“”“Создать или обновить игрока”””
row = find_player_row(sheet, user_id)
now = datetime.now().strftime(”%Y-%m-%d %H:%M:%S”)

```
if row:
    # Обновляем существующего
    existing = sheet.row_values(row)
    keys = ["user_id","username","first_name","ton_balance","stars_balance",
            "games","wins","max_mult","total_deposited","last_seen"]
    player = dict(zip(keys, existing + [""]*(len(keys)-len(existing))))
    player.update(data)
    player["username"]   = username or player.get("username","")
    player["first_name"] = first_name or player.get("first_name","")
    player["last_seen"]  = now
    sheet.update(f"A{row}:J{row}", [[
        player["user_id"], player["username"], player["first_name"],
        player["ton_balance"], player["stars_balance"],
        player["games"], player["wins"], player["max_mult"],
        player["total_deposited"], player["last_seen"]
    ]])
else:
    # Новый игрок
    sheet.append_row([
        str(user_id),
        username or "",
        first_name or "",
        data.get("ton_balance", 0.10),
        data.get("stars_balance", 0),
        data.get("games", 0),
        data.get("wins", 0),
        data.get("max_mult", 0),
        data.get("total_deposited", 0),
        now
    ])
```

def log_transaction(sheet, user_id, username, tx_type, amount, currency):
“”“Записать транзакцию”””
now = datetime.now().strftime(”%Y-%m-%d %H:%M:%S”)
sheet.append_row([now, str(user_id), username or “”, tx_type, amount, currency])

# ══════════════════════════════════════════

# КОМАНДЫ БОТА

# ══════════════════════════════════════════

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(**name**)

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
user = update.effective_user
args = ctx.args  # параметры после /start

```
try:
    sp = get_sheet()
    players_ws = sp.worksheet("Players")

    # Регистрируем игрока если нет
    existing = get_player(players_ws, user.id)
    if not existing:
        upsert_player(players_ws, user.id, user.username, user.first_name, {
            "ton_balance": 0.10,
            "stars_balance": 0,
            "games": 0, "wins": 0, "max_mult": 0,
            "total_deposited": 0
        })
        is_new = True
    else:
        upsert_player(players_ws, user.id, user.username, user.first_name, {})
        is_new = False

    # Обработка депозита через Stars (/start dep_50_userid)
    if args and args[0].startswith("dep_"):
        parts = args[0].split("_")
        if len(parts) >= 2:
            stars_amount = int(parts[1])
            ton_equiv = round(stars_amount / 100 * 0.1, 4)

            # Создаём invoice для оплаты Stars
            await ctx.bot.send_invoice(
                chat_id=update.effective_chat.id,
                title=f"Пополнение {stars_amount} ⭐",
                description=f"Пополнение игрового баланса Stars 9P\n"
                            f"Вы получите: {ton_equiv} TON игрового баланса",
                payload=f"deposit_{user.id}_{stars_amount}",
                provider_token="",   # пусто для Telegram Stars
                currency="XTR",      # XTR = Telegram Stars
                prices=[{"label": f"{stars_amount} Stars", "amount": stars_amount}],
                photo_url="https://pinecom1.github.io/Stars-9P/icon.png",
                photo_width=512,
                photo_height=512,
            )
            return

    # Приветственное сообщение
    greeting = "🎉 Добро пожаловать!" if is_new else f"👋 С возвращением, {user.first_name}!"
    player = get_player(players_ws, user.id)

    keyboard = [[
        InlineKeyboardButton("🚀 Играть", url="https://pinecom1.github.io/Stars-9P"),
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"{greeting}\n\n"
        f"💎 TON баланс: `{float(player.get('ton_balance',0.10)):.4f}`\n"
        f"⭐ Stars: `{player.get('stars_balance',0)}`\n"
        f"🎮 Игр сыграно: `{player.get('games',0)}`\n\n"
        f"Нажми кнопку чтобы начать игру! 🎰",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

except Exception as e:
    logger.error(f"start error: {e}")
    await update.message.reply_text(
        f"👋 Привет, {user.first_name}!\n\n"
        f"🚀 Играть: https://pinecom1.github.io/Stars-9P"
    )
```

async def cmd_balance(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
user = update.effective_user
try:
sp = get_sheet()
player = get_player(sp.worksheet(“Players”), user.id)
if not player:
await update.message.reply_text(“Ты ещё не зарегистрирован. Напиши /start”)
return
await update.message.reply_text(
f”💼 *Твой баланс:*\n\n”
f”💎 TON: `{float(player.get('ton_balance',0)):.4f}`\n”
f”⭐ Stars: `{player.get('stars_balance',0)}`\n”
f”📊 Депозитов: `{float(player.get('total_deposited',0)):.2f} TON`”,
parse_mode=“Markdown”
)
except Exception as e:
logger.error(f”balance error: {e}”)
await update.message.reply_text(“Ошибка получения баланса. Попробуй позже.”)

async def cmd_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
user = update.effective_user
try:
sp = get_sheet()
player = get_player(sp.worksheet(“Players”), user.id)
if not player:
await update.message.reply_text(“Ты ещё не зарегистрирован. Напиши /start”)
return
games = int(player.get(“games”, 0) or 0)
wins  = int(player.get(“wins”, 0) or 0)
winrate = round(wins/games*100) if games > 0 else 0
await update.message.reply_text(
f”📊 *Твоя статистика:*\n\n”
f”🎮 Игр: `{games}`\n”
f”✅ Побед: `{wins}`\n”
f”📈 Винрейт: `{winrate}%`\n”
f”🏆 Макс. множитель: `{float(player.get('max_mult',0)):.2f}×`\n”
f”⏰ Последний вход: `{player.get('last_seen','—')}`”,
parse_mode=“Markdown”
)
except Exception as e:
logger.error(f”stats error: {e}”)
await update.message.reply_text(“Ошибка. Попробуй позже.”)

async def cmd_top(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
try:
sp = get_sheet()
ws = sp.worksheet(“Players”)
all_rows = ws.get_all_records()

```
    # Сортируем по Stars по убыванию
    top = sorted(all_rows, key=lambda x: int(x.get("stars_balance",0) or 0), reverse=True)[:10]

    text = "🏆 *Топ-10 игроков:*\n\n"
    medals = ["🥇","🥈","🥉"]
    for i, p in enumerate(top):
        medal = medals[i] if i < 3 else f"{i+1}."
        name = p.get("first_name") or p.get("username") or "Аноним"
        stars = int(p.get("stars_balance",0) or 0)
        text += f"{medal} {name} — `{stars:,} ⭐`\n"

    await update.message.reply_text(text, parse_mode="Markdown")
except Exception as e:
    logger.error(f"top error: {e}")
    await update.message.reply_text("Ошибка. Попробуй позже.")
```

# ── Обработка успешной оплаты Stars ──

async def pre_checkout(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
“”“Telegram требует подтвердить оплату в течение 10 секунд”””
await update.pre_checkout_query.answer(ok=True)

async def successful_payment(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
“”“Зачисляем баланс после успешной оплаты Stars”””
user = update.effective_user
payment = update.message.successful_payment
stars_paid = payment.total_amount   # количество Stars
payload    = payment.invoice_payload  # “deposit_{user_id}_{amount}”

```
ton_credit = round(stars_paid / 100 * 0.1, 4)

try:
    sp = get_sheet()
    players_ws = sp.worksheet("Players")
    txn_ws     = sp.worksheet("Transactions")

    player = get_player(players_ws, user.id)
    if player:
        new_ton   = round(float(player.get("ton_balance",0) or 0) + ton_credit, 4)
        new_stars = int(player.get("stars_balance",0) or 0)
        new_dep   = round(float(player.get("total_deposited",0) or 0) + ton_credit, 4)
        upsert_player(players_ws, user.id, user.username, user.first_name, {
            "ton_balance": new_ton,
            "stars_balance": new_stars,
            "total_deposited": new_dep
        })
    else:
        upsert_player(players_ws, user.id, user.username, user.first_name, {
            "ton_balance": ton_credit,
            "stars_balance": 0,
            "total_deposited": ton_credit
        })

    # Логируем транзакцию
    log_transaction(txn_ws, user.id, user.username, "deposit_stars", stars_paid, "XTR")

    await update.message.reply_text(
        f"✅ *Оплата получена!*\n\n"
        f"⭐ Оплачено: `{stars_paid} Stars`\n"
        f"💎 Зачислено: `{ton_credit} TON`\n\n"
        f"Баланс обновлён в игре! 🚀",
        parse_mode="Markdown"
    )
except Exception as e:
    logger.error(f"payment error: {e}")
    await update.message.reply_text(
        f"✅ Оплата {stars_paid} Stars получена!\n"
        f"Зачислено: {ton_credit} TON\n"
        f"Обратитесь к администратору если баланс не обновился."
    )
```

# ── Синхронизация данных из игры ──

async def sync_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
“”“Игра отправляет JSON с данными игрока через sendData”””
try:
data = json.loads(update.message.web_app_data.data)
user = update.effective_user
sp = get_sheet()
ws = sp.worksheet(“Players”)
upsert_player(ws, user.id, user.username, user.first_name, {
“ton_balance”:    round(float(data.get(“ton”, 0)), 4),
“stars_balance”:  int(data.get(“stars”, 0)),
“games”:          int(data.get(“games”, 0)),
“wins”:           int(data.get(“wins”, 0)),
“max_mult”:       round(float(data.get(“maxMult”, 0)), 2),
})
except Exception as e:
logger.error(f”sync error: {e}”)

# ══════════════════════════════════════════

# ЗАПУСК

# ══════════════════════════════════════════

def main():
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler(“start”,   cmd_start))
app.add_handler(CommandHandler(“balance”, cmd_balance))
app.add_handler(CommandHandler(“stats”,   cmd_stats))
app.add_handler(CommandHandler(“top”,     cmd_top))
app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, sync_handler))
from telegram.ext import PreCheckoutQueryHandler
app.add_handler(PreCheckoutQueryHandler(pre_checkout))
logger.info(“Bot started!”)
app.run_polling()

if **name** == “**main**”:
main()
