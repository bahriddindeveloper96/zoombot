from django.core.management.base import BaseCommand
from telegram_bot.bot import ZoomTelegramBot
from django.conf import settings

class Command(BaseCommand):
    help = 'Run Telegram bot'

    def handle(self, *args, **options):
        bot = ZoomTelegramBot(settings.TELEGRAM_BOT_TOKEN)
        self.stdout.write(self.style.SUCCESS('Starting Telegram bot...'))
        bot.run()
