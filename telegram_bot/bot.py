import logging
import os
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from django.contrib.auth.models import User
from django.utils import timezone
from django.contrib.auth import get_user_model
from asgiref.sync import sync_to_async
from .models import TelegramUser, Department, DepartmentAdmin
from booking.models import ZoomMeeting, BookingRequest

logger = logging.getLogger(__name__)
User = get_user_model()

class ZoomTelegramBot:
    def __init__(self, token):
        self.application = Application.builder().token(token).build()
        self.setup_handlers()

    def setup_handlers(self):
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("profile", self.profile_command))
        self.application.add_handler(CommandHandler("book", self.book_command))
        self.application.add_handler(CommandHandler("my_meetings", self.my_meetings_command))
        self.application.add_handler(CommandHandler("requests", self.requests_command))
        self.application.add_handler(CommandHandler("admin", self.admin_command))
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.text_handler))

    @sync_to_async
    def create_or_get_user(self, user_id, username, first_name, last_name):
        """Create or get Django user synchronously"""
        try:
            django_user = User.objects.get(username=f"tg_{user_id}")
        except User.DoesNotExist:
            django_user = User.objects.create_user(
                username=f"tg_{user_id}", 
                email=f"{user_id}@telegram.bot",
                password=os.urandom(12).hex()  # Random password
            )
        return django_user

    @sync_to_async
    def create_or_get_telegram_user(self, user_id, username, first_name, last_name, django_user):
        """Create or get Telegram user synchronously"""
        # Handle None values for optional fields
        if first_name is None:
            first_name = ""
        if last_name is None:
            last_name = ""
        if username is None:
            username = ""
        
        # Create new user with explicit field values
        telegram_user = TelegramUser.objects.create(
            telegram_id=user_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            user=django_user
        )
        
        return telegram_user

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        
        # Handle None values for user fields
        first_name = user.first_name or ""
        last_name = user.last_name or ""
        username = user.username or ""
        
        # Create Django user first
        django_user = await self.create_or_get_user(user.id, username, first_name, last_name)
        
        # Create Telegram user
        telegram_user = await self.create_or_get_telegram_user(user.id, username, first_name, last_name, django_user)

        welcome_text = f"""
🎉 **Zoomga xush kelibsiz!** 🎉

Assalomu alaykum, {first_name}!

Men Zoom uchrashuvlari boshqaruv botiman. Quyidagi imkoniyatlarga egaman:

📅 **Uchrashuv yaratish**
⏰ **Vaqt jadvalini ko'rish**
📊 **So'rovlar yuborish**
👥 **Bo'limlarni boshqarish**

Boshlash uchun /profile buyrug'ini yuboring va profilingizni to'ldiring!
        """

        keyboard = [
            [KeyboardButton("📊 Profil"), KeyboardButton("📅 Uchrashuv yaratish")],
            [KeyboardButton("⏰ Jadval"), KeyboardButton("📋 So'rovlar")],
            [KeyboardButton("❓ Yordam")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        await update.message.reply_text(welcome_text, parse_mode='Markdown', reply_markup=reply_markup)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = """
🤖 **Bot yordam** 🤖

**Asosiy buyruqlar:**
/start - Botni ishga tushirish
/profile - Profilni ko'rish va tahrirlash
/book - Yangi uchrashuv yaratish
/my_meetings - Mening uchrashuvlarim
/requests - So'rovlar
/admin - Admin paneli

**Tugmalar:**
📊 Profil - Shaxsiy ma'lumotlar
📅 Uchrashuv yaratish - Yangi uchrashuv
⏰ Jadval - Kunlik reja
📋 So'rovlar - Arizalar holati

Savollaringiz bo'lsa admin bilan bog'laning!
        """
        await update.message.reply_text(help_text, parse_mode='Markdown')

    async def profile_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        telegram_user = await sync_to_async(TelegramUser.objects.get)(telegram_id=update.effective_user.id)
        
        departments = await sync_to_async(DepartmentAdmin.objects.filter)(telegram_user=telegram_user, is_active=True)
        dept_list = "\n".join([f"🏢 {da.department.name}" for da in departments]) if departments else "🏢 Bo'lim tayinlanmagan"

        profile_text = f"""
📊 **Sizning profilingiz** 📊

👤 Ism: {telegram_user.first_name} {telegram_user.last_name}
🆔 Telegram ID: {telegram_user.telegram_id}
👥 Username: @{telegram_user.username}
🔹 Status: {'👑 Admin' if telegram_user.is_admin else '👤 Foydalanuvchi'}

🏢 **Bo'limlar:**
{dept_list}

📅 **Bugungi uchrashuvlar soni:** {await self.get_today_meeting_count(telegram_user)}
        """

        keyboard = []
        if telegram_user.is_admin:
            keyboard.append([KeyboardButton("👑 Admin panel")])
        keyboard.append([KeyboardButton("⬅️ Orqaga")])
        
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(profile_text, parse_mode='Markdown', reply_markup=reply_markup)

    async def book_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        telegram_user = await sync_to_async(TelegramUser.objects.get)(telegram_id=update.effective_user.id)
        
        if self.check_daily_limit(telegram_user):
            await update.message.reply_text(
                "⚠️ **Kunlik limit to'ldi!**\n\n"
                "Siz kuniga 5 ta uchrashuv yaratishingiz mumkin. "
                "Ertaga yana urinib ko'ring!",
                parse_mode='Markdown'
            )
            return

        departments = await sync_to_async(DepartmentAdmin.objects.filter)(telegram_user=telegram_user, is_active=True)
        if not departments:
            await update.message.reply_text(
                "❌ **Sizda hech qanday bo'lim yo'q!**\n\n"
                "Iltimos, admin bilan bog'laning va o'z Bo'limingizni tayinlang.",
                parse_mode='Markdown'
            )
            return

        keyboard = []
        for dept_admin in departments:
            keyboard.append([InlineKeyboardButton(
                f"🏢 {dept_admin.department.name}", 
                callback_data=f"select_dept_{dept_admin.department.id}"
            )])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "🏢 **Bo'limni tanlang:**",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def my_meetings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        telegram_user = await sync_to_async(TelegramUser.objects.get)(telegram_id=update.effective_user.id)
        
        today = timezone.now().date()
        meetings = await sync_to_async(list)(ZoomMeeting.objects.filter(
            created_by=telegram_user,
            start_time__date=today,
            is_active=True
        ).order_by('start_time'))

        if not meetings:
            await update.message.reply_text(
                "📅 **Bugungi uchrashuvlar yo'q**\n\n"
                "Yangi uchrashuv yaratish uchun /book buyrug'idan foydalaning.",
                parse_mode='Markdown'
            )
            return

        text = "📅 **Bugungi uchrashuvlarim:**\n\n"
        for meeting in meetings:
            status_emoji = {
                'scheduled': '⏰',
                'active': '🟢',
                'ended': '✅',
                'cancelled': '❌'
            }.get(meeting.status, '📋')

            text += f"{status_emoji} **{meeting.title}**\n"
            text += f"🕐 Vaqt: {meeting.start_time.strftime('%H:%M')} - {meeting.end_time.strftime('%H:%M')}\n"
            text += f"🏢 Bo'lim: {meeting.department.name}\n"
            text += f"🔗 Havola: {meeting.meeting_url or 'Yaratilmoqda...'}\n\n"

        await update.message.reply_text(text, parse_mode='Markdown')

    async def requests_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        telegram_user = await sync_to_async(TelegramUser.objects.get)(telegram_id=update.effective_user.id)
        
        requests = await sync_to_async(list)(BookingRequest.objects.filter(
            requested_by=telegram_user
        ).order_by('-created_at')[:5])

        if not requests:
            await update.message.reply_text(
                "📋 **Sizda so'rovlar yo'q**\n\n"
                "Yangi so'rov yaratish uchun /book buyrug'idan foydalaning.",
                parse_mode='Markdown'
            )
            return

        text = "📋 **So'rovlaringiz:**\n\n"
        for request in requests:
            status_emoji = {
                'pending': '⏳',
                'approved': '✅',
                'rejected': '❌',
                'cancelled': '🚫'
            }.get(request.status, '📋')

            text += f"{status_emoji} **{request.title}**\n"
            text += f"🕐 Vaqt: {request.preferred_start_time.strftime('%Y-%m-%d %H:%M')}\n"
            text += f"🏢 Bo'lim: {request.department.name}\n"
            text += f"📊 Holat: {request.get_status_display()}\n\n"

        await update.message.reply_text(text, parse_mode='Markdown')

    async def admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        telegram_user = await sync_to_async(TelegramUser.objects.get)(telegram_id=update.effective_user.id)
        
        if not telegram_user.is_admin:
            await update.message.reply_text(
                "❌ **Siz admin emassiz!**\n\n"
                "Bu buyruq faqat adminlar uchun.",
                parse_mode='Markdown'
            )
            return

        keyboard = [
            [InlineKeyboardButton("📊 So'rovlar", callback_data="admin_requests")],
            [InlineKeyboardButton("👥 Foydalanuvchilar", callback_data="admin_users")],
            [InlineKeyboardButton("🏢 Bo'limlar", callback_data="admin_departments")],
            [InlineKeyboardButton("📈 Statistika", callback_data="admin_stats")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "👑 **Admin paneli** 👑\n\n"
            "Kerakli bo'limni tanlang:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        data = query.data
        telegram_user = await sync_to_async(TelegramUser.objects.get)(telegram_id=update.effective_user.id)

        if data.startswith("select_dept_"):
            dept_id = data.split("_")[2]
            context.user_data['selected_department'] = dept_id
            await query.edit_message_text(
                "📝 **Uchrashuv nomini kiriting:**\n\n"
                "Masalan: 'Muhim majlis'",
                parse_mode='Markdown'
            )

        elif data == "admin_requests":
            pending_requests = await sync_to_async(BookingRequest.objects.filter)(status='pending').order_by('-created_at')[:10]
            
            if not pending_requests:
                await query.edit_message_text(
                    "📋 **Kutilayotgan so'rovlar yo'q**",
                    parse_mode='Markdown'
                )
                return

            text = "📋 **Kutilayotgan so'rovlar:**\n\n"
            keyboard = []
            
            for request in pending_requests:
                text += f"📝 {request.title}\n"
                text += f"👤 {request.requested_by.first_name}\n"
                text += f"🏢 {request.department.name}\n"
                text += f"🕐 {request.preferred_start_time.strftime('%Y-%m-%d %H:%M')}\n\n"
                
                keyboard.append([
                    InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"approve_req_{request.id}"),
                    InlineKeyboardButton("❌ Rad etish", callback_data=f"reject_req_{request.id}")
                ])

            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)

    async def text_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text
        telegram_user = await sync_to_async(TelegramUser.objects.get)(telegram_id=update.effective_user.id)

        if text == "📊 Profil":
            await self.profile_command(update, context)
        elif text == "📅 Uchrashuv yaratish":
            await self.book_command(update, context)
        elif text == "⏰ Jadval":
            await self.my_meetings_command(update, context)
        elif text == "📋 So'rovlar":
            await self.requests_command(update, context)
        elif text == "❓ Yordam":
            await self.help_command(update, context)
        elif text == "⬅️ Orqaga":
            await self.start_command(update, context)
        elif text == "👑 Admin panel" and telegram_user.is_admin:
            await self.admin_command(update, context)
        elif 'selected_department' in context.user_data:
            await self.handle_meeting_creation(update, context, text)

    async def handle_meeting_creation(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text):
        telegram_user = await sync_to_async(TelegramUser.objects.get)(telegram_id=update.effective_user.id)
        
        if 'meeting_title' not in context.user_data:
            context.user_data['meeting_title'] = text
            await update.message.reply_text(
                "⏰ **Boshlanish vaqtini kiriting:**\n\n"
                "Format: HH:MM (masalan: 14:30)",
                parse_mode='Markdown'
            )
        elif 'meeting_time' not in context.user_data:
            try:
                time_obj = datetime.strptime(text, '%H:%M').time()
                today = timezone.now().date()
                start_time = timezone.make_aware(datetime.combine(today, time_obj))
                
                if start_time <= timezone.now():
                    await update.message.reply_text(
                        "❌ **Vaqt noto'g'ri!**\n\n"
                        "Iltimos, kelajakdagi vaqtni kiriting.",
                        parse_mode='Markdown'
                    )
                    return

                context.user_data['meeting_time'] = start_time
                await update.message.reply_text(
                    "⏱️ **Davomiyligini kiriting (daqiqalarda):**\n\n"
                    "Masalan: 60",
                    parse_mode='Markdown'
                )
            except ValueError:
                await update.message.reply_text(
                    "❌ **Vaqt formati noto'g'ri!**\n\n"
                    "Iltimos, HH:MM formatida kiriting (masalan: 14:30)",
                    parse_mode='Markdown'
                )
        elif 'meeting_duration' not in context.user_data:
            try:
                duration = int(text)
                if duration <= 0 or duration > 480:  # Max 8 hours
                    await update.message.reply_text(
                        "❌ **Davomiylig noto'g'ri!**\n\n"
                        "Davomiylig 1 daqiqadan 480 daqiqagacha bo'lishi kerak.",
                        parse_mode='Markdown'
                    )
                    return

                context.user_data['meeting_duration'] = duration
                await update.message.reply_text(
                    "📝 **Tavsifini kiriting:**\n\n"
                    "Ixtiyoriy: Uchrashuv haqida qo'shimcha ma'lumot",
                    parse_mode='Markdown'
                )
            except ValueError:
                await update.message.reply_text(
                    "❌ **Davomiylig formati noto'g'ri!**\n\n"
                    "Iltimos, faqat son kiriting (masalan: 60)",
                    parse_mode='Markdown'
                )
        else:
            context.user_data['meeting_description'] = text
            await self.create_booking_request(update, context)

    async def create_booking_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        telegram_user = await sync_to_async(TelegramUser.objects.get)(telegram_id=update.effective_user.id)
        department_id = context.user_data.get('selected_department')
        meeting_title = context.user_data.get('meeting_title')
        meeting_time = context.user_data.get('meeting_time')
        meeting_duration = context.user_data.get('meeting_duration')
        meeting_description = context.user_data.get('meeting_description')

        try:
            department = await sync_to_async(Department.objects.get)(id=department_id)
            
            booking_request = await sync_to_async(BookingRequest.objects.create)(
                title=meeting_title,
                description=meeting_description,
                preferred_start_time=meeting_time,
                duration=meeting_duration,
                department=department,
                requested_by=telegram_user,
                status='pending'
            )

            # Clear user data
            del context.user_data['selected_department']
            del context.user_data['meeting_title']
            del context.user_data['meeting_time']
            del context.user_data['meeting_duration']
            del context.user_data['meeting_description']

            await update.message.reply_text(
                f"✅ **Uchrashuv muvaffaqiyatli yaratildi!**\n\n"
                f"📝 Nomi: {meeting_title}\n"
                f"🏢 Bo'lim: {department.name}\n"
                f"🕐 Vaqt: {meeting_time.strftime('%Y-%m-%d %H:%M')}\n"
                f"⏱️ Davomiyligi: {meeting_duration} daqiqa\n\n"
                f"Uchrashuv havolasi tez orada yuboriladi!",
                parse_mode='Markdown'
            )

        except Exception as e:
            await update.message.reply_text(
                "❌ **Xatolik yuz berdi!**\n\n"
                "Iltimos, qaytadan urinib ko'ring.",
                parse_mode='Markdown'
            )

    @sync_to_async
    def check_daily_limit(self, telegram_user):
        today = timezone.now().date()
        today_count = ZoomMeeting.objects.filter(
            created_by=telegram_user,
            start_time__date=today,
            is_active=True
        ).count()
        return today_count >= 5

    @sync_to_async
    def get_today_meeting_count(self, telegram_user):
        today = timezone.now().date()
        return ZoomMeeting.objects.filter(
            created_by=telegram_user,
            start_time__date=today,
            is_active=True
        ).count()

    def run(self):
        self.application.run_polling()
