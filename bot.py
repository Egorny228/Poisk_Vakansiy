import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import BOT_TOKEN
from database import init_db, add_user, remove_user, get_all_users, mark_vacancy_sent, is_vacancy_sent
from parser_hh import search_vacancies

# Настройка логирования
logging.basicConfig(level=logging.WARNING)

# Инициализация бота
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Инициализация БД
init_db()

# Состояния FSM
class Registration(StatesGroup):
    waiting_for_profession = State()
    waiting_for_city = State()
    waiting_for_salary = State()
    waiting_for_employment = State()  # ТИП ЗАНЯТОСТИ
    waiting_for_schedule = State()    # ГРАФИК РАБОТЫ
    waiting_for_experience = State()  # ОПЫТ РАБОТЫ

# Клавиатуры для фильтров
def get_employment_keyboard():
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Полная"), KeyboardButton(text="Частичная")],
            [KeyboardButton(text="Стажировка"), KeyboardButton(text="Любая")]
        ],
        resize_keyboard=True
    )
    return kb

def get_schedule_keyboard():
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Удалёнка"), KeyboardButton(text="Гибкий")],
            [KeyboardButton(text="Сменный"), KeyboardButton(text="Любой")]
        ],
        resize_keyboard=True
    )
    return kb

def get_experience_keyboard():
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Без опыта"), KeyboardButton(text="1-3 года")],
            [KeyboardButton(text="3-6 лет"), KeyboardButton(text="Любой")]
        ],
        resize_keyboard=True
    )
    return kb

# Команда /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await message.answer(
        "👋 Привет! Я буду присылать новые вакансии по твоим фильтрам.\n\n"
        "Давай настроим поиск.\n"
        "Введи профессию (например, 'повар', 'программист'):",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(Registration.waiting_for_profession)

