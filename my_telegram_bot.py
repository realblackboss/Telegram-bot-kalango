import logging
import sqlite3
import telegram
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
import os
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from contextlib import contextmanager
import re
import bcrypt
import sys
import asyncio

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# Configuração do logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Obter o token do bot de uma variável de ambiente
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not TOKEN:
    logger.error("O token do bot não foi encontrado. Verifique o arquivo .env.")
    exit(1)

# Número de WhatsApp para contato
WHATSAPP_NUMBER = os.getenv('WHATSAPP_NUMBER', '+5582988951440')

# Mensagens predefinidas para o botão de suporte
WHATSAPP_MESSAGE_REGISTRATION = "Olá, gostaria de solicitar a liberação do meu acesso ao botkalangoanuncios."

# Limite máximo de grupos que um usuário pode adicionar
MAX_GROUPS = 3

# Gerenciador de agendamentos
scheduler = AsyncIOScheduler()
scheduler.start()

# Função para obter o caminho do banco de dados do usuário
def get_db_path():
    db_dir = 'databases'
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)
    return os.path.join(db_dir, 'bot.db')

# Função para exibir o menu de registro, login, recuperação de senha, suporte e seleção de idioma
def start_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("Registrar 📝", callback_data='register')],
        [InlineKeyboardButton("Entrar 🔑", callback_data='login')],
        [InlineKeyboardButton("Sobre ℹ️", callback_data='sobre')],
        [InlineKeyboardButton("Selecionar Idioma 🌐", callback_data='select_language')],
        [InlineKeyboardButton("Suporte ☎️", url=f"https://wa.me/{WHATSAPP_NUMBER.replace('+', '')}?text={WHATSAPP_MESSAGE_REGISTRATION.replace(' ', '%20')}")]
    ]
    return InlineKeyboardMarkup(keyboard)

