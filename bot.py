from config import TOKEN, logger
import services
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters import Text
from aiogram.utils import executor
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup


class UserStates(StatesGroup):
    user_setName = State()


bot = Bot(token=TOKEN, parse_mode=types.ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


def launch_bot():
    try:
        services.create_notification_tasks()
        executor.start_polling(dp, skip_updates=True)
    except Exception as _ex:
        logger.error(f'Telegram bot startup error:\n{_ex}')


if __name__ == '__main__':
    launch_bot()


@dp.message_handler(lambda message: services.its_admin(message.from_user.id) is False)
async def cmd_start(message: types.Message):
    await services.command_start(message)


@dp.message_handler(commands='start')
async def cmd_start(message: types.Message):
    await services.command_start(message)


@dp.message_handler(commands='m')
@dp.message_handler(Text(startswith='🆙'))
async def cmd_menu(message: types.Message):
    await services.get_main_menu(message)


@dp.message_handler(commands='h')
@dp.message_handler(Text(startswith='❌'))
async def hide_menu(message: types.Message):
    await message.reply(text="Спрятано", reply_markup=types.ReplyKeyboardRemove())


@dp.message_handler(Text(startswith='😸 Мои котики'))
async def del_user(message: types.Message):
    await services.get_users(message=message, user_type=services.user_types[0])


@dp.message_handler(Text(startswith='🛄 Запросы'))
async def del_user(message: types.Message):
    await services.get_users(message=message, user_type=services.user_types[1])


@dp.message_handler(Text(startswith='😐 Заблокированные'))
async def del_user(message: types.Message):
    await services.get_users(message=message, user_type=services.user_types[2])


@dp.callback_query_handler(lambda c: c.data.startswith('user_'))
async def callback_user(call: types.callback_query, state: FSMContext):
    async with state.proxy() as data:
        data['user_id'] = await services.user_callback(call=call, state=state)
        data['message'] = call.message


@dp.message_handler(state='*', commands='c')
@dp.message_handler(Text(equals='Отмена', ignore_case=True), state='*')
async def cancel_handler(message: types.Message, state: FSMContext):
    """
    Allow user to cancel any action
    """
    # Cancel state and inform user about it
    await state.finish()
    # And remove keyboard (just in case)
    await message.reply('Отменено.')


@dp.message_handler(state=UserStates.user_setName)
async def user_set_mame(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        await services.user_set_name(message=message, user_id=data['user_id'])
        await state.finish()


@dp.callback_query_handler(lambda c: c.data.startswith('notif_'))
async def callback_user(call: types.callback_query):
    await services.notification_callback(call=call)
