class Event:
    def get_log_string(self): ...
    def get_verbose_log_string(self):
        return self.get_log_string()


class Query(Event):
    def __init__(self, cmd, admin_ids, chat_id, user_id):
        self.cmd = cmd
        self.admin_ids = admin_ids
        self.chat_id = chat_id
        self.user_id = user_id

    def get_log_string(self):
        template_string = "[{query}]: {chat_id} - {user_id}"
        return template_string.format(
            query=self.cmd, chat_id=self.chat_id, user_id=self.user_id
        )


class QueryWithPayload(Query):
    def __init__(self, cmd, admin_ids, chat_id, user_id, payload):
        super().__init__(cmd, admin_ids, chat_id, user_id)
        self.payload = payload


class QueryWithTarget(QueryWithPayload):
    def __init__(self, cmd, admin_ids, chat_id, user_id, payload, target_id):
        super().__init__(cmd, admin_ids, chat_id, user_id, payload)
        self.target_id = target_id

    def get_log_string(self):
        template_string = "[{query}]: {chat_id} - {user_id} - {target_id}"
        return template_string.format(
            query=self.cmd,
            chat_id=self.chat_id,
            user_id=self.user_id,
            target_id=self.target_id,
        )


class Response(Event):
    def __init__(self, chat_id, text, valid=False, parse_mode=None):
        self.chat_id = chat_id
        self.text = text
        self.is_valid = valid
        self.parse_mode = parse_mode

    def get_log_string(self):
        template_string = "[{response_type}]: {chat_id} - {parse_mode} - {text_head}"
        return template_string.format(
            response_type=self.response_type,
            chat_id=self.chat_id,
            parse_mode=self.parse_mode if self.parse_mode else "default",
            text_head=self.text.split("\n")[0],
        )

    @property
    def response_type(self):
        return "Response"


class ResponseWithAlert(Response):
    def __init__(
        self, chat_id, text, payload, valid, parse_mode=None, regenerate_keyboard=False
    ):
        super().__init__(chat_id, text, valid, parse_mode)
        self.payload = payload
        self.regenerate_keyboard = regenerate_keyboard

    @property
    def response_type(self):
        return "ResponseWithAlert"


class ResponseWithOptions(Response):
    def __init__(
        self, chat_id, text, candidates, valid=False, parse_mode=None, cmd=None
    ):
        super().__init__(chat_id, text, valid, parse_mode)
        self.candidates = candidates
        self.cmd = cmd

    @property
    def response_type(self):
        return "ResponseWithOptions"


class StartGameQuery(Query):
    def __init__(self, cmd, admin_ids, chat_id, user_id, chat_type):
        super().__init__(cmd, admin_ids, chat_id, user_id)
        self.chat_type = chat_type


class JoinGameQuery(QueryWithPayload):
    def __init__(self, cmd, admin_ids, chat_id, user_id, payload, username):
        super().__init__(cmd, admin_ids, chat_id, user_id, payload)
        self.username = username

    def get_log_string(self):
        template_string = "[{query}]: {chat_id} - {user_id} - {username} - {count}"
        return template_string.format(
            query=self.cmd,
            chat_id=self.chat_id,
            user_id=self.user_id,
            username=self.username,
            count=len(self.admin_ids),
        )


RunQuery = Query

TerminateQuery = Query

InfoQuery = Query

SpeechRelatedQuery = Query

NominateQuery = Query
CommitNominateQuery = QueryWithTarget

VoteQuery = Query
CommitVoteQuery = QueryWithTarget

BalanceQuery = Query
CommitBalanceQuery = QueryWithTarget

StartNightQuery = Query

SkipNightQuery = Query


class NightActionQuery(QueryWithPayload):
    def __init__(self, cmd, admin_ids, chat_id, user_id, payload, action, target):
        super().__init__(cmd, admin_ids, chat_id, user_id, payload)
        self.action = action
        self.target = target

    def get_log_string(self):
        template_string = "[{query}]: {chat_id} - {action}"
        return template_string.format(
            query=self.cmd, chat_id=self.chat_id, action=self.action
        )

    def get_verbose_log_string(self):
        template_string = "[{query}]: {chat_id} - {user_id} - {target_id} - {action}"
        return template_string.format(
            query=self.cmd,
            chat_id=self.chat_id,
            user_id=self.user_id,
            target_id=self.target,
            action=self.action,
        )


class MafiaChatQuery(Query):
    def __init__(self, cmd, admin_ids, chat_id, user_id, text):
        super().__init__(cmd, admin_ids, chat_id, user_id)
        self.text = text

    def get_log_string(self):
        template_string = "[{query}]: {chat_id} - {text_head}"
        return template_string.format(
            query=self.cmd, chat_id=self.chat_id, text_head=self.text.split("\n")[0]
        )

    def get_verbose_log_string(self):
        template_string = "[{query}]: {chat_id} - {user_id} - {text}"
        return template_string.format(
            query=self.cmd,
            chat_id=self.chat_id,
            user_id=self.user_id,
            text=self.text,
        )
