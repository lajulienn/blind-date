import config
import shelve
import telebot

bot = telebot.TeleBot(config.token)

# opened_dialogues = shelve.open(config.opened_dialogues_db)
# closed_dialogues = shelve.open(config.closed_dialogues_db)
opened_dialogues = {}
closed_dialogues = {}
waiting_queue = []

# with shelve.open(config.users_db) as users:


@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, 'Finding a partner for you...')
    if message.chat.id in opened_dialogues or (len(waiting_queue) != 0 and id == waiting_queue[0]):
        return

    # user = message.from_user.username
    # if user not in users:
    #     users[message.chat.id] = (user, False)  # id -> (username, revealed)

    def is_smb_available(id):
        return len(waiting_queue) != 0 and (id not in closed_dialogues
                                           or closed_dialogues.get(id) != waiting_queue[0])

    if not is_smb_available(message.chat.id):
        waiting_queue.append(message.chat.id)
    else:
        first = message.chat.id
        second = waiting_queue.pop(0)
        opened_dialogues[first] = second
        opened_dialogues[second] = first
        if first in closed_dialogues:
            del closed_dialogues[first]
        if second in closed_dialogues:
            del closed_dialogues[second]
        bot.send_message(first, 'Start talking!')
        bot.send_message(second, 'Start talking!')


@bot.message_handler(commands=['help'])
def send_help(message):
    bot.send_message(message.chat.id, 'Help')


@bot.message_handler(content_types=['text'])
def reply(message):
    bot.send_message(opened_dialogues[message.chat.id], message.text)


# receiving new messages
bot.polling()

# opened_dialogues.close()
# closed_dialogues.close()