# Função para exibir as opções de idiomas ao clicar no botão "Selecionar Idioma"
async def handle_select_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    # Cria um teclado com as opções de idiomas e um botão para voltar ao menu principal
    keyboard = [
        [InlineKeyboardButton("Português 🇧🇷", callback_data='set_language_pt')],
        [InlineKeyboardButton("English 🇬🇧", callback_data='set_language_en')],
        [InlineKeyboardButton("中文 🇨🇳", callback_data='set_language_zh')],
        [InlineKeyboardButton("Voltar ao Menu Principal 🔙", callback_data='menu_registro')]
    ]
    
    await query.edit_message_text(
        text="Escolha o idioma:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Funções para definir o idioma
async def set_language_pt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    context.user_data['language'] = 'pt'
    await query.edit_message_text("Idioma definido para Português. Retornando ao menu principal...")
    await start(update, context)

async def set_language_en(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    context.user_data['language'] = 'en'
    await query.edit_message_text("Language set to English. Returning to the main menu...")
    await start(update, context)

async def set_language_zh(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    context.user_data['language'] = 'zh'
    await query.edit_message_text("语言设置为中文。返回主菜单...")
    await start(update, context)

# Função para exibir as opções de idiomas ao clicar no botão "Sobre"
async def handle_sobre(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    # Cria um teclado com as opções de idiomas e um botão para voltar ao menu principal
    keyboard = [
        [InlineKeyboardButton("Ler em Português 🇧🇷", callback_data='sobre_pt')],
        [InlineKeyboardButton("Read in English 🇬🇧", callback_data='sobre_en')],
        [InlineKeyboardButton("读中文 🇨🇳", callback_data='sobre_zh')],
        [InlineKeyboardButton("Voltar ao Menu Principal 🔙", callback_data='menu_registro')]
    ]
    
    await query.edit_message_text(
        text="Escolha o idioma para ler sobre o bot:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Função para exibir o texto "Sobre" em português
async def handle_sobre_pt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    sobre_text_pt = """
**🤖 Sobre o Bot**

Bem-vindo ao nosso bot, criado para facilitar o gerenciamento de grupos e agendamento de mensagens! 🎯

Aqui estão algumas funcionalidades principais:

1. **📝 Registro de Usuário**
   - Insira seu e-mail, senha e número de WhatsApp para se cadastrar.
   - Após o registro, solicite a ativação da sua conta via WhatsApp.

2. **🔑 Login**
   - Acesse o bot com seu e-mail e senha.
   - O sistema verifica automaticamente o status da sua conta, como bloqueios ou vencimento de prazo.

3. **📅 Agendamento de Mensagens**
   - Programe o envio de mensagens de texto, imagens ou vídeos para grupos.
   - Você pode escolher enviar diariamente ou em uma data específica.

4. **👥 Gerenciamento de Grupos**
   - Adicione até três grupos para o envio de mensagens programadas.
   - Visualize e remova grupos diretamente pelo bot.

5. **🚫 Cancelamento de Mensagens Agendadas**
   - Consulte todas as mensagens agendadas para um grupo e cancele qualquer uma, se necessário.

6. **⏰ Verificação Automática de Contas Expiradas**
   - O bot faz verificações diárias e bloqueia automaticamente as contas expiradas.

7. **📞 Suporte**
   - Precisa de ajuda? Use o botão de suporte para falar diretamente via WhatsApp.
    """
    
    # Botão de voltar ao menu de idiomas
    keyboard = [
        [InlineKeyboardButton("Voltar 🔙", callback_data='sobre')]
    ]
    
    await query.edit_message_text(text=sobre_text_pt, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

# Função para exibir o texto "Sobre" em inglês
async def handle_sobre_en(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    sobre_text_en = """
**🤖 About the Bot**

Welcome to our bot, designed to help manage groups and schedule messages! 🎯

Here are some of the main features:

1. **📝 User Registration**
   - Enter your e-mail, password, and WhatsApp number to register.
   - After registering, request your account activation via WhatsApp.

2. **🔑 Login**
   - Log in using your e-mail and password.
   - The system will automatically check your account status for blocks or expiration.

3. **📅 Message Scheduling**
   - Schedule the sending of text, image, or video messages to groups.
   - You can choose to send messages daily or on a specific date.

4. **👥 Group Management**
   - Add up to three groups for scheduled messages.
   - View and remove groups directly via the bot.

5. **🚫 Cancel Scheduled Messages**
   - Check all scheduled messages for a group and cancel any if necessary.

6. **⏰ Automatic Account Expiration Check**
   - The bot performs daily checks and automatically blocks expired accounts.

7. **📞 Support**
   - Need help? Use the support button to chat directly via WhatsApp.
    """
    
    # Botão de voltar ao menu de idiomas
    keyboard = [
        [InlineKeyboardButton("Back 🔙", callback_data='sobre')]
    ]
    
    await query.edit_message_text(text=sobre_text_en, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

# Função para exibir o texto "Sobre" em chinês simplificado
async def handle_sobre_zh(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    sobre_text_zh = """
**🤖 关于机器人**

欢迎使用我们的机器人，它旨在帮助您管理群组和安排消息的发送！ 🎯

以下是一些主要功能：

1. **📝 用户注册**
   - 输入您的电子邮件、密码和WhatsApp号码进行注册。
   - 注册后，通过WhatsApp请求激活您的账户。

2. **🔑 登录**
   - 使用您的电子邮件和密码登录。
   - 系统会自动检查您的账户状态，如是否被封锁或过期。

3. **📅 消息安排**
   - 安排向群组发送文本、图片或视频消息。
   - 您可以选择每天发送或在特定日期发送。

4. **👥 群组管理**
   - 添加最多三个群组以安排消息发送。
   - 通过机器人直接查看和移除群组。

5. **🚫 取消已安排的消息**
   - 查看群组的所有已安排消息，并在必要时取消任何一条。

6. **⏰ 自动账户过期检查**
   - 机器人每天检查，并自动封锁过期账户。

7. **📞 支持**
   - 需要帮助？使用支持按钮直接通过WhatsApp进行联系。
    """
    
    # Botão de voltar ao menu de idiomas
    keyboard = [
        [InlineKeyboardButton("返回 🔙", callback_data='sobre')]
    ]
    
    await query.edit_message_text(text=sobre_text_zh, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

# Função para exibir o menu principal
def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("Adicionar Grupo ➕", callback_data='adicionar_link')],
        [InlineKeyboardButton("Ver Grupos 👀", callback_data='ver_grupos')],
        [InlineKeyboardButton("Remover Grupo ❌", callback_data='remover_grupo')],
        [InlineKeyboardButton("Agendar Mensagem e Cancelar 📅", callback_data='agendar_cancelar')],
        [InlineKeyboardButton("Preciso de ajuda, o bot travou ☎️", url=f"https://wa.me/{WHATSAPP_NUMBER.replace('+', '')}?text=Preciso%20de%20ajuda,%20o%20bot%20travou.")],
        [InlineKeyboardButton("Limpar Interface 🧹", callback_data='clear_interface')]
    ]
    return InlineKeyboardMarkup(keyboard)

# Função para limpar a interface e exibir o menu principal novamente
async def clear_interface(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat_id

    # Pegando o ID da mensagem atual (geralmente usada para limpar)
    current_message_id = query.message.message_id

    # IDs de mensagens que queremos preservar (ex.: mensagens relacionadas à listagem de agendamentos)
    preserved_message_ids = context.user_data.get('scheduled_message_ids', [])

    try:
        # Deletando mensagens a partir do ID da mensagem atual, mas preservando as importantes
        for i in range(current_message_id, current_message_id - 100, -1):
            if i not in preserved_message_ids:
                try:
                    await context.bot.delete_message(chat_id=chat_id, message_id=i)
                except telegram.error.BadRequest:
                    # Ignorar se não puder deletar a mensagem (ex: se não existe)
                    continue

    except Exception as e:
        logger.error(f"Erro ao limpar mensagens: {e}")

    # Exibir o menu principal novamente
    await context.bot.send_message(
        chat_id=chat_id,
        text="Escolha uma opção no menu:",
        reply_markup=main_menu_keyboard()
    )

# Função para agendar mensagens com um job_id único usando o message_id
def schedule_message(user_id, group_id, message_type, message_content, schedule_time, message_caption=None, message_thumbnail=None):
    with db_connection() as conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO scheduled_messages (user_id, group_id, message_type, message_content, scheduled_time, message_caption, message_thumbnail) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (user_id, group_id, message_type, message_content, schedule_time, message_caption, message_thumbnail)
            )
            conn.commit()
            message_id = cursor.lastrowid
            
            if is_valid_time_format(schedule_time):
                hour, minute = map(int, schedule_time.split(":"))
                job_id = f'schedule_{group_id}_{message_type}_{message_id}'
                scheduler.add_job(send_scheduled_message, 'cron', hour=hour, minute=minute, args=[group_id, message_type, message_content, message_caption, message_thumbnail], id=job_id)
            else:
                schedule_datetime = parse_schedule_time(schedule_time)
                if schedule_datetime:
                    job_id = f'schedule_{group_id}_{message_type}_{message_id}'
                    scheduler.add_job(send_scheduled_message, 'date', run_date=schedule_datetime, args=[group_id, message_type, message_content, message_caption, message_thumbnail], id=job_id)
                else:
                    logger.error(f"Erro ao agendar a mensagem: formato de data/hora inválido '{schedule_time}'")
        except Exception as e:
            logger.error(f"Erro ao agendar a mensagem: {e}")

# Função para listar mensagens agendadas de um grupo específico (ajustada)
async def list_group_scheduled_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    group_id = context.user_data['selected_group_id']
    user_id = update.effective_user.id

    # Armazenar os IDs das mensagens enviadas para posterior exclusão
    context.user_data['scheduled_message_ids'] = []

    # Deleta a mensagem anterior (menu principal ou outra) se houver
    try:
        await query.message.delete()  # Apagar o menu principal
    except telegram.error.BadRequest as e:
        logger.warning(f"Falha ao deletar a mensagem anterior: {e}")

    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id, message_type, message_content, scheduled_time, message_caption, message_thumbnail FROM scheduled_messages WHERE user_id=? AND group_id=?', (user_id, group_id))
        messages = cursor.fetchall()

        if messages:
            for msg in messages:
                message_id, message_type, message_content, scheduled_time, message_caption, message_thumbnail = msg

                # Construir a descrição da mensagem
                if message_type == 'text':
                    message_description = f"Texto - Agendada para: {scheduled_time}\nConteúdo: {message_content}"
                else:
                    message_description = f"{message_type.capitalize()} - Agendada para: {scheduled_time}"
                    if message_caption:
                        message_description += f"\nLegenda: {message_caption}"

                # Verificar se a mensagem é de mídia (imagem ou vídeo)
                if message_type in ['image', 'video']:
                    try:
                        if message_thumbnail:
                            msg_sent = await context.bot.send_photo(
                                chat_id=query.message.chat_id,
                                photo=message_thumbnail,
                                caption=message_description,
                                reply_markup=InlineKeyboardMarkup([
                                    [InlineKeyboardButton("Escolher opções", callback_data=f"cancel_message_{message_id}")],
                                ])
                            )
                        else:
                            raise ValueError("Miniatura não encontrada no banco de dados.")
                    except Exception as e:
                        logger.warning(f"Falha ao exibir a miniatura armazenada: {e}")
                        try:
                            if message_type == 'image':
                                msg_sent = await context.bot.send_photo(
                                    chat_id=query.message.chat_id,
                                    photo=message_content,
                                    caption=message_description,
                                    reply_markup=InlineKeyboardMarkup([
                                        [InlineKeyboardButton("Escolher opções", callback_data=f"cancel_message_{message_id}")],
                                    ])
                                )
                            elif message_type == 'video':
                                msg_sent = await context.bot.send_video(
                                    chat_id=query.message.chat_id,
                                    video=message_content,
                                    caption=message_description,
                                    reply_markup=InlineKeyboardMarkup([
                                        [InlineKeyboardButton("Escolher opções", callback_data=f"cancel_message_{message_id}")],
                                    ])
                                )
                        except Exception as ex:
                            logger.error(f"Erro ao buscar a mídia do Telegram: {ex}")
                            await context.bot.send_message(
                                chat_id=query.message.chat_id,
                                text=f"Erro ao exibir a mídia agendada. Por favor, tente novamente.",
                                reply_markup=InlineKeyboardMarkup([])
                            )
                else:
                    # Caso seja uma mensagem de texto ou não tenha miniatura
                    msg_sent = await context.bot.send_message(
                        chat_id=query.message.chat_id,
                        text=message_description,
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("Escolher opções", callback_data=f"cancel_message_{message_id}")],
                        ])
                    )

                # Armazenar os message_ids enviados para exclusão posterior
                context.user_data['scheduled_message_ids'].append(msg_sent.message_id)

        else:
            # Caso não haja mensagens agendadas
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="Nenhuma mensagem agendada neste grupo.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Voltar 🔙", callback_data=f'select_agendar_grupo_{group_id}')],  # Adição do botão voltar
                ])
            )

