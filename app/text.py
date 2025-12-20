from loader import _


class MessageText:
    @property
    def WELCOME(self):
        return _(
            "👋, <a href='tg://user?id={}'>{}</a>\nПривіт, це бот який відправляє актуальний розклад відключення світла в Київській області."
        )

    @property
    def INFO(self):
        return _("Bot Info:")

    @property
    def INVITE_FRIENDS(self):
        return _("Invited users: <b>{}</b>\n\nLink for friends:\n<code>{}</code>")

    @property
    def CHANGE_LANG(self):
        return _("Select the language you want to switch to: 🌐")

    @property
    def DONE_CHANGE_LANG(self):
        return _("Your language has been successfully changed! ✅")

    @property
    def ADMIN_WELCOME(self):
        return _("You're the administrator!")

    @property
    def LOG_SENDING(self):
        return _("Logs sending...")

    @property
    def UNKNOWN_COMMAND(self):
        return _("Unknown command. If you are lost, type /start.")


message_text = MessageText()
