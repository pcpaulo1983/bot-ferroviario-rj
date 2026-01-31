import os
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# LOGGING (IMPORTANTE)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TOKEN")

ramais = {
    "japeri": {
        "nome": "Ramal Japeri",
        "status": "🟢 Operação normal",
        "alerta": "Nenhum alerta ativo no momento."
    },
    "santacruz": {
        "nome": "Ramal Santa Cruz",
        "status": "🟢 Operação normal",
        "alerta": "Nenhum alerta ativo no momento."
    }
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("📩 /start recebido")

    teclado = [
        [InlineKeyboardButton("🚆 Ramal Japeri", callback_data="ramal_japeri")],
        [InlineKeyboardButton("🚆 Ramal Santa Cruz", callback_data="ramal_santacruz")]
    ]

    await update.message.reply_text(
        "🚆 *Central Ferroviária RJ*\n\nEscolha o ramal:",
        reply_markup=InlineKeyboardMarkup(teclado),
        parse_mode="Markdown"
    )

async def botoes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    ramal = query.data.split("_")[1]
    dados = ramais[ramal]

    teclado = [
        [InlineKeyboardButton("🚨 Ver alerta", callback_data=f"alerta_{ramal}")],
        [InlineKeyboardButton("📊 Status", callback_data=f"status_{ramal}")]
    ]

    await query.message.reply_text(
        f"*{dados['nome']}*\n\nEscolha uma opção:",
        reply_markup=InlineKeyboardMarkup(teclado),
        parse_mode="Markdown"
    )

async def ver_alerta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    ramal = query.data.split("_")[1]
    dados = ramais[ramal]

    await query.message.reply_text(
        f"🚨 *ALERTA — {dados['nome']}*\n\n{dados['alerta']}",
        parse_mode="Markdown"
    )

async def ver_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    ramal = query.data.split("_")[1]
    dados = ramais[ramal]

    await query.message.reply_text(
        f"📊 *STATUS — {dados['nome']}*\n\n{dados['status']}",
        parse_mode="Markdown"
    )

def main():
    logger.info("🤖 Bot Ferroviário RJ iniciado")

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(ver_alerta, pattern="^alerta_"))
    app.add_handler(CallbackQueryHandler(ver_status, pattern="^status_"))
    app.add_handler(CallbackQueryHandler(botoes, pattern="^ramal_"))

    app.run_polling()

if __name__ == "__main__":
    main()