# Função para cancelar uma mensagem agendada no scheduler e no banco de dados (ajustada)
async def cancelar_mensagem_agendada(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("Função cancelar_mensagem_agendada chamada.")
    query = update.callback_query
    await query.answer()

    # Apagar todas as mensagens agendadas exibidas anteriormente
    for message_id in context.user_data.get('scheduled_message_ids', []):
        try:
            await context.bot.delete_message(chat_id=query.message.chat_id, message_id=message_id)
        except telegram.error.BadRequest as e:
            logger.warning(f"Falha ao deletar mensagem agendada: {e}")

    message_id = int(query.data.split("_")[-1])
    logger.info(f"ID da mensagem a ser cancelada: {message_id}")
    with db_connection() as conn:
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT group_id, message_type, message_content, scheduled_time, message_thumbnail FROM scheduled_messages WHERE id=?', (message_id,))
            result = cursor.fetchone()
            if result:
                group_id, message_type, message_content, scheduled_time, message_thumbnail = result

                # Apagar a mensagem de mídia ou texto antes de exibir o menu principal
                try:
                    if message_type in ['image', 'video']:  # Se for mídia
                        await query.message.delete()  # Tenta deletar a mensagem de mídia
                    else:
                        await safe_edit_message_text(query, "Escolha uma opção no menu:", reply_markup=main_menu_keyboard())
                except telegram.error.BadRequest as e:
                    logger.error(f"Erro ao deletar mensagem de mídia: {e}")
                    await query.message.reply_text("Erro ao deletar a mensagem de mídia. Retornando ao menu.")

                # Apresentar a confirmação de cancelamento com texto
                confirmation_text = f"Você realmente deseja cancelar esta mensagem?\n\nTipo: {message_type.capitalize()}\nAgendada para: {scheduled_time}"
                
                # Apenas texto de confirmação, agora com o botão "Voltar ao menu principal"
                await query.message.reply_text(
                    confirmation_text,
                    reply_markup=InlineKeyboardMarkup([ 
                        [InlineKeyboardButton("Sim ✅", callback_data=f"confirm_cancel_{message_id}")],
                        [InlineKeyboardButton("Retornar à seleção de escolha", callback_data=f"back_to_cancel_selection")],
                        [InlineKeyboardButton("Voltar ao menu principal", callback_data='menu_principal')]
                    ])
                )
            else:
                await query.edit_message_text("Mensagem não encontrada.", reply_markup=main_menu_keyboard())
        except Exception as e:
            logger.error(f"Erro ao cancelar a mensagem no banco de dados: {e}")

# Função para confirmar o cancelamento da mensagem e incluir o botão de retorno ao menu principal
async def confirm_cancel_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    message_id = int(query.data.split("_")[-1])
    
    with db_connection() as conn:
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT group_id, message_type, scheduled_time FROM scheduled_messages WHERE id=?', (message_id,))
            message = cursor.fetchone()

            if message:
                group_id, message_type, scheduled_time = message
                job_id = f'schedule_{group_id}_{message_type}_{message_id}'

                # Verificar se o job está agendado e removê-lo
                job = scheduler.get_job(job_id)
                if job:
                    scheduler.remove_job(job_id)
                    logger.info(f"Job {job_id} removido do scheduler.")

                # Remover a mensagem do banco de dados
                cursor.execute('DELETE FROM scheduled_messages WHERE id=?', (message_id,))
                conn.commit()

                logger.info(f"Mensagem agendada {message_id} foi cancelada e removida do banco de dados.")
                
                # Apagar a mensagem de confirmação e exibir apenas o menu principal
                try:
                    await query.message.delete()  # Deleta a mensagem de confirmação "Sim/Não"
                except telegram.error.BadRequest as e:
                    logger.warning(f"Erro ao tentar apagar a mensagem: {e}")

                # Enviar uma nova mensagem com o menu principal
                await context.bot.send_message(
                    chat_id=query.message.chat_id, 
                    text="Mensagem agendada cancelada com sucesso!", 
                    reply_markup=main_menu_keyboard()
                )
            
            else:
                await query.message.reply_text("Mensagem não encontrada.", reply_markup=main_menu_keyboard())

        except Exception as e:
            logger.error(f"Erro ao cancelar a mensagem no banco de dados: {e}")
            await query.message.reply_text("Erro ao cancelar a mensagem. Tente novamente.", reply_markup=main_menu_keyboard())

# Adicionar um callback separado para o botão "Voltar ao menu principal"
async def back_to_cancel_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.message.reply_text("Cancelamento abortado. Retornando à lista de mensagens agendadas...")
    await list_group_scheduled_messages(update, context)

# Callback para retornar ao menu principal
async def menu_principal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.message.reply_text("Retornando ao menu principal...", reply_markup=main_menu_keyboard())
            
# Função para enviar a mensagem agendada com um atraso de 3 segundos
async def send_scheduled_message(group_id: int, message_type: str, message_content: str, message_caption=None, message_thumbnail=None):
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT link FROM groups WHERE id=?', (group_id,))
        group_link_result = cursor.fetchone()

        # Verifica se a mensagem ainda existe no banco de dados antes de enviar
        cursor.execute('SELECT COUNT(*) FROM scheduled_messages WHERE group_id=? AND message_content=?', (group_id, message_content))
        remaining_message = cursor.fetchone()

        if remaining_message[0] == 0:
            logger.info(f"Mensagem agendada para {group_id} já foi cancelada. Não será enviada.")
            return

        if group_link_result:
            group_link = group_link_result[0]
            logger.info(f"Tentando enviar mensagem para chat_id/link: {group_link}")
        else:
            logger.error(f"Erro ao buscar o link do grupo com id {group_id}")
            return

    try:
        chat_id = get_chat_id_from_link(group_link)
        is_bot_in_group, _ = await verify_bot_in_group(application.bot, chat_id)
        if not is_bot_in_group:
            logger.error(f"O bot não está mais no grupo ou não tem permissões no grupo: {chat_id}")
            return

        # Garantindo que a legenda não seja None
        message_caption = message_caption or ""

        # Enviar a mensagem de acordo com o tipo
        if message_type == 'text':
            await application.bot.send_message(chat_id=chat_id, text=message_content)
        elif message_type == 'image':
            await application.bot.send_photo(chat_id=chat_id, photo=message_content, caption=message_caption)
        elif message_type == 'video':
            await application.bot.send_video(chat_id=chat_id, video=message_content, caption=message_caption)

        # Adiciona um atraso de 3 segundos entre as mensagens
        await asyncio.sleep(3)
    
    except telegram.error.BadRequest as e:
        logger.error(f"Erro ao enviar mensagem agendada: {e}")
    except Exception as e:
        logger.error(f"Erro inesperado ao enviar mensagem agendada: {e}")

# Função para liberar ou banir um usuário manualmente (por exemplo, via admin)
def update_ban_status(telegram_id, banned_status):
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET banned = ? WHERE telegram_id = ?', (banned_status, telegram_id))
        conn.commit()

# Função para verificar o status de banimento em cada interação
async def check_ban_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    telegram_id = update.effective_user.id
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT banned FROM users WHERE telegram_id=?', (telegram_id,))
        result = cursor.fetchone()

        if result and result[0]:  # Se o usuário está banido
            await update.message.reply_text(
                "Você está banido. Registre-se ou entre em contato com o suporte.",
                reply_markup=start_menu_keyboard()  # Voltar ao menu de registro/login
            )
            return False
    return True

# Função de inicialização
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    telegram_id = user.id

    # Exibe o diretório de trabalho atual para depuração
    print(f"Diretório de trabalho atual: {os.getcwd()}")

    # Defina o caminho para a imagem PNG
    image_path = r'C:\Users\ander\OneDrive\Área de Trabalho\TELEGRAM BOTSS\BOT.png.png'

    # Texto de boas-vindas em três idiomas: Português, Inglês e Chinês Simplificado
    welcome_text_multilingual = (
        f"👋 *Olá, {user.first_name}!*\n"
        "Seja bem-vindo ao Bot!\n"
        "Clique em *Sobre* para entender todas as funcionalidades do bot! 😊\n\n"
        
        f"👋 *Hello, {user.first_name}!* \n"
        "Welcome to the Bot!\n"
        "Click *About* to understand all the bot's features! 😊\n\n"

        f"👋 *你好，{user.first_name}!* \n"
        "欢迎使用此机器人！\n"
        "点击 *关于* 以了解此机器人的所有功能！ 😊"
    )

    try:
        # Verifica se o arquivo existe antes de tentar abri-lo
        if os.path.exists(image_path):
            print(f"Arquivo encontrado: {image_path}")
            # Envia a imagem de boas-vindas com o texto multilíngue
            await context.bot.send_photo(chat_id=telegram_id, photo=open(image_path, 'rb'), caption=welcome_text_multilingual, parse_mode='Markdown')
        else:
            raise FileNotFoundError(f"Arquivo não encontrado: {image_path}")
    except Exception as e:
        logger.error(f"Erro ao enviar a imagem de boas-vindas: {e}")
        await update.message.reply_text("Bem-vindo ao bot! Não consegui carregar a imagem de boas-vindas.")

    # Verifica se o usuário já está registrado e não banido
    if is_user_registered_and_not_banned(telegram_id):
        await update.message.reply_text(
            f"Você já está registrado. Selecione uma opção no menu:",
            reply_markup=main_menu_keyboard()
        )
    else:
        # Redireciona o usuário para o menu de registro e login
        await update.message.reply_text(
            "Selecione uma opção para registro ou login:",
            reply_markup=start_menu_keyboard()
        )

# Função para processar o login
async def handle_login_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if query.data == "login":
        await query.edit_message_text(text="Por favor, envie seu e-mail para login:")
        context.user_data['login'] = True

# Função para processar o registro
async def handle_register_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if query.data == "register":
        # Solicita o e-mail para registro, sem exibir o menu de registro novamente
        await query.edit_message_text(text="Por favor, envie seu e-mail para registro:")
        context.user_data['register'] = True

# Atualização no handle_message para verificar o banimento antes de prosseguir
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_data = context.user_data
    telegram_id = update.effective_user.id

    # Verificar se o usuário está banido antes de qualquer ação
    if not await check_ban_status(update, context):
        return

    # Lógica de agendamento de mensagens (incluindo texto, imagem e vídeo)
    if user_data.get('awaiting_schedule_time'):
        schedule_type = user_data['schedule_type']
        schedule_time = update.message.text.strip()

        # Oculta a mensagem enviada pelo usuário (horário ou data)
        await safe_delete_message(context.bot, update.effective_chat.id, update.message.message_id)

        if schedule_type == 'daily':
            if is_valid_time_format(schedule_time):
                user_data['schedule_time'] = schedule_time
                group_id = user_data.get('selected_group_id')
                content_type = user_data.get('content_type')
                message_content = user_data.get('message_content')

                schedule_message(telegram_id, group_id, content_type, message_content, schedule_time, user_data.get('message_caption'))
                await update.message.reply_text("Mensagem agendada diariamente com sucesso!")
            else:
                await update.message.reply_text("Formato inválido. Por favor, envie no formato 'HH:MM' (ex: 14:30).")
                return

        elif schedule_type == 'specific':
            parsed_time = parse_schedule_time(schedule_time)
            if parsed_time:
                user_data['schedule_time'] = parsed_time.strftime("%d-%m-%Y %H:%M")
                group_id = user_data.get('selected_group_id')
                content_type = user_data.get('content_type')
                message_content = user_data.get('message_content')

                schedule_message(telegram_id, group_id, content_type, message_content, user_data['schedule_time'], user_data.get('message_caption'))
                await update.message.reply_text("Mensagem agendada para a data específica com sucesso!")
            else:
                await update.message.reply_text("Formato inválido. Por favor, envie no formato 'dd-mm-aaaa HH:MM' (ex: 01-01-2024 14:30).")
                return

        user_data['awaiting_schedule_time'] = False
        await update.message.reply_text("Agendamento concluído. Retornando ao menu principal.", reply_markup=main_menu_keyboard())
        return

    if user_data.get('awaiting_group_link'):
        group_link = update.message.text
        chat_id = get_chat_id_from_link(group_link)

        is_bot_in_group, chat = await verify_bot_in_group(context.bot, chat_id)
        if is_bot_in_group:
            with db_connection() as conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute('SELECT COUNT(*) FROM groups WHERE user_id=?', (telegram_id,))
                    group_count = cursor.fetchone()[0]

                    if group_count < MAX_GROUPS:
                        group_name = chat.title if chat else "Grupo cadastrado"
                        cursor.execute('INSERT INTO groups (user_id, group_name, link) VALUES (?, ?, ?)', 
                                       (telegram_id, group_name, group_link))
                        conn.commit()
                        await update.message.reply_text("Grupo adicionado com sucesso!")
                    else:
                        await update.message.reply_text(f"Você já atingiu o número máximo de grupos permitidos ({MAX_GROUPS}).")
                except sqlite3.Error as e:
                    logger.error(f"Erro ao adicionar grupo: {e}")
                    await update.message.reply_text("Erro ao adicionar o grupo.")
        else:
            await update.message.reply_text("O bot não está no grupo ou não tem permissões adequadas.")

        user_data['awaiting_group_link'] = False
        await update.message.reply_text("Selecione uma opção abaixo:", reply_markup=main_menu_keyboard())
        return

    elif user_data.get('awaiting_message_content'):
        content_type = user_data.get('content_type')  # Recuperando o content_type

        if content_type == 'text':
            message_content = update.message.text
        elif content_type == 'image':
            if update.message.photo:
                message_content = update.message.photo[-1].file_id
                user_data['message_caption'] = update.message.caption or ""
                user_data['message_thumbnail'] = update.message.photo[-1].file_id  # Usando a mesma imagem como thumbnail
            else:
                await update.message.reply_text("Por favor, envie uma imagem válida.")
                return
        elif content_type == 'video':
            if update.message.video:
                message_content = update.message.video.file_id
                user_data['message_caption'] = update.message.caption or ""
                user_data['message_thumbnail'] = update.message.video.thumb.file_id if hasattr(update.message.video, 'thumb') else None  # Corrigido para acessar a thumbnail
            else:
                await update.message.reply_text("Por favor, envie um vídeo válido.")
                return

        # Oculta a mensagem de conteúdo enviada pelo usuário
        await safe_delete_message(context.bot, update.effective_chat.id, update.message.message_id)

        user_data['message_content'] = message_content
        await update.message.reply_text(
            "Escolha o tipo de agendamento:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Agendar Diário", callback_data='schedule_daily')],
                [InlineKeyboardButton("Data Específica", callback_data='schedule_specific')]
            ])
        )
        user_data['awaiting_schedule_time'] = True
        user_data['awaiting_message_content'] = False
        return

    elif user_data.get('login'):
        user_data['login'] = False
        email = update.message.text
        user_data['email'] = email
        await update.message.reply_text("Por favor, envie sua senha:")
        user_data['awaiting_login_password'] = True
        return

    elif user_data.get('awaiting_login_password'):
        password = update.message.text
        user_data['password'] = password
        user_id = check_user(user_data['email'], user_data['password'])

        if user_id == "banned":  # Se o usuário estiver banido, volta ao menu de registro
            await update.message.reply_text(
                "Você está banido. Registre-se ou entre em contato com o suporte.",
                reply_markup=start_menu_keyboard()  # Aqui, voltamos ao menu de registro
            )
            # Limpa os dados de login
            user_data.clear()
        elif user_id:
            await update.message.reply_text("Login realizado com sucesso!")
            await update.message.reply_text("Você está no menu principal.", reply_markup=main_menu_keyboard())
        else:
            await update.message.reply_text("Falha no login. Verifique suas credenciais.")
            await update.message.reply_text("Selecione uma opção abaixo:", reply_markup=start_menu_keyboard())  # Volta ao menu de registro
            # Limpa os dados de login para permitir o registro
            user_data.clear()
        return

    elif user_data.get('register'):
        user_data['register'] = False
        email = update.message.text
        user_data['email'] = email
        await update.message.reply_text("Por favor, envie uma senha:")
        user_data['awaiting_password'] = True
        return

    elif user_data.get('awaiting_password'):
        password = update.message.text
        user_data['password'] = password
        user_data['awaiting_password'] = False
        await update.message.reply_text("Por favor, envie seu número de WhatsApp:")
        user_data['awaiting_whatsapp_number'] = True
        return

    elif user_data.get('awaiting_whatsapp_number'):
        whatsapp_number = update.message.text
        user_data['whatsapp_number'] = whatsapp_number
        user_data['awaiting_whatsapp_number'] = False

        period_buttons = [
            [InlineKeyboardButton("30 dias", callback_data='30')],
            [InlineKeyboardButton("90 dias", callback_data='90')],
            [InlineKeyboardButton("180 dias", callback_data='180')],
            [InlineKeyboardButton("365 dias", callback_data='365')],
        ]
        await update.message.reply_text(
            "Selecione o período de acesso:",
            reply_markup=InlineKeyboardMarkup(period_buttons)
        )
        return

