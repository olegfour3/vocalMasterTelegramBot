import datetime
import config
from model import User, Notification
from aiogram import types
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.dispatcher import FSMContext
import bot as telegram_bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler


user_types = ("confirmed", "request", "blocked")
user_list_message = ["Держи этих замечательных людей:", "Запросы на всупление в наш клан:", "Непонятные человеки:"]
scheduler = AsyncIOScheduler()


async def send_message(chat_id: int, text: str):
    await telegram_bot.bot.send_message(chat_id=chat_id, text=text, parse_mode=types.ParseMode.HTML)


async def send_user_notifications():
    now_date = datetime.datetime.now()
    config.logger.info(f'Рассылка работает {now_date}')
    max_date = now_date.combine(now_date.date(), now_date.max.time())
    notifications = Notification.select().where(Notification.notification_date <= max_date,
                                                Notification.canceled == False, Notification.performed == False)
    for notification in notifications:
        if notification.user.blocked or not notification.user.confirmed:
            notification.canceled = True
            notification.save()
            continue
        try:
            await send_message(chat_id=str(notification.user.telegram_id),
                               text=f"Эт снова я! 🤛\n"
                               f"Спешу уведомить, что осталось занятий <b><u>{notification.user.lessons_quant}</u></b>\n"
                               f"Это значит, что настало время подношений нашей богине 🍪")
            notification.performed = True
            notification.save()
        except Exception as _ex:
            config.logger.info(f'Ошибка работы рассылки: {_ex}')


def create_notification_tasks():
    scheduler.add_job(send_user_notifications, 'cron', hour=config.NOTIFICATION_HOUR, minute=config.NOTIFICATION_MINUTE)
    scheduler.start()


def its_admin(telegram_id: str | int) -> bool:
    if config.ADMIN_ID == str(telegram_id):
        return True
    else:
        return False


def get_main_keyboard() -> types.ReplyKeyboardMarkup:
    confirmed_users_count = get_users_by_type(user_types[0]).count()
    user_requests_count = get_users_by_type(user_types[1]).count()
    blocked_users_count = get_users_by_type(user_types[2]).count()

    bnt_confirmed = KeyboardButton(f'😸 Мои котики ({confirmed_users_count})')
    bnt_requests = KeyboardButton(f'🛄 Запросы ({user_requests_count})')
    bnt_blocked = KeyboardButton(f'😐 Заблокированные ({blocked_users_count})')
    bnt_menu_upd = KeyboardButton('🆙')
    bnt_menu_hide = KeyboardButton('❌')
    main_menu = ReplyKeyboardMarkup(resize_keyboard=True).add(bnt_confirmed)
    main_menu.row(bnt_requests)
    main_menu.row(bnt_blocked)
    main_menu.row(bnt_menu_upd, bnt_menu_hide)
    return main_menu


def get_keyboard_of_users(users: [User], user_type: str) -> types.InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup(row_width=2)
    btns = [InlineKeyboardButton(text=user.name, callback_data=f"user_{user_type}_menu_{user.id}") for user in users]
    markup.add(*btns)
    return markup


def get_keyboard_of_user(user: User, user_type: str) -> types.InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup(row_width=1)

    btns_type = {
        'setName': 'Переименовать'
    }

    match user_types.index(user_type):
        case 0:
            btns_type["addLess"] = "Добавить занятие"
            btns_type["delLess"] = "Списать занятие"
        case 1 | 2:
            btns_type["confirm"] = "Подтвердить"

    btns_type["block"] = "Заблокировать" if not user.blocked else "Разблокировать"
    btns_type["back"] = "<< Назад"

    btns = [InlineKeyboardButton(text=btns_type[key],
                                 callback_data=f"user_{user_type}_{key}_{user.id}") for key in btns_type]
    markup.add(*btns)
    return markup


