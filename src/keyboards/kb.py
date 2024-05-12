from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


def make_row_keyboard(items: list[str]) -> ReplyKeyboardMarkup:
    """
    Создаёт реплай-клавиатуру с кнопками в один ряд
    :param items: список текстов для кнопок
    :return: объект реплай-клавиатуры
    """
    row = [KeyboardButton(text=item) for item in items]
    return ReplyKeyboardMarkup(keyboard=[row], one_time_keyboard=True, resize_keyboard=True)

def make_inline_keyboard(items: list[str], cb_text:str) -> InlineKeyboardMarkup:
    for item in items:
        button = InlineKeyboardButton(item, callback_data=cb_text)
    return InlineKeyboardMarkup().add(buttons)

# async def number_buttons(n: int) -> ReplyKeyboardMarkup:
#     nums = [i for i in range(1,n+1)]
#     row = [[KeyboardButton(text=num)] for row in range(1,5) for num in nums for ]
#     return markup
    