# Função auxiliar para verificar o status do bot em um grupo
async def verify_bot_in_group(bot, chat_id):
    try:
        chat = await bot.get_chat(chat_id)
        chat_member = await bot.get_chat_member(chat_id, bot.id)

        if chat_member.status in [ChatMember.ADMINISTRATOR, ChatMember.MEMBER]:
            logger.info(f"O bot está no grupo/canal: {chat.title} ({chat_id})")
            return True, chat
        else:
            logger.warning(f"O bot não tem as permissões necessárias no grupo/canal: {chat.title} ({chat_id})")
            return False, None
    except telegram.error.BadRequest as e:
        logger.error(f"Erro ao verificar a presença do bot no grupo/canal: {e}")
        return False, None

# Verifica se o link é um username ou um chat_id
def get_chat_id_from_link(group_link: str) -> str:
    if group_link.startswith("https://t.me/"):
        chat_id = group_link.split("/")[-1]
        if not chat_id.startswith("@") and not chat_id.startswith("-"):
            chat_id = f"@{chat_id}"
        return chat_id
    return group_link

# Função para lidar com o menu principal e submenus
async def handle_menu_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    # Verificação se a mensagem ainda existe antes de tentar editá-la
    if query.message:
        await safe_edit_message_text(query, "Escolha uma opção no menu:", reply_markup=main_menu_keyboard())
    else:
        await query.message.reply_text("Escolha uma opção no menu:", reply_markup=main_menu_keyboard())

    if query.data == "adicionar_link":
        await query.edit_message_text(
            text="Por favor, envie o link do grupo:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Voltar ao Menu Principal 🔙", callback_data='menu_principal')]
            ])
        )
        context.user_data['awaiting_group_link'] = True

    elif query.data == "ver_grupos":
        user_id = update.effective_user.id
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT group_name, link FROM groups WHERE user_id=?', (user_id,))
            groups = cursor.fetchall()
            if groups:
                groups_list = "\n".join([f"{name} - {link}" for name, link in groups])
                # Inclui um botão de "Voltar ao Menu Principal"
                await query.edit_message_text(
                    f"Grupos cadastrados:\n{groups_list}",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("Voltar ao Menu Principal 🔙", callback_data='menu_principal')]
                    ])
                )
            else:
                await query.edit_message_text(
                    "Nenhum grupo cadastrado.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("Voltar ao Menu Principal 🔙", callback_data='menu_principal')]
                    ])
                )

    elif query.data == "remover_grupo":
        user_id = update.effective_user.id
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT group_name, id FROM groups WHERE user_id=?', (user_id,))
            groups = cursor.fetchall()
            if groups:
                group_buttons = [[InlineKeyboardButton(f"Grupo {i+1}: {name}", callback_data=f"select_remove_grupo_{group_id}")] for i, (name, group_id) in enumerate(groups)]
                group_keyboard = InlineKeyboardMarkup(group_buttons)
                await query.edit_message_text("Selecione o grupo que deseja remover:", reply_markup=group_keyboard)
            else:
                await query.edit_message_text(
                    "Nenhum grupo cadastrado para remover.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("Voltar 🔙", callback_data='menu_principal')]
                    ])
                )

    elif query.data.startswith("select_remove_grupo_"):
        group_id = int(query.data.split("_")[-1])
        user_id = update.effective_user.id
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT group_name, link FROM groups WHERE id=? AND user_id=?', (group_id, user_id))
            selected_group = cursor.fetchone()
            if selected_group:
                group_name, group_link = selected_group
                confirmation_buttons = [
                    [InlineKeyboardButton("Sim ✅", callback_data=f"confirm_remove_{group_id}")],
                    [InlineKeyboardButton("Retornar à seleção de escolha", callback_data='menu')]
                ]
                await query.edit_message_text(f"Deseja remover o grupo '{group_name}' com o link {group_link}?", reply_markup=InlineKeyboardMarkup(confirmation_buttons))
            else:
                await query.edit_message_text("Grupo não encontrado.")

    elif query.data.startswith("confirm_remove_"):
        group_id = int(query.data.split("_")[-1])
        user_id = update.effective_user.id
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM scheduled_messages WHERE group_id=? AND user_id=?', (group_id, user_id))
            cursor.execute('DELETE FROM groups WHERE id=? AND user_id=?', (group_id, user_id))
            conn.commit()
            await query.edit_message_text(
            "O grupo e suas mensagens agendadas foram removidos com sucesso.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Voltar 🔙", callback_data='remover_grupo')]
            ])
        )

    elif query.data == 'agendar_cancelar':
        user_id = update.effective_user.id
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, group_name FROM groups WHERE user_id=?', (user_id,))
            groups = cursor.fetchall()

            if groups:
                group_buttons = [
                    [InlineKeyboardButton(f"Grupo {i+1}: {name}", callback_data=f"select_agendar_grupo_{group_id}")] 
                    for i, (group_id, name) in enumerate(groups)
                ]
                group_buttons.append([InlineKeyboardButton("Voltar ao Menu Principal 🔙", callback_data='menu_principal')])
                group_keyboard = InlineKeyboardMarkup(group_buttons)
                await query.edit_message_text("Escolha o grupo para agendar uma mensagem ou cancelar uma mensagem agendada:", reply_markup=group_keyboard)
            else:
             await query.edit_message_text(
                 "Nenhum grupo cadastrado para agendamento.",
                 reply_markup=InlineKeyboardMarkup([
                     [InlineKeyboardButton("Voltar 🔙", callback_data='menu_principal')]
                 ])
             )

    elif query.data.startswith("select_agendar_grupo_"):
        group_id = int(query.data.split("_")[-1])
        context.user_data['selected_group_id'] = group_id
        await query.edit_message_text(
            text="Escolha uma ação:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Agendar Nova Mensagem 📝", callback_data='agendar_nova')],
                [InlineKeyboardButton("Cancelar Mensagem Agendada 🗑", callback_data='cancelar_mensagem')],
                [InlineKeyboardButton("Voltar 🔙", callback_data='agendar_cancelar')]  # Novo botão "Voltar"
            ])
        )

    elif query.data == 'cancelar_mensagem':
        await list_group_scheduled_messages(update, context)

    elif query.data == 'agendar_nova':
        context.user_data['awaiting_content_type'] = True
        await query.edit_message_text(
            text="Escolha o tipo de conteúdo para enviar:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Texto ✍️", callback_data='content_text')],
                [InlineKeyboardButton("Imagem 🖼", callback_data='content_image')],
                [InlineKeyboardButton("Vídeo 🎥", callback_data='content_video')],
                [InlineKeyboardButton("Voltar 🔙", callback_data=f'select_agendar_grupo_{context.user_data["selected_group_id"]}')],
            ])
        )

    elif query.data == 'content_text':
        context.user_data['content_type'] = 'text'
        context.user_data['awaiting_message_content'] = True
        await query.edit_message_text("Por favor, envie a mensagem de texto que deseja agendar.")

    elif query.data == 'content_image':
        context.user_data['content_type'] = 'image'
        context.user_data['awaiting_message_content'] = True
        await query.edit_message_text("Por favor, envie a imagem que deseja agendar.")

    elif query.data == 'content_video':
        context.user_data['content_type'] = 'video'
        context.user_data['awaiting_message_content'] = True
        await query.edit_message_text("Por favor, envie o vídeo que deseja agendar.")

    elif query.data == 'schedule_daily':
        context.user_data['schedule_type'] = 'daily'
        await query.edit_message_text(
            text="Envie o horário diário no formato 'HH:MM' (ex: 14:30):"
        )
        context.user_data['awaiting_schedule_time'] = True

    elif query.data == 'schedule_specific':
        context.user_data['schedule_type'] = 'specific'
        await query.edit_message_text(
            text="Envie a data e hora no formato 'dd-mm-aaaa HH:MM' (ex: 01-01-2024 14:30):"
        )
        context.user_data['awaiting_schedule_time'] = True

    elif context.user_data.get('awaiting_schedule_time'):
        schedule_type = context.user_data['schedule_type']
        schedule_time = update.message.text

        if schedule_type == 'daily':
            if is_valid_time_format(schedule_time):
                context.user_data['schedule_time'] = schedule_time
                await update.message.reply_text("Mensagem agendada diariamente com sucesso!")
            else:
                await update.message.reply_text("Formato inválido. Por favor, envie no formato 'HH:MM' (ex: 14:30).")

        elif schedule_type == 'specific':
            parsed_time = parse_schedule_time(schedule_time)
            if parsed_time:
                context.user_data['schedule_time'] = parsed_time.strftime("%d-%m-%Y %H:%M")
                await update.message.reply_text("Mensagem agendada para a data específica com sucesso!")
            else:
                await update.message.reply_text("Formato inválido. Por favor, envie no formato 'dd-mm-aaaa HH:MM' (ex: 01-01-2024 14:30).")

        context.user_data['awaiting_schedule_time'] = False
        await update.message.reply_text("Agendamento concluído. Retornando ao menu principal.", reply_markup=main_menu_keyboard())

