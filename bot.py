import config
import shelve
import telebot

bot = telebot.TeleBot(config.token)

opened_dialogues = {}
closed_dialogues = {}
waiting_queue = []

with shelve.open(config.users_db) as users:

    def is_opened(user_id):
        return user_id in opened_dialogues \
               or (len(waiting_queue) != 0 and user_id == waiting_queue[0])


    def is_smb_available(user_id):
        return len(waiting_queue) != 0 and (user_id not in closed_dialogues
                                            or closed_dialogues.get(user_id) != waiting_queue[0])


    def remove_from_closed(first, second):
        if first in closed_dialogues:
            del closed_dialogues[first]
        if second in closed_dialogues:
            del closed_dialogues[second]


    def add_new_user(user_id, username):
        users[str(user_id)] = config.UserProperties(username, False)

    @bot.message_handler(commands=['start'])
    def start(message):
        user_id = message.chat.id
        bot.send_message(user_id, 'Finding a partner for you...')

        if is_opened(user_id):
            return

        username = message.from_user.username
        add_new_user(user_id, username)

        if not is_smb_available(user_id):
            waiting_queue.append(user_id)
        else:
            first = user_id
            second = waiting_queue.pop(0)
            opened_dialogues[first] = second
            opened_dialogues[second] = first
            remove_from_closed(first, second)
            bot.send_message(first, 'Start talking!')
            bot.send_message(second, 'Start talking!')


    @bot.message_handler(commands=['help'])
    def send_help(message):
        bot.send_message(message.chat.id,
                         'Send "/start" to start a conversation.\n'
                         'Send "/leave" to close a conversation.\n'
                         'Send "/change_room" to change your partner.\n'
                         'Send "/reveal" to allow bot to show your username to your partner. '
                         'It would be shown only provided that '
                         'your partner also sent a reveal command\n')


    @bot.message_handler(lambda: True)
    def reply(message):
        bot.send_message(opened_dialogues[message.chat.id], message.text)


    bot.polling()
