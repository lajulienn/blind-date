import config
import shelve
import telebot
import logging

logging.basicConfig(format=u'%(levelname)-8s [%(asctime)s] %(message)s',
                    level=logging.DEBUG,
                    filename=u'mylog.log')

bot = telebot.TeleBot(config.token)

opened_dialogues = {}
closed_dialogues = {}
waiting_queue = []

with shelve.open(config.users_db) as users:

    def is_started(user_id):
        return user_id in opened_dialogues \
               or (len(waiting_queue) != 0 and user_id == waiting_queue[0])


    def is_smb_available(user_id):
        return len(waiting_queue) != 0 \
               and (user_id not in closed_dialogues
                    or closed_dialogues.get(user_id) != waiting_queue[0])


    def remove_from_list(first, second, list):
        if first in list:
            del list[first]
        if second in list:
            del list[second]

    def add_to_list(first, second, list):
        list[first] = second
        list[second] = first

    def add_new_user(user_id, username):
        users[str(user_id)] = config.UserProperties(username, False)

    @bot.message_handler(commands=['start'])
    def start(message):
        logging.debug('\start command was received from user {}'
                      .format(message.chat.id))
        user_id = message.chat.id
        if is_started(user_id):
            logging.warning('\start command was received for the second time')
            return

        bot.send_message(user_id, 'Finding a partner for you...')
        logging.debug('Started partner finding')

        username = message.from_user.username
        add_new_user(user_id, username)

        if not is_smb_available(user_id):
            waiting_queue.append(user_id)
            logging.debug('Add new user to waiting queue')
        else:
            first = user_id
            second = waiting_queue.pop(0)
            add_to_list(first, second, list=opened_dialogues)
            remove_from_list(first, second, list=closed_dialogues)
            bot.send_message(first, 'Start talking!')
            bot.send_message(second, 'Start talking!')
            logging.debug('Conversation started between users: {} and {}'
                          .format(first, second))


    @bot.message_handler(commands=['help'])
    def send_help(message):
        logging.debug('\help command was received from user {}'
                      .format(message.chat.id))
        bot.send_message(
            message.chat.id,
            'Send "/start" to start a conversation.\n'
            'Send "/leave" to close a conversation.\n'
            'Send "/change_room" to change your partner.\n'
            'Send "/reveal" to allow bot to show your username to your partner. '
            'It would be shown only provided that '
            'your partner also sent a reveal command\n')


    @bot.message_handler(commands=['leave'])
    def leave(message):
        logging.debug('\leave command was received from user {}'
                      .format(message.chat.id))
        first = message.chat.id
        if first in waiting_queue:
            waiting_queue.remove(first)
            logging.debug('Removed user {} from the waiting queue'
                          .format(first))
        if first not in opened_dialogues:
            logging.warning('User {} was not in the opened dialogues'
                            .format(message.chat.id))
            return
        second = opened_dialogues[first]
        remove_from_list(first, second, list=opened_dialogues)
        add_to_list(first, second, list=closed_dialogues)
        bot.send_message(second, 'Your partner left the chat. :(\n'
                                 'Send "/start" to open a new conversation.')
        logging.debug('Closed dialogue between users: {} and {}'
                      .format(first, second))


    @bot.message_handler(commands=['change_room'])
    def change_room(message):
        logging.debug('\change_room command was received from user {}'
                      .format(message.chat.id))
        user_id = message.chat.id
        if user_id in waiting_queue:
            logging.error('User {} can not change room, '
                          'he is only in the waiting queue'
                          .format(message.chat.id))
            return
        leave(message)
        start(message)
        logging.debug('Changed room for user {}'.format(message.chat.id))


    @bot.message_handler(commands=['reveal'])
    def reveal(message):
        logging.debug(u'\reveal command was received from user {}'
                      .format(message.chat.id))
        first = message.chat.id
        if first in waiting_queue:
            bot.send_message(first, 'Your chat has not started yet.')
            logging.warning('Chat with user {} was not started yet'
                            .format(first))
            return
        if first not in opened_dialogues:
            bot.send_message(first, 'Start a conversation first.')
            logging.warning('Chat with user {} was not started yet'
                            .format(first))
            return

        second = opened_dialogues[first]
        first_username = users[str(first)].username

        if first_username is None:
            bot.send_message(first, 'Please, set username first.')
            logging.warning('Username of user {} was not set yet'
                            .format(first))
            return

        if users[str(second)].revealed:
            second_username = users[str(second)].username
            bot.send_message(
                first,
                'User @{} revealed his username.'.format(second_username))
            bot.send_message(
                second,
                'User @{} revealed his username.'.format(first_username))
            logging.debug('Revealed users {} and {} to each other'
                          .format(first, second))
        else:
            users[str(first)] = config.UserProperties(first_username, True)
            logging.debug('Set users {} "revealed"=True'.format(first))


    @bot.message_handler(content_types=['text'])
    def reply(message):
        logging.debug('Text message was received from user {}'
                      .format(message.chat.id))
        user_id = message.chat.id
        if user_id in opened_dialogues:
            partner = opened_dialogues[user_id]
            bot.send_message(partner,
                             message.text)
            logging.debug('Send a text message from {} to {}'
                          .format(user_id, partner))


    @bot.message_handler(content_types=['audio'])
    def reply(message):
        logging.debug('Audio message was received from user {}'
                      .format(message.chat.id))
        user_id = message.chat.id
        if user_id in opened_dialogues:
            partner = opened_dialogues[user_id]
            bot.send_audio(partner,
                           message.audio.file_id)
            logging.debug('Send an audio message from {} to {}'
                          .format(user_id, partner))


    @bot.message_handler(content_types=['sticker'])
    def sticker(message):
        logging.debug('Sticker was received from user {}'
                      .format(message.chat.id))
        user_id = message.chat.id
        if user_id in opened_dialogues:
            partner = opened_dialogues[user_id]
            bot.send_sticker(partner,
                             message.sticker.file_id)
            logging.debug('Send a sticker from {} to {}'
                          .format(user_id, partner))


    @bot.message_handler(content_types=['voice'])
    def sticker(message):
        logging.debug('Voice was received from user {}'
                      .format(message.chat.id))
        user_id = message.chat.id
        if user_id in opened_dialogues:
            partner = opened_dialogues[user_id]
            bot.send_voice(partner,
                           message.voice.file_id)
            logging.debug('Send a voice from {} to {}'
                          .format(user_id, partner))


    @bot.message_handler(content_types=['document'])
    def sticker(message):
        logging.debug('Document was received from user {}'
                      .format(message.chat.id))
        user_id = message.chat.id
        if user_id in opened_dialogues:
            partner = opened_dialogues[user_id]
            bot.send_document(partner,
                              message.document.file_id)
            logging.debug('Send a document from {} to {}'
                          .format(user_id, partner))


    @bot.message_handler(content_types=['photo'])
    def sticker(message):
        logging.debug('Photo was received from user {}'
                      .format(message.chat.id))
        user_id = message.chat.id
        if user_id in opened_dialogues:
            partner = opened_dialogues[user_id]
            bot.send_photo(partner,
                           message.photo[len(message.photo)-1].file_id)
            logging.debug('Send a photo from {} to {}'
                          .format(user_id, partner))


    @bot.message_handler(content_types=['video'])
    def sticker(message):
        logging.debug('Video was received from user {}'
                      .format(message.chat.id))
        user_id = message.chat.id
        if user_id in opened_dialogues:
            partner = opened_dialogues[user_id]
            bot.send_video(partner,
                           message.video.file_id)
            logging.debug('Send a video from {} to {}'
                          .format(user_id, partner))


    @bot.message_handler(content_types=['location'])
    def sticker(message):
        logging.debug('Location was received from user {}'
                      .format(message.chat.id))
        user_id = message.chat.id
        if user_id in opened_dialogues:
            partner = opened_dialogues[user_id]
            bot.send_location(partner,
                              message.location.latitude,
                              message.location.longitude)
            logging.debug('Send a location from {} to {}'
                          .format(user_id, partner))

    bot.polling()