# Função para enviar a mensagem agendada
async def send_scheduled_message(group_id: int, message_type: str, message_content: str, message_caption=None, message_thumbnail=None):
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT link FROM groups WHERE id=?', (group_id,))
        group_link_result = cursor.fetchone()
        if group_link_result:
            group_link = group_link_result[0]
            logger.info(f"Tentando enviar mensagem para chat_id/link: {group_link}")
        else:
            logger.error(f"Erro ao buscar o link do grupo com id {group_id}")
            return

        cursor.execute('SELECT COUNT(*) FROM scheduled_messages WHERE group_id=?', (group_id,))
        remaining_messages = cursor.fetchone()[0]
        if remaining_messages == 0:
            logger.info(f"Nenhuma mensagem agendada restante para o grupo {group_id}. Cancelando envio.")
            return

    try:
        chat_id = get_chat_id_from_link(group_link)

        is_bot_in_group, _ = await verify_bot_in_group(application.bot, chat_id)
        if not is_bot_in_group:
            logger.error(f"O bot não está mais no grupo ou não tem permissões no grupo: {chat_id}")
            return

        # Garantindo que a legenda não seja None
        message_caption = message_caption or None

        # Verifica se a mensagem é texto
        if message_type == 'text':
            logger.info(f"Enviando mensagem de texto: {message_content}")
            await application.bot.send_message(chat_id=chat_id, text=message_content)
        
        # Verifica se a mensagem é imagem e envia com a legenda
        elif message_type == 'image':
            if message_content:
                logger.info(f"Enviando imagem com legenda: {message_caption}")
                await application.bot.send_photo(chat_id=chat_id, photo=message_content, caption=message_caption)
            else:
                logger.warning("Conteúdo da imagem não encontrado.")
        
        # Verifica se a mensagem é vídeo e envia com a legenda
        elif message_type == 'video':
            if message_content:
                logger.info(f"Enviando vídeo com legenda: {message_caption}")
                await application.bot.send_video(chat_id=chat_id, video=message_content, caption=message_caption)
            else:
                logger.warning("Conteúdo do vídeo não encontrado.")
    
    except telegram.error.BadRequest as e:
        logger.error(f"Erro ao enviar mensagem agendada: {e}")
    except Exception as e:
        logger.error(f"Erro inesperado ao enviar mensagem agendada: {e}")

