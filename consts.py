##
## Stores consts access JSON files more easily
##

# Config file
class Config():
    EMAIL = "email"
    PASSWORD = "password"
    THREAD_FBID = "thread_fbid"
    USERS = "users"

# Command main fields
class Cmd():
    NAME = "cmd_name"
    SHORT = "cmd_short"
    INFO = "info"
    IS_OPER = "is_oper"
    ENTRY_METHOD = "entry_method"
    ARGS = "args"
    TXT_EXECUTED = "txt_executed"
    TXT_FORMAT = "txt_format"
    TXT_ARGS_ERROR = "txt_error_arg"

# User fields
class User():
    ID = "id"
    NAME = "name"
    FULL_NAME = "full_name"
    GENDER = "gender"
    THUMB_SRC = "thumb_src"
    URL = "url"
    NICKNAMES = "nicknames"
    IN_CHAT = "in_chat"
    IS_FRIEND = "is_friend"
    ADDRESSING_NAMES = "addressing_names"


COMMANDS = "commands"
OPER_FBID_LIST = "oper_fbid_list"

COMMAND_ERROR = "command_error"
COMMAND_ERROR_OPER = "command_error_oper"