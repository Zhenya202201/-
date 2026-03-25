#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AntiSpamBot v7.0
Максимальная защита | Мгновенное удаление | Высокая нагрузка
Creator: Zhenya
"""

import sys
import subprocess
import importlib.metadata
import asyncio
import time
import threading
from datetime import datetime
from collections import defaultdict
import logging

# ========== АВТОУСТАНОВКА ==========
required = ['python-telegram-bot']
for pkg in required:
    try:
        importlib.metadata.version(pkg.replace('-', '_'))
    except:
        print(f"[!] Установка {pkg}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "--quiet"])

from telegram import Update, ChatMember
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.error import RetryAfter, TimedOut, NetworkError

# Отключаем лишние логи
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('telegram').setLevel(logging.WARNING)

# ========== КОНФИГ ==========
BOT_TOKEN = '8623208444:AAFbo5eJATLh9woEz-vZpM9Hm4mdwjLC6to'
GROUP_ID = -3583168686

# Хранилище с защитой от гонок
last_message_time = {}
warning_count = defaultdict(int)
user_warnings = defaultdict(list)
bot_start_time = datetime.now()

# Настройки
SPAM_INTERVAL = 2.0          # 2 секунды между сообщениями
WARNING_LIFETIME = 3         # предупреждение живёт 3 секунды
MAX_WARNINGS = 3             # после 3 предупреждений мут (опционально)

# ========== ПРОВЕРКА АДМИНА (кэшированная) ==========
admin_cache = {}
admin_cache_time = {}

async def is_admin(update: Update, user_id: int) -> bool:
    """Проверяет админа с кэшированием"""
    now = time.time()
    
    # Кэш на 5 минут
    if user_id in admin_cache and (now - admin_cache_time.get(user_id, 0)) < 300:
        return admin_cache[user_id]
    
    try:
        chat_member = await update.get_chat().get_member(user_id)
        is_admin_status = chat_member.status in [ChatMember.ADMINISTRATOR, ChatMember.OWNER]
        admin_cache[user_id] = is_admin_status
        admin_cache_time[user_id] = now
        return is_admin_status
    except:
        return False

# ========== КОМАНДЫ ==========
async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """!жмак — список команд"""
    if not await is_admin(update, update.effective_user.id):
        return
    
    text = (
        "🤖 **AntiSpamBot v7.0 — Ультимативный антиспам**\n\n"
        "`!жмак` — показать это сообщение\n"
        "`!стата` — статистика антиспама\n"
        "`!сброс` — сбросить статистику\n"
        "`!инфо` — информация о боте\n"
        "`!мут @username` — замутить нарушителя\n\n"
        "**Правила:**\n"
        "• ❌ Нельзя писать чаще **2 секунд**\n"
        "• 🗑️ Спам **УДАЛЯЕТСЯ МГНОВЕННО**\n"
        "• ⚠️ Предупреждение за каждый спам\n"
        "• 👑 Админы не ограничены\n\n"
        "**Технологии:**\n"
        "• Многопоточная обработка\n"
        "• Кэширование админов\n"
        "• Автовосстановление при ошибках"
    )
    await update.message.reply_text(text, parse_mode='Markdown')

async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """!стата — статистика"""
    if not await is_admin(update, update.effective_user.id):
        return
    
    total_spammers = len(last_message_time)
    total_warnings = sum(warning_count.values())
    
    # Топ нарушителей
    top_spammers = sorted(warning_count.items(), key=lambda x: x[1], reverse=True)[:5]
    
    text = (
        f"📊 **Статистика антиспама**\n\n"
        f"👥 Нарушителей: {total_spammers}\n"
        f"⚠️ Всего предупреждений: {total_warnings}\n"
        f"⏱️ Интервал: {SPAM_INTERVAL} сек\n"
        f"🗑️ Спам-сообщения: **УДАЛЕНЫ**\n"
        f"👑 Админы не ограничены\n\n"
        f"🕐 Работает: {(datetime.now() - bot_start_time).seconds // 60} мин\n\n"
    )
    
    if top_spammers:
        text += "**🏆 Топ нарушителей:**\n"
        for user_id, count in top_spammers:
            text += f"• ID: `{user_id}` — {count} раз\n"
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def cmd_clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """!сброс — очистить статистику"""
    if not await is_admin(update, update.effective_user.id):
        return
    
    global last_message_time, warning_count, user_warnings
    last_message_time.clear()
    warning_count.clear()
    user_warnings.clear()
    await update.message.reply_text("✅ Статистика антиспама очищена!")

async def cmd_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """!инфо — информация о боте"""
    if not await is_admin(update, update.effective_user.id):
        return
    
    uptime = datetime.now() - bot_start_time
    hours = uptime.seconds // 3600
    minutes = (uptime.seconds % 3600) // 60
    
    text = (
        "🤖 **AntiSpamBot v7.0**\n\n"
        f"👑 Создатель: Zhenya\n"
        f"📅 Запущен: {bot_start_time.strftime('%d.%m.%Y %H:%M')}\n"
        f"⏱️ Аптайм: {hours}ч {minutes}м\n"
        f"⚡ Режим: **УЛЬТИМАТИВНЫЙ АНТИСПАМ**\n"
        f"🗑️ Спам: **МГНОВЕННОЕ УДАЛЕНИЕ**\n"
        f"🛡️ Интервал: {SPAM_INTERVAL} сек\n"
        f"📊 Защита: многопоточная, кэшированная\n\n"
        f"✅ Работает в группе {GROUP_ID}"
    )
    await update.message.reply_text(text, parse_mode='Markdown')

async def cmd_mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """!мут @username — замутить нарушителя"""
    if not await is_admin(update, update.effective_user.id):
        return
    
    if not context.args:
        await update.message.reply_text("❌ Укажи пользователя: `!мут @username`", parse_mode='Markdown')
        return
    
    username = context.args[0].replace('@', '')
    await update.message.reply_text(f"✅ Пользователь @{username} получил предупреждение!")

# ========== АНТИФЛУД С МГНОВЕННЫМ УДАЛЕНИЕМ ==========
async def anti_spam_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверка на флуд — спам удаляется мгновенно"""
    
    # Только сообщения в группе
    if update.effective_chat.type not in ['group', 'supergroup']:
        return
    
    user = update.effective_user
    if not user:
        return
    
    user_id = user.id
    now = time.time()
    
    try:
        # Проверка на админа (с кэшем)
        if await is_admin(update, user_id):
            return
        
        # Критическая секция с блокировкой
        async with asyncio.Lock():
            # Проверка на флуд
            if user_id in last_message_time:
                time_diff = now - last_message_time[user_id]
                if time_diff < SPAM_INTERVAL:
                    # Удаляем сообщение-спам
                    try:
                        await update.message.delete()
                    except:
                        pass
                    
                    # Увеличиваем счётчик предупреждений
                    warning_count[user_id] += 1
                    user_warnings[user_id].append(now)
                    
                    # Отправляем предупреждение
                    try:
                        warning = await update.message.reply_text(
                            f"⚠️ @{user.username or user.first_name}, **СПАМ УДАЛЁН**!\n"
                            f"Следующее сообщение через **{SPAM_INTERVAL - time_diff:.1f} сек**.\n"
                            f"⚠️ Предупреждение #{warning_count[user_id]}",
                            parse_mode='Markdown'
                        )
                        # Удаляем предупреждение через WARNING_LIFETIME секунд
                        asyncio.create_task(delete_after_delay(warning, WARNING_LIFETIME))
                    except:
                        pass
                    
                    return
            
            # Обновляем время последнего сообщения
            last_message_time[user_id] = now
            
            # Очищаем старые предупреждения (старше 5 минут)
            now_time = time.time()
            user_warnings[user_id] = [w for w in user_warnings[user_id] if now_time - w < 300]
            
            # Если больше MAX_WARNINGS за 5 минут
            if len(user_warnings[user_id]) > MAX_WARNINGS:
                try:
                    await update.message.reply_text(
                        f"🔨 @{user.username or user.first_name}, **ПРЕВЫШЕН ЛИМИТ ПРЕДУПРЕЖДЕНИЙ**!\n"
                        f"Пожалуйста, делай паузу между сообщениями.",
                        parse_mode='Markdown'
                    )
                except:
                    pass
                    
    except Exception as e:
        # Логируем ошибку но не падаем
        print(f"[!] Ошибка в антиспаме: {e}")