# Função para lidar com o registro do usuário
async def handle_register_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if query.data == "register":
        await query.edit_message_text(text="Por favor, envie seu e-mail para registro:")
        context.user_data['register'] = True

# Captura a seleção do período
async def handle_period_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    selected_period = query.data
    if selected_period in ['30', '90', '180', '365']:

        user_data = context.user_data
        telegram_id = update.effective_user.id
        expiration_date = datetime.now() + timedelta(days=int(selected_period))

        user_id = add_user(
            telegram_id, 
            user_data['email'], 
            user_data['password'], 
            user_data['whatsapp_number'], 
            expiration_date
        ) 

        if user_id:
            await query.edit_message_text("Registrado com sucesso! Solicite o desbloqueio via WhatsApp.")
            await query.message.reply_text(f"Envie uma mensagem para {WHATSAPP_NUMBER} com a seguinte mensagem: {WHATSAPP_MESSAGE_REGISTRATION}")
            support_button = InlineKeyboardButton("Suporte ☎️", url=f"https://wa.me/{WHATSAPP_NUMBER.replace('+', '')}?text={WHATSAPP_MESSAGE_REGISTRATION.replace(' ', '%20')}") 
            menu_button = InlineKeyboardButton("Menu de Registro 📄", callback_data='menu_registro')
            await query.message.reply_text(
                "Selecione uma opção abaixo:",
                reply_markup=InlineKeyboardMarkup([[menu_button, support_button]])
            )
        else:
            await query.message.reply_text("Falha no registro. O usuário já existe ou ocorreu um erro.")
            await query.message.reply_text("Selecione uma opção abaixo:", reply_markup=main_menu_keyboard())

