import os
import django
import random
import uuid
from django.utils import timezone
from asgiref.sync import sync_to_async
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.utils.executor import start_polling
from aiogram.contrib.fsm_storage.memory import MemoryStorage



os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from users.models import CustomUser, VerificationCode

API_TOKEN = ''

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    button = KeyboardButton('Send Contact', request_contact=True)
    markup = ReplyKeyboardMarkup(resize_keyboard=True).add(button)
    await message.reply("Please share your contact to proceed.", reply_markup=markup)

@dp.message_handler(content_types=[types.ContentType.CONTACT])
async def contact(message: types.Message):
    if message.contact:
        phone_number = message.contact.phone_number

        user, created = await sync_to_async(CustomUser.objects.get_or_create)(
            phone_number=phone_number,
            defaults={
                'telegram_username': message.from_user.username,
                'telegram_profile_photo': None
            }
        )

        if created or not user.has_usable_password():
            user.set_password(str(uuid.uuid4()))
            await sync_to_async(user.save)()

        photos = await bot.get_user_profile_photos(message.from_user.id)

        if photos.total_count > 0:
            photo_file_id = photos.photos[0][0].file_id

            file_info = await bot.get_file(photo_file_id)
            file_path = file_info.file_path
            file_url = f'https://api.telegram.org/file/bot{API_TOKEN}/{file_path}'

            user.telegram_profile_photo = file_url
            await sync_to_async(user.save)()

        code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        await sync_to_async(VerificationCode.objects.create)(user=user, code=code)
        await message.reply(f"Your verification code is: {code}. It is valid for 1 minute.")

if __name__ == '__main__':
    start_polling(dp, skip_updates=True)