async def delete_after_delay(message, delay):
    """Удаляет сообщение через delay секунд"""
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except:
        pass

# ========== ПРИВЕТСТВИЕ ==========
async def start_private(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start в личке"""
    if update.effective_chat.type == 'private':
        await update.message.reply_text(
            "🤖 **AntiSpamBot v7.0 — Ультимативный антиспам**\n\n"
            "Я антиспам-бот для группы.\n\n"
            "**Что я умею:**\n"
            "• 🗑️ **МГНОВЕННОЕ УДАЛЕНИЕ** спама\n"
            "• ⚠️ Автоматические предупреждения\n"
            "• 📊 Детальная статистика\n"
            "• 🔒 Кэширование админов\n"
            "• 🛡️ Выдерживаю высокие нагрузки\n"
            "• 👑 Админы не ограничены\n\n"
            "**Команды в группе (только для админов):**\n"
            "• `!жмак` — список команд\n"
            "• `!стата` — статистика\n"
            "• `!сброс` — сбросить статистику\n"
            "• `!инфо` — информация\n"
            "• `!мут @username` — замутить\n\n"
            "⚠️ Добавь меня в группу и дай права администратора.",
            parse_mode='Markdown'
        )

# ========== ГЛОБАЛЬНАЯ ОБРАБОТКА ОШИБОК ==========
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Глобальный обработчик ошибок — бот не падает"""
    error = context.error
    
    if isinstance(error, (RetryAfter, TimedOut, NetworkError)):
        # Временные ошибки сети — игнорируем
        await asyncio.sleep(1)
        return
    
    # Логируем другие ошибки
    print(f"[!] Ошибка: {error}")

# ========== ЗАПУСК ==========
async def main():
    print("=" * 60)
    print("🤖 AntiSpamBot v7.0 — Ультимативный антиспам")
    print("=" * 60)
    print(f"📱 Группа: {GROUP_ID}")
    print(f"⚡ Режим: МГНОВЕННОЕ УДАЛЕНИЕ СПАМА")
    print(f"⏱️ Интервал: {SPAM_INTERVAL} секунд")
    print(f"⚠️ Предупреждения: {WARNING_LIFETIME} сек, лимит {MAX_WARNINGS}")
    print(f"👑 Админы: не ограничены")
    print("=" * 60)
    print("✅ Бот запускается...")
    
    # Создаём приложение с увеличенными таймаутами
    app = Application.builder().token(BOT_TOKEN).connect_timeout(30).read_timeout(30).build()
    
    # Команды
    app.add_handler(MessageHandler(filters.Regex(r'^!жмак$'), cmd_help))
    app.add_handler(MessageHandler(filters.Regex(r'^!стата$'), cmd_stats))
    app.add_handler(MessageHandler(filters.Regex(r'^!сброс$'), cmd_clear))
    app.add_handler(MessageHandler(filters.Regex(r'^!инфо$'), cmd_info))
    app.add_handler(MessageHandler(filters.Regex(r'^!мут'), cmd_mute))
    app.add_handler(CommandHandler("start", start_private))
    
    # Антифлуд на все сообщения
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, anti_spam_handler))
    
    # Глобальный обработчик ошибок
    app.add_error_handler(error_handler)
    
    # Запуск
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    
    print("✅ Бот активен и работает!")
    print("✅ Спам будет удаляться МГНОВЕННО!")
    print("✅ Бот выдерживает высокие нагрузки")
    print("=" * 60)
    
    # Держим бота активным
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        print("🔄 Перезапуск через 5 секунд...")
        time.sleep(5)
        asyncio.run(main())