# Шаг 1: Профессия
@dp.message(Registration.waiting_for_profession)
async def set_profession(message: types.Message, state: FSMContext):
    await state.update_data(profession=message.text)
    await message.answer(
        "Теперь введи город (например, 'Москва', 'Казань'):",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(Registration.waiting_for_city)

# Шаг 2: Город
@dp.message(Registration.waiting_for_city)
async def set_city(message: types.Message, state: FSMContext):
    await state.update_data(city=message.text)
    await message.answer(
        "Введите минимальную зарплату (только цифры) или 0, если не важно:",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(Registration.waiting_for_salary)

# Шаг 3: Зарплата
@dp.message(Registration.waiting_for_salary)
async def set_salary(message: types.Message, state: FSMContext):
    try:
        salary = int(message.text)
        if salary < 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введи число (например, 50000 или 0):")
        return
    
    await state.update_data(salary=salary)
    await message.answer(
        "Выбери тип занятости:",
        reply_markup=get_employment_keyboard()
    )
    await state.set_state(Registration.waiting_for_employment)

# Шаг 4: Тип занятости
@dp.message(Registration.waiting_for_employment)
async def set_employment(message: types.Message, state: FSMContext):
    employment_map = {
        "Полная": "full",
        "Частичная": "part",
        "Стажировка": "internship",
        "Любая": "any"
    }
    employment = employment_map.get(message.text, "any")
    await state.update_data(employment=employment)
    
    await message.answer(
        "Выбери график работы:",
        reply_markup=get_schedule_keyboard()
    )
    await state.set_state(Registration.waiting_for_schedule)

# Шаг 5: График работы
@dp.message(Registration.waiting_for_schedule)
async def set_schedule(message: types.Message, state: FSMContext):
    schedule_map = {
        "Удалёнка": "remote",
        "Гибкий": "flexible",
        "Сменный": "shift",
        "Любой": "any"
    }
    schedule = schedule_map.get(message.text, "any")
    await state.update_data(schedule=schedule)
    
    await message.answer(
        "Выбери требуемый опыт:",
        reply_markup=get_experience_keyboard()
    )
    await state.set_state(Registration.waiting_for_experience)

# Шаг 6: Опыт работы
@dp.message(Registration.waiting_for_experience)
async def set_experience(message: types.Message, state: FSMContext):
    experience_map = {
        "Без опыта": "noExperience",
        "1-3 года": "between1And3",
        "3-6 лет": "between3And6",
        "Любой": "any"
    }
    experience = experience_map.get(message.text, "any")
    await state.update_data(experience=experience)
    
    # Сохраняем всё в БД
    data = await state.get_data()
    profession = data['profession']
    city = data['city']
    salary = data['salary']
    
    # Сохраняем пользователя с фильтрами
    add_user(
        user_id=message.from_user.id,
        query=profession,
        city=city,
        salary_from=salary
    )
    
    # Показываем все настройки
    await message.answer(
        f"✅ Настройки сохранены!\n\n"
        f"🔍 Профессия: {profession}\n"
        f"📍 Город: {city}\n"
        f"💰 Зарплата от: {salary if salary > 0 else 'Не важно'}\n"
        f"💼 Тип занятости: {message.text}\n"
        f"🕐 График: {data.get('schedule', 'Любой')}\n"
        f"📈 Опыт: {message.text}\n\n"
        f"Я буду присылать тебе новые вакансии каждые 30 минут.\n"
        f"Чтобы отписаться, отправь /stop",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.clear()

# Команда /stop
@dp.message(Command("stop"))
async def cmd_stop(message: types.Message):
    remove_user(message.from_user.id)
    await message.answer("❌ Ты отписался от рассылки. Чтобы подписаться заново, отправь /start")

# Команда /check
@dp.message(Command("check"))
async def cmd_check(message: types.Message):
    await message.answer("🔍 Проверяю вакансии...")
    await check_vacancies_for_user(message.from_user.id)
    await message.answer("✅ Готово!")

# Проверка для одного пользователя
async def check_vacancies_for_user(user_id):
    users = get_all_users()
    for uid, query, city, salary in users:
        if uid != user_id:
            continue
        
        vacancies = search_vacancies(
            query=query,
            city=city,
            salary_from=salary
            # Фильтры пока не передаём, но можно добавить позже
        )
        
        for vac in vacancies:
            if not is_vacancy_sent(vac['id'], uid):
                text = (
                    f"🍳 <b>{vac['title']}</b>\n"
                    f"🏢 {vac['company']}\n"
                    f"💰 {vac['salary']}\n"
                    f"📝 {vac['description']}...\n"
                    f"🔗 <a href='{vac['url']}'>Смотреть вакансию</a>"
                )
                try:
                    await bot.send_message(uid, text, parse_mode="HTML")
                    mark_vacancy_sent(vac['id'], uid)
                    await asyncio.sleep(0.5)
                except Exception as e:
                    print(f"Ошибка отправки пользователю {uid}: {e}")

# Периодическая проверка
async def check_all_users():
    logging.info("Проверка новых вакансий...")
    users = get_all_users()
    
    for user_id, query, city, salary in users:
        try:
            vacancies = search_vacancies(
                query=query,
                city=city,
                salary_from=salary
            )
            
            for vac in vacancies:
                if not is_vacancy_sent(vac['id'], user_id):
                    text = (
                        f"🍳 <b>{vac['title']}</b>\n"
                        f"🏢 {vac['company']}\n"
                        f"💰 {vac['salary']}\n"
                        f"📝 {vac['description']}...\n"
                        f"🔗 <a href='{vac['url']}'>Смотреть вакансию</a>"
                    )
                    await bot.send_message(user_id, text, parse_mode="HTML")
                    mark_vacancy_sent(vac['id'], user_id)
                    await asyncio.sleep(0.5)
        except Exception as e:
            logging.error(f"Ошибка для {user_id}: {e}")

# Запуск
async def main():
    scheduler = AsyncIOScheduler(timezone='UTC')
    scheduler.add_job(check_all_users, 'interval', minutes=15)
    scheduler.start()
    logging.info("Бот запущен! Планировщик активен.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())