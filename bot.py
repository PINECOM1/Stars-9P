import logging
import httpx
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (ApplicationBuilder, CommandHandler,
                           MessageHandler, PreCheckoutQueryHandler,
                           ContextTypes, filters)

BOT_TOKEN = "8727347320:AAGiDIFkoxEIcLUWqfVYjd4HddBnokhU4_g"
SB_URL    = "https://sdzapdsdikirgbgtrpmd.supabase.co"
SB_KEY    = "sb_publishable_yp_xTKmkb1Rgl3pWv-0LNA_YLJvyXEF"
GAME_URL  = "https://pinecom1.github.io/Stars-9P"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

HEADERS = {
    "apikey": SB_KEY,
    "Authorization": "Bearer " + SB_KEY,
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates,return=minimal"
}

async def sb_get(tg_id):
    async with httpx.AsyncClient() as c:
        r = await c.get(SB_URL + "/rest/v1/players",
            params={"tg_id": "eq." + str(tg_id), "select": "*"}, headers=HEADERS)
        rows = r.json()
        return rows[0] if rows else None

async def sb_set(data):
    async with httpx.AsyncClient() as c:
        await c.post(SB_URL + "/rest/v1/players", json=data, headers=HEADERS)

async def sb_top():
    async with httpx.AsyncClient() as c:
        r = await c.get(SB_URL + "/rest/v1/players",
            params={"select": "first_name,username,stars_balance",
                    "order": "stars_balance.desc", "limit": 10}, headers=HEADERS)
        return r.json() or []

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = ctx.args
    p = await sb_get(str(user.id))
    if not p:
        await sb_set({"tg_id": str(user.id), "username": user.username or "",
            "first_name": user.first_name or "", "ton_balance": 0.10,
            "stars_balance": 0, "games": 0, "wins": 0, "max_mult": 0,
            "total_deposited": 0, "last_seen": datetime.utcnow().isoformat()})
        p = await sb_get(str(user.id))
        greeting = "Добро пожаловать!"
    else:
        await sb_set({"tg_id": str(user.id), "username": user.username or "",
            "first_name": user.first_name or "",
            "last_seen": datetime.utcnow().isoformat()})
        greeting = "С возвращением, " + user.first_name + "!"

    if args and args[0].startswith("dep_"):
        parts = args[0].split("_")
        if len(parts) >= 2:
            amt = int(parts[1])
            await ctx.bot.send_invoice(
                chat_id=update.effective_chat.id,
                title="Пополнение " + str(amt) + " Stars",
                description="Пополнение баланса Stars 9P",
                payload="deposit_" + str(user.id) + "_" + str(amt),
                provider_token="", currency="XTR",
                prices=[{"label": str(amt) + " Stars", "amount": amt}])
            return

    ton   = float(p.get("ton_balance", 0.10) or 0.10)
    stars = int(p.get("stars_balance", 0) or 0)
    games = int(p.get("games", 0) or 0)
    kb = [[InlineKeyboardButton("Играть", url=GAME_URL)]]
    await update.message.reply_text(
        greeting + "\n\nTON: " + str(round(ton, 4)) +
        "\nStars: " + str(stars) + "\nИгр: " + str(games),
        reply_markup=InlineKeyboardMarkup(kb))

async def cmd_balance(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    p = await sb_get(str(update.effective_user.id))
    if not p:
        await update.message.reply_text("Напиши /start чтобы начать!")
        return
    ton   = float(p.get("ton_balance", 0) or 0)
    stars = int(p.get("stars_balance", 0) or 0)
    dep   = float(p.get("total_deposited", 0) or 0)
    await update.message.reply_text(
        "Баланс:\n\nTON: " + str(round(ton, 4)) +
        "\nStars: " + str(stars) +
        "\nДепозитов: " + str(round(dep, 2)) + " TON")

async def cmd_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    p = await sb_get(str(update.effective_user.id))
    if not p:
        await update.message.reply_text("Напиши /start чтобы начать!")
        return
    g = int(p.get("games", 0) or 0)
    w = int(p.get("wins", 0) or 0)
    maxm = float(p.get("max_mult", 0) or 0)
    winrate = round(w / g * 100) if g > 0 else 0
    await update.message.reply_text(
        "Статистика:\n\nИгр: " + str(g) + "\nПобед: " + str(w) +
        "\nВинрейт: " + str(winrate) + "%\nМакс: " + str(round(maxm, 2)) + "x")

async def cmd_top(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    top = await sb_top()
    medals = ["1.", "2.", "3."]
    text = "Топ-10 игроков:\n\n"
    for i, p in enumerate(top):
        name  = p.get("first_name") or p.get("username") or "Аноним"
        stars = int(p.get("stars_balance", 0) or 0)
        medal = medals[i] if i < 3 else str(i + 1) + "."
        text += medal + " " + name + " - " + str(stars) + " Stars\n"
    await update.message.reply_text(text)

async def pre_checkout(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.pre_checkout_query.answer(ok=True)

async def successful_payment(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user       = update.effective_user
    stars_paid = update.message.successful_payment.total_amount
    ton_credit = round(stars_paid / 100 * 0.1, 4)
    p = await sb_get(str(user.id))
    new_ton = round(float(p.get("ton_balance", 0) or 0) + ton_credit, 4) if p else ton_credit
    new_dep = round(float(p.get("total_deposited", 0) or 0) + ton_credit, 4) if p else ton_credit
    await sb_set({"tg_id": str(user.id), "username": user.username or "",
        "first_name": user.first_name or "", "ton_balance": new_ton,
        "total_deposited": new_dep, "last_seen": datetime.utcnow().isoformat()})
    await update.message.reply_text(
        "Оплата получена!\n\nStars: " + str(stars_paid) +
        "\nЗачислено: " + str(ton_credit) + " TON")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start",   cmd_start))
    app.add_handler(CommandHandler("balance", cmd_balance))
    app.add_handler(CommandHandler("stats",   cmd_stats))
    app.add_handler(CommandHandler("top",     cmd_top))
    app.add_handler(PreCheckoutQueryHandler(pre_checkout))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    logger.info("Bot started!")
    app.run_polling()

if __name__ == "__main__":
    main()
