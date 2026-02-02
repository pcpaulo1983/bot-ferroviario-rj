import os
import logging
import asyncio
import requests
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
GROUP_ID = int(os.getenv("GROUP_ID"))

logging.basicConfig(level=logging.INFO)

# ================= DADOS =================
ramais = {}          # ramal -> thread_id
status_ramais = {}   # ramal -> status
alertas = {}         # ramal -> alerta
mensagem_fixa = {}   # ramal -> msg_id

# ================= PALAVRAS-CHAVE =================
PALAVRAS_ALERTA = [
    "interrompida", "interrompido", "paralisada", "paralisado",
    "sem circulação", "atraso", "atrasos", "lentidão",
    "operação parcial", "falha", "ocorrência", "pane", "manutenção"
]

PALAVRAS_NORMAL = [
    "operação normal", "circulando normalmente",
    "serviço normalizado", "circulação normal"
]

# ================= FONTES OFICIAIS =================
FONTES = {
    "supervia": "https://www.supervia.com.br/rss",
    "metro rio": "https://www.metrorio.com.br/rss",
    "vlt rio": "https://www.vltrio.com.br/rss",
    "bondinho santa teresa": "https://www.rio.rj.gov.br/rss"
}

# ================= UTIL =================
def normalizar(texto):
    return texto.lower().strip()

def agora():
    return datetime.now().strftime("%d/%m %H:%M")

def painel(ramal):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📍 Status", callback_data=f"status|{ramal}")],
        [InlineKeyboardButton("🕒 Horários", callback_data=f"horarios|{ramal}")],
        [InlineKeyboardButton("🚨 Alertas", callback_data=f"alerta|{ramal}")]
    ])

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Bot Ferroviário RJ online!")

# ================= DETECTAR TÓPICOS =================
async def detectar_topico(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.forum_topic_created:
        nome = update.message.forum_topic_created.name
        chave = normalizar(nome)
        thread_id = update.message.message_thread_id

        ramais[chave] = thread_id
        status_ramais[chave] = "🟢 Operação normal"

        msg = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            message_thread_id=thread_id,
            text=f"🚆 **{nome} — Central Ferroviária**\n\nStatus: 🟢 Operação normal",
            reply_markup=painel(chave),
            parse_mode="Markdown"
        )

        mensagem_fixa[chave] = msg.message_id
        await context.bot.pin_chat_message(update.effective_chat.id, msg.message_id)

# ================= BOTÕES =================
async def botoes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    acao, ramal = query.data.split("|")

    if acao == "status":
        await query.message.reply_text(f"📍 Status atual:\n{status_ramais.get(ramal)}")

    elif acao == "horarios":
        await query.message.reply_text(
            "🕒 Horários médios:\n"
            "Pico: 5–10 min\n"
            "Normal: 10–15 min\n"
            "Última viagem: ~23:30"
        )

    elif acao == "alerta":
        await query.message.reply_text(alertas.get(ramal, "🟢 Nenhum alerta ativo"))

# ================= BUSCA INTERNET =================
def buscar_status_online(ramal):
    for nome, url in FONTES.items():
        if nome in ramal:
            try:
                r = requests.get(url, timeout=10)
                texto = r.text.lower()

                for p in PALAVRAS_ALERTA:
                    if p in texto:
                        return "🔴 Problema detectado", p

                for p in PALAVRAS_NORMAL:
                    if p in texto:
                        return "🟢 Operação normal", None

            except Exception as e:
                logging.error(e)

    return None, None

# ================= ALERTA AUTOMÁTICO =================
async def monitorar(context: ContextTypes.DEFAULT_TYPE):
    for ramal, thread in ramais.items():
        status, palavra = buscar_status_online(ramal)

        if not status:
            continue

        if status != status_ramais.get(ramal):
            status_ramais[ramal] = status

            texto = (
                f"🚨 **ALERTA AUTOMÁTICO — {ramal}**\n\n"
                f"Status: {status}\n"
                f"Motivo detectado: {palavra}\n\n"
                f"🕒 {agora()}"
            )

            alertas[ramal] = texto

            msg = await context.bot.send_message(
                chat_id=GROUP_ID,
                message_thread_id=thread,
                text=texto,
                parse_mode="Markdown"
            )

            await context.bot.pin_chat_message(GROUP_ID, msg.message_id)

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(botoes))
    app.add_handler(
        MessageHandler(filters.StatusUpdate.FORUM_TOPIC_CREATED, detectar_topico)
    )

    app.job_queue.run_repeating(monitorar, interval=300, first=30)

    app.run_polling()

if __name__ == "__main__":
    main()
