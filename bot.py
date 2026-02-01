import os
import logging
from datetime import datetime

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ================= CONFIG =================
TOKEN = os.getenv("TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID", "0"))


logging.basicConfig(level=logging.INFO)

# ================= DADOS =================
ramais = {}        # ramal -> thread_id
status_ramais = {} # ramal -> status
alertas = {}       # ramal -> alerta
mensagem_fixa = {} # ramal -> msg_id

# ================= UTIL =================
def normalizar(texto):
    return texto.lower().strip()

def agora():
    return datetime.now().strftime("%d/%m %H:%M")

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Bot Ferroviário RJ online!")

# ================= DETECTAR TÓPICO =================
async def detectar_topico(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    if update.message.forum_topic_created:
        nome = update.message.forum_topic_created.name
        thread_id = update.message.message_thread_id
        chave = normalizar(nome)

        ramais[chave] = thread_id
        status_ramais[chave] = "🟢 Operação normal"

        msg = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            message_thread_id=thread_id,
            text=(
                f"🚆 **{nome} — Central Ferroviária**\n\n"
                f"Status: {status_ramais[chave]}"
            ),
            reply_markup=painel(chave),
            parse_mode="Markdown"
        )

        mensagem_fixa[chave] = msg.message_id
        await context.bot.pin_chat_message(
            chat_id=update.effective_chat.id,
            message_id=msg.message_id
        )

# ================= PAINEL =================
def painel(ramal):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📍 Status", callback_data=f"status|{ramal}")],
        [InlineKeyboardButton("🕒 Horários", callback_data=f"horarios|{ramal}")],
        [InlineKeyboardButton("🚨 Alertas", callback_data=f"alerta|{ramal}")]
    ])

# ================= BOTÕES =================
async def botoes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    acao, ramal = query.data.split("|")

    if acao == "status":
        await query.message.reply_text(
            f"📍 Status:\n{status_ramais.get(ramal)}"
        )

    elif acao == "horarios":
        await query.message.reply_text(
            "🕒 Intervalos:\nPico: 5–10 min\nNormal: 15 min\nÚltimo: 23:30"
        )

    elif acao == "alerta":
        await query.message.reply_text(
            alertas.get(ramal, "🟢 Nenhum alerta ativo")
        )

# ================= ALERTA MANUAL =================
async def alerta_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        return await update.message.reply_text(
            "Uso: /alerta ramal mensagem"
        )

    ramal = normalizar(context.args[0])
    texto = " ".join(context.args[1:])

    alertas[ramal] = (
        f"🚨 **ALERTA — {ramal}**\n\n"
        f"{texto}\n\n🕒 {agora()}"
    )

    status_ramais[ramal] = "🔴 Alerta ativo"

    thread = ramais.get(ramal)
    if thread:
        msg = await context.bot.send_message(
            chat_id=GROUP_ID,
            message_thread_id=thread,
            text=alertas[ramal],
            parse_mode="Markdown"
        )
        await context.bot.pin_chat_message(GROUP_ID, msg.message_id)

# ================= NORMALIZAR =================
async def normalizado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ramal = normalizar(context.args[0])
    alertas.pop(ramal, None)
    status_ramais[ramal] = "🟢 Operação normal"
    await update.message.reply_text(f"✅ {ramal} normalizado")

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("alerta", alerta_cmd))
    app.add_handler(CommandHandler("normalizado", normalizado))
    app.add_handler(CallbackQueryHandler(botoes))
    app.add_handler(
        MessageHandler(filters.StatusUpdate.FORUM_TOPIC_CREATED, detectar_topico)
    )

    app.run_polling()

if __name__ == "__main__":
    main()