async def command_start(message: types.Message):
    if its_admin(message.from_user.id):
        await get_main_menu(message=message, text="Добро пожаловать, Незабвенная! 🌹")
        return

    user, created = User.get_or_create(telegram_id=message.from_user.id,
                                       defaults={'telegram_id': message.from_user.id,
                                                 'name': message.from_user.full_name})
    if created:
        await message.answer("Приятно познакомиться! Ждем одобрения высших сил")
        await send_message(chat_id=config.ADMIN_ID,
                               text=f'Новая заявка на вступление от <a href="tg://user?id={user.telegram_id}">{user.name}</a>\n')
        return

    match (user.confirmed, user.blocked):
        case False, False: await message.answer("Все еще ждем одобрения высших сил..")
        case False, True: await message.answer("Приятно было пообщаться, но все имеет дурацкое свойство заканчиваться.")
        case True, False: await message.answer("Все же хорошо, че бузишь?")
        case _: await message.answer("Ты кто ваще такой?7?")


async def get_main_menu(message: types.Message, text: str = ''):
    if text == '':
        text = 'Обновлена'
    await message.answer(text=text, reply_markup=get_main_keyboard())


def get_users_by_type(user_type: str):
    match user_types.index(user_type):
        case 0:
            return User.select().where(User.confirmed == True, User.blocked == False)
        case 1:
            return User.select().where(User.confirmed == False, User.blocked == False)
        case 2:
            return User.select().where(User.confirmed == False, User.blocked == True)


def check_user_type(user: User, user_type: str) -> bool:
    # проверяет пользователя на вхождение в список, в котором он должен находится по коллбэку
    if user_type not in user_types:
        return False

    match user_types.index(user_type):
        case 0:
            return user.confirmed and not user.blocked
        case 1:
            return not user.confirmed and not user.blocked
        case 2:
            return not user.confirmed and user.blocked


def get_user_type(user: User) -> bool:
    match user.confirmed, user.blocked:
        case True, False:
            return 0
        case False, False:
            return 1
        case False, True:
            return 2


async def get_users(message: types.Message, user_type: str):
    answer_text = user_list_message[user_types.index(user_type)]

    users = get_users_by_type(user_type=user_type)

    if users is None:
        await message.answer("Незвестная команда -_-")
        return

    if users.count() > 0:
        await message.answer(answer_text, reply_markup=get_keyboard_of_users(users=users, user_type=user_type))
    else:
        await message.answer("Пока пользователей нет :с")


def get_user_info(user: User, user_type: str) -> str:
    user_info = f'<b><u>{user.name}</u></b>\n\nID телеграм: <a href="tg://user?id={user.telegram_id}">{user.telegram_id}</a>\n'
    match user_types.index(user_type):
        case 0:
            user_info += f'Осталось занятий: {user.lessons_quant}\n' \
                         f'Дата запроса: {user.request_date.strftime("%d-%m-%Y")}'
        case 1:
            user_info += f'Дата запроса: {user.request_date.strftime("%d-%m-%Y")}'
        case 2:
            user_info += f'Дата запроса: {user.request_date.strftime("%d-%m-%Y")}\n' \
                         f'Дата блокировки: {user.block_date.strftime("%d-%m-%Y")}'

    return user_info


