##
## Stores consts access JSON files more easily
##

# Config file
class Config():
    EMAIL = "email"
    PASSWORD = "password"
    THREAD_FBID = "thread_fbid"

# Command main fields
class Cmd():
    NAME = "cmd_name"
    SHORT = "cmd_short"
    IS_OPER = "is_oper"
    ENTRY_METHOD = "entry_method"
    ARGS = "args"
    TXT_EXECUTED = "txt_executed"
    TXT_ARGS_ERROR = "txt_error_arg"


COMMANDS = "commands"
OPER_FBID_LIST = "oper_fbid_list"

COMMAND_ERROR = "command_error"
COMMAND_ERROR_OPER = "command_error_oper"