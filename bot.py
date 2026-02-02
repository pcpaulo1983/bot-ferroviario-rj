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

# ================= CONFIG =================
TOKEN = os.getenv("TOKEN")
GROUP_ID_ENV = os.getenv("GROUP_ID")

if not TOKEN or not GROUP_ID_ENV:
    raise RuntimeError("❌ TOKEN ou GROUP_ID não definidos no Railway")

GROUP_ID = int(GROUP_ID_ENV)

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

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
def normalizar(texto: str) -> str:
    return texto.lower().strip()

def agora() -> str:
    return datetime.now().strftime("%d/%m %H:%M")

def painel(ramal: str):
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
    if not update.message or not update.message.forum_topic_created:
        return

    nome = update.message.forum_topic_created.name
    chave = normalizar(nome)
    thread_id = update.message.message_thread_id

    ramais[chave] = thread_id
    status_ramais[chave] = "🟢 Operação normal"

    msg = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        message_thread_id=thread_id,
        text=(
            f"🚆 **{nome} — Central Ferroviária**\n\n"
            f"Status: 🟢 Operação normal"
        ),
        reply_markup=painel(chave),
        parse_mode="Markdown"
    )

    mensagem_fixa[chave] = msg.message_id
    await context.bot.pin_chat_message(
        chat_id=update.effective_chat.id,
        message_id=msg.message_id
    )

# ================= BOTÕES =================
async def botoes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    acao, ramal = query.data.split("|")

    if acao == "status":
        await query.message.reply_text(
            f"📍 Status atual:\n{status_ramais.get(ramal, 'Desconhecido')}"
        )

    elif acao == "horarios":
        await query.message.reply_text(
            "🕒 Horários médios:\n"
            "Pico: 5–10 min\n"
            "Normal: 10–15 min\n"
            "Última viagem: ~23:30"
        )

    elif acao == "alerta":
        await query.message.reply_text(
            alertas.get(ramal, "🟢 Nenhum alerta ativo")
        )

# ================= BUSCA ONLINE =================
def buscar_status_online(ramal: str):
    for nome, url in FONTES.items():
        if nome in ramal:
            try:
                with httpx.Client(timeout=10) as client:
                    resposta = client.get(url)

                texto = resposta.text.lower()

                for palavra in PALAVRAS_ALERTA:
                    if palavra in texto:
                        return "🔴 Problema detectado", palavra

                for palavra in PALAVRAS_NORMAL:
                    if palavra in texto:
                        return "🟢 Operação normal", None

            except Exception as e:
                logging.error(f"Erro ao acessar {url}: {e}")

    return None, None

# ================= ALERTA AUTOMÁTICO =================
async def monitorar(context: ContextTypes.DEFAULT_TYPE):
    for ramal, thread_id in ramais.items():
        status, motivo = buscar_status_online(ramal)

        if not status:
            continue

        if status != status_ramais.get(ramal):
            status_ramais[ramal] = status

            texto = (
                f"🚨 **ALERTA AUTOMÁTICO — {ramal}**\n\n"
                f"Status: {status}\n"
                f"Motivo detectado: {motivo or 'não informado'}\n\n"
                f"🕒 {agora()}"
            )

            alertas[ramal] = texto

            msg = await context.bot.send_message(
                chat_id=GROUP_ID,
                message_thread_id=thread_id,
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

    # verifica status a cada 5 minutos
    app.job_queue.run_repeating(
        monitorar,
        interval=300,
        first=30
    )

    app.run_polling()

if __name__ == "__main__":
    main()