async def user_callback(call: types.callback_query, state: FSMContext):
    its_user, user_type, action, user_id = call.data.split('_')

    user = User.get_by_id(int(user_id))

    if user is None:
        try:
            await call.message.edit_text(text=user_list_message[user_types.index(user_type)],
                                         reply_markup=get_keyboard_of_users(users=get_users_by_type(user_type=user_type),
                                                                            user_type=user_type))
        except:
            pass
        await call.answer(f"Пользователя больше нет в базе :c")
        return None
    elif not check_user_type(user=user, user_type=user_type):
        try:
            await call.message.edit_text(text=user_list_message[user_types.index(user_type)],
                                         reply_markup=get_keyboard_of_users(users=get_users_by_type(user_type=user_type),
                                                                            user_type=user_type))
        except:
            pass
        await call.answer(f"Пользователь <b><u>{user.name}</u></b> уже в другом списке")
        return user_id

    match action:
        case 'back':
            await call.message.edit_text(text=user_list_message[user_types.index(user_type)],
                                         reply_markup=get_keyboard_of_users(users=get_users_by_type(user_type=user_type),
                                                                            user_type=user_type))

        case 'menu':
            await call.message.edit_text(get_user_info(user=user, user_type=user_type),
                                         reply_markup=get_keyboard_of_user(user=user, user_type=user_type))

        case 'addLess':
            user.lessons_quant += 1
            user.save()

            await call.message.edit_text(text=get_user_info(user=user, user_type=user_type),
                                         reply_markup=get_keyboard_of_user(user=user, user_type=user_type))

        case 'delLess':
            if user.lessons_quant >= 1:
                user.lessons_quant -= 1
                user.save()
                if user.lessons_quant == 1:
                    await call.message.edit_text(text=f"У <b><u>{user.name}</u></b> осталось последнее занятие. На какое число создать уведомление?",
                                                 reply_markup=get_notification_keyboard(user=user))
                    return
            else:
                await call.answer('Не осталось занятий')
            try:
                await call.message.edit_text(get_user_info(user=user, user_type=user_type),
                                             reply_markup=get_keyboard_of_user(user=user, user_type=user_type))
            except:
                pass

        case 'block':
            user.lessons_quant = 0
            user.block_date = datetime.datetime.now()
            user.blocked = not user.blocked
            user.confirmed = False
            user.save()
            await call.message.edit_text(user_list_message[user_types.index(user_type)])
            await call.message.edit_reply_markup(get_keyboard_of_users(users=get_users_by_type(user_type=user_type),
                                                                       user_type=user_type))
            await call.message.answer(f'Пользователь <b><u>{user.name}</u></b> {"заблокирован" if user.blocked else "разблокирован"}')
            if user.blocked:
                await telegram_bot.bot.send_message(chat_id=user.telegram_id, text=f'Оказалось, что нам не по пути..')

        case 'confirm':
            user.blocked = False
            user.confirmed = True
            user.save()

            await call.message.answer(f'Пользователь <b><u>{user.name}</u></b> принят в нашу банду')
            await telegram_bot.bot.send_message(chat_id=user.telegram_id, text=f'Добро пожаловать в нашу банду!')

        case 'setName':
            await telegram_bot.UserStates.user_setName.set()
            await call.message.answer(f'Отправь новое имя для пользователя {user.name}\n\n'
                                      f'Для отмены отправь "Отметить" или /c', reply_markup=types.ReplyKeyboardRemove)

    await call.answer()
    return user_id


async def user_set_name(message: types.Message, user_id: str):
    user = User.get_by_id(int(user_id))

    if user is None:
        await message.reply(text="Что-то пошло не так")
        return

    user.name = message.text
    user.save()
    await message.reply('Имя пользователя изменено')


def get_notification_keyboard(user: User) -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup(row_width=1)
    i = 1
    now = datetime.datetime.now()
    btns = [InlineKeyboardButton(text=f'{(now + datetime.timedelta(days=i+1)).strftime("%a --- %d-%m-%Y")}',
                                 callback_data=f"notif_create_{user.id}_{i}") for i in range(7)]

    markup.add(*btns)
    markup.add(InlineKeyboardButton(text="Не создавать", callback_data=f"notif_cancel_{user.id}_0"))
    return markup


async def notification_callback(call: types.callback_query):
    its_notification, action, user_id, days = call.data.split('_')

    user = User.get_by_id(int(user_id))

    if user is None:
        await call.message.edit_text(text='<b><u>Пользователья больше нет в базе :c', reply_markup=types.ReplyKeyboardRemove())
        return
    elif get_user_type(user=user) != 0:
        await call.message.edit_text(text=f'Для <b><u>{user.name}</u></b> больше не понадобятся уведомления -_-', reply_markup=types.ReplyKeyboardRemove())
        return

    if action == 'cancel' :
        await call.answer('Создание уведомления отменено')
        await call.message.edit_text(get_user_info(user=user, user_type=user_types[0]),
                                     reply_markup=get_keyboard_of_user(user=user, user_type=user_types[0]))
    elif action == 'create':
        notif_date = datetime.datetime.now() + datetime.timedelta(days=int(days))
        notif = Notification(user=user, notification_date=notif_date)
        # notif = Notification(user=user, notification_date=datetime.datetime.now())
        notif.save()
        await call.answer(text=f'Для {user.name} создано уведомление на {notif_date.strftime("%d-%m-%Y (%a)")}')
        await call.message.edit_text(get_user_info(user=user, user_type=user_types[0]),
                                     reply_markup=get_keyboard_of_user(user=user, user_type=user_types[0]))
        await call.message.answer(text=f'Для <b><u>{user.name}</u></b> создано уведомление на {notif_date.strftime("%d-%m-%Y (%a)")}')



