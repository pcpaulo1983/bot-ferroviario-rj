import os
import logging
import httpx
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
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ================= CONFIG =================
TOKEN = os.getenv("TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID", "0"))  # coloque o ID do grupo
CHECK_INTERVAL_MIN = 10  # checar sites a cada X minutos

logging.basicConfig(level=logging.INFO)

# ================= DADOS INTERNOS =================
ramais = {}        # nome -> thread_id
status_ramais = {} # nome -> status
alertas = {}       # nome -> texto do alerta
mensagem_fixa = {} # nome -> message_id

# ================= UTIL =================
def normalizar(nome: str):
    return nome.lower().strip()

def agora():
    return datetime.now().strftime("%d/%m %H:%M")

# ================= DETECTAR NOVO TÓPICO =================
async def detectar_topico(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.is_topic_message:
        return

    if update.message.forum_topic_created:
        nome = update.message.forum_topic_created.name
        thread_id = update.message.message_thread_id

        if "ramal" in nome.lower() or "metrô" in nome.lower() or "vlt" in nome.lower():
            chave = normalizar(nome)
            ramais[chave] = thread_id
            status_ramais[chave] = "🟢 Operação normal"

            msg = await context.bot.send_message(
                chat_id=update.effective_chat.id,
                message_thread_id=thread_id,
                text=f"🚆 **{nome} — Central Ferroviária**\n\n"
                     f"Status atual: {status_ramais[chave]}\n\n"
                     f"👇 Use os botões abaixo:",
                reply_markup=painel_botoes(chave),
                parse_mode="Markdown"
            )

            mensagem_fixa[chave] = msg.message_id
            await context.bot.pin_chat_message(
                chat_id=update.effective_chat.id,
                message_id=msg.message_id
            )

# ================= PAINEL =================
def painel_botoes(ramal):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📍 Status", callback_data=f"status|{ramal}")],
        [InlineKeyboardButton("🕒 Horários", callback_data=f"horarios|{ramal}")],
        [InlineKeyboardButton("🚨 Alertas", callback_data=f"alerta|{ramal}")]
    ])

# ================= CALLBACK BOTÕES =================
async def botoes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    acao, ramal = query.data.split("|")

    if acao == "status":
        texto = status_ramais.get(ramal, "Sem dados.")
        await query.message.reply_text(f"📍 Status {ramal}:\n{texto}")

    elif acao == "horarios":
        horarios = await buscar_horarios(ramal)
        await query.message.reply_text(horarios)

    elif acao == "alerta":
        alerta = alertas.get(ramal, "🟢 Nenhum alerta ativo.")
        await query.message.reply_text(alerta)

# ================= BUSCAR HORÁRIOS =================
async def buscar_horarios(ramal):
    # AQUI você pode trocar por:
    # - API oficial
    # - Google Sheets
    # - CSV
    # - Scraping
    return (
        f"🕒 Horários — {ramal}\n\n"
        "🚆 Pico: 5–10 min\n"
        "🚆 Normal: 15 min\n"
        "🌙 Último trem: 23:30"
    )

# ================= ALERTA MANUAL =================
async def alerta_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Uso: /alerta ramal texto")
        return

    ramal = normalizar(context.args[0])
    texto = " ".join(context.args[1:])

    alertas[ramal] = (
        f"🚨 **ALERTA — {ramal}**\n\n"
        f"{texto}\n\n"
        f"🕒 Atualizado: {agora()}"
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

# ================= NORMALIZADO =================
async def normalizado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ramal = normalizar(context.args[0])
    alertas.pop(ramal, None)
    status_ramais[ramal] = "🟢 Operação normal"

    await update.message.reply_text(f"✅ {ramal} normalizado.")

# ================= MONITORAMENTO AUTOMÁTICO =================
async def monitorar_sites():
    # EXEMPLO — você pode adaptar
    async with httpx.AsyncClient(timeout=20) as client:
        # url = "https://www.supervia.com.br/status"
        # r = await client.get(url)
        # if "interrupção" in r.text.lower():
        #     disparar_alerta(...)
        pass

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Bot Ferroviário RJ online!")

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("alerta", alerta_cmd))
    app.add_handler(CommandHandler("normalizado", normalizado))
    app.add_handler(CallbackQueryHandler(botoes))
    app.add_handler(MessageHandler(filters.ALL, detectar_topico))

    scheduler = AsyncIOScheduler()
    scheduler.add_job(monitorar_sites, "interval", minutes=CHECK_INTERVAL_MIN)
    scheduler.start()

    app.run_polling()

if __name__ == "__main__":
    main()
