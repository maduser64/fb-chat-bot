# FB Chat Bot
Everyone who has used IRC or Twitch or Discord knows about group bots. They're pretty cool. I wanted one for my group chat. I also wanted to learn at least a little bit of Python, see what's the hype about. And, well, here it is - a Python FB Chat Bot.

![Here bot is in action](https://i.imgur.com/xqBM4Ks.png)

Currently available commands:
* `!addnickname [new_nickname]` - add a nickname to how bot calls you
* `!addressingname [new_addressing_name]` - add a name to how bot addresses you
* `!aesthetic [text]` - converts text to aesthetic (full-width) text
* `!annoy [name] [count] [text]` - writes a message immediately after the person writes a message
* `!help` - shows help
* `!on` - shows if bot is online right now and for how long
* `!onseen [name] [text]` - writes a message to person, when he opens up chat
* `!roll` - rolls a number for given max value (inclusive)
* `!roll1` - another type of roll
* `!say [text]` - bot repeats what you say
* `!stats` - displays chat stats
* `!time` - shows current time and date
* `!urban [query]` - shows Urban Dictionary definition
* `!quiz (!q) query/more/mystats/allstats` - a fun trivia game
* `!weather` - shows weather
* `!wiki [query]` - shows Wikipedia article extract

Then there are admin commands:
* `!addsimplecommand [cmd_name] [returned string]` - adds a command, which only returns a prewritten string
* `!savestats` - forces bot to save current stats
* `!updateconfig` - forces bot to update fields from config file
* `!saveuserlist` - saves people currently in the chat

## Making config file
1. Enter the email and password of the account the bot will be running on.
2. Enter `thread_id` you see in your address bar when that chat is opened, e.g. 13285268271687201
3. Give your bot a name and enter the quiz file to read for questions (more on that later).
4. To give yourself operator commands, enter your FB ID in `oper_fbid_list`.
5. Enter what bot says when he logs in, when somebody writes non-existing command and when somebody tries to access OP command.


## How to use
1. Start `fb_chat_bot.py`.
2. With people in the chat write `!saveuserlist`
3. ???
4. Profit.

## Adding new commands
This thing I made actually quite easy. Let's say you want to make a new command, which returns a price for a spefic item from amazon. You'd have to enter this into `commands` in `config.json` file:

		"amazon_price_check": {
			"cmd_name": "!amazon",
			"cmd_short": "!a",
			"info": "shows price for this item from Amazon",
			"info_args": {},
			"entry_method": "cmd_amazon_price",
			"is_oper": false,
			"txt_executed": "Price of %s is %s€."
		}
    
After this, create a method in `fb_chat_bot.py`:

    def cmd_amazon_price(self, author_id, command, args):
        """Gets price of an item from Amazon"""
        try:
            if args == "": raise Exception
            # Some logic
            self.command_log(command[consts.Cmd.NAME], args)
            self.group_send(command[consts.Cmd.TXT_EXECUTED] % (args, price))
        except:
            self.command_log_error()

`author_id` - ID of the person who sent it. You can use `self.fbIdToName(id)` method to get the name of the person.

`command` - all the fields of your command, so you access settings of it easier.

`args` - everything that was written after command name as a string. In this example it would be some item name, otherwise an error message would be written.

That's it. 

### Trivia game
Fill the question file each line question and answer like `question|answer`. 