# Função para lidar com o menu de registro
async def handle_menu_register(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        text="Escolha uma opção para registro ou login:",
        reply_markup=start_menu_keyboard()
    )

# Função principal para inicializar o bot
def main():
    global application
    application = Application.builder().token(TOKEN).build()

    # Adiciona handlers para os diferentes textos "Sobre" nos 3 idiomas
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_sobre, pattern='^sobre$'))
    application.add_handler(CallbackQueryHandler(handle_sobre_pt, pattern='^sobre_pt$'))
    application.add_handler(CallbackQueryHandler(handle_sobre_en, pattern='^sobre_en$'))
    application.add_handler(CallbackQueryHandler(handle_sobre_zh, pattern='^sobre_zh$'))

    # Handler para a seleção de idioma
    application.add_handler(CallbackQueryHandler(handle_select_language, pattern='^select_language$'))
    application.add_handler(CallbackQueryHandler(set_language_pt, pattern='^set_language_pt$'))
    application.add_handler(CallbackQueryHandler(set_language_en, pattern='^set_language_en$'))
    application.add_handler(CallbackQueryHandler(set_language_zh, pattern='^set_language_zh$'))

    # Outros handlers existentes
    application.add_handler(CallbackQueryHandler(handle_register_selection, pattern='^register$'))
    application.add_handler(CallbackQueryHandler(handle_login_selection, pattern='^login$'))
    application.add_handler(CallbackQueryHandler(handle_menu_register, pattern='menu_registro'))
    application.add_handler(CallbackQueryHandler(handle_period_selection, pattern='^(30|90|180|365)$'))
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(clear_interface, pattern='clear_interface'))
    application.add_handler(CallbackQueryHandler(handle_menu_selection, pattern='^adicionar_link|ver_grupos|remover_grupo|select_remove_grupo_|confirm_remove_|menu|agendar_cancelar|select_agendar_grupo_|agendar_nova|cancelar_mensagem|select_cancelar_mensagem_|content_text|content_image|content_video|schedule_daily|schedule_specific|menu_principal$'))
    application.add_handler(CallbackQueryHandler(confirm_cancel_message, pattern='^confirm_cancel_'))
    application.add_handler(CallbackQueryHandler(cancelar_mensagem_agendada, pattern='^cancel_message_'))
    application.add_handler(CallbackQueryHandler(back_to_cancel_selection, pattern='^back_to_cancel_selection$'))
    application.add_handler(CallbackQueryHandler(menu_principal, pattern='menu_principal'))
    application.run_polling()

if __name__ == "__main__":
    # Captura de exceções não tratadas
    def handle_exception(exc_type, exc_value, exc_traceback):
        logger.error("Erro não tratado", exc_info=(exc_type, exc_value, exc_traceback))

    sys.excepthook = handle_exception
    main()
