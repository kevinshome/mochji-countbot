import os
import ast
import json
import string
import discord
import dotenv

dotenv.load_dotenv()

class BotInfo():
    def __init__(self):
        self.lock = False
        self.last_number = 0
        self.last_guesser_id = 0
        self.highest_number = 0
        self.last_round_info = {
            "last_number": 0,
            "last_guesser_id": 0,
        }
        self.token_info = {
            "token_count": 0,
            "next_token_progress": 0.0,
            "cooldown_end": 0,
        }

        try:
            with open("./perpetual/info.json", 'r') as f:
                data = json.load(f)
                self.last_number = data["last_number"]
                self.last_guesser_id = data["last_guesser_id"]
                self.last_round_info = data["last_round_info"]
                self.highest_number = data["highest_number"]
                self.token_info = data["token_info"]
        except:
            pass

    def save_to_disk(self):
        data = {
            "last_number": self.last_number,
            "highest_number": self.highest_number,
            "last_guesser_id": self.last_guesser_id,
            "last_round_info": self.last_round_info,
            "token_info": self.token_info,
        }

        with open("./perpetual/info.json", 'w') as f:
            json.dump(data, f)

class CountBot(discord.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.info = BotInfo()

client = CountBot(intents=discord.Intents.all())

global guild
global baka_role


def eval_(node):
    try:
        op
    except NameError:
        import operator as op

    operators = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul,
                 ast.Div: op.truediv, ast.Pow: op.pow, ast.BitXor: op.xor,
                 ast.USub: op.neg, ast.BitOr: op.or_, ast.BitAnd: op.and_,
                 ast.LShift: op.lshift, ast.RShift: op.rshift}

    match node:
        case ast.Constant(value) if isinstance(value, int):
            return value  # integer
        case ast.BinOp(left, op, right):
            return operators[type(op)](eval_(left), eval_(right))
        case ast.UnaryOp(op, operand):  # e.g., -1
            return operators[type(op)](eval_(operand))
        case _:
            raise TypeError(node)


@client.event
async def on_ready():
    global guild
    global baka_role

    guild = await client.fetch_guild(int(os.environ["GUILD_ID"]))
    guild_roles = await guild.fetch_roles()
    for role in guild_roles:
        if role.id == int(os.environ["BAKA_ROLE_ID"]):
            baka_role = role
            break
    else:
        baka_role = None
    print(f"Logged in as {client.user}")
    print(f"baka_role={baka_role}\nguild={guild}")
    print(f"channel_id={os.environ['COUNTING_CHANNEL_ID']}")
    print("Syncing commands...")
    await client.sync_commands(force=True)
    print("Done!")


@client.event
async def on_message(msg: discord.Message):
    global baka_role

    if msg.author.bot:
        return

    if (msg.author.id == client.info.last_guesser_id) and os.environ.get("DEBUG_MODE") is None:
        return

    if msg.channel.id != int(os.environ["COUNTING_CHANNEL_ID"]):
        return

    split_msg = msg.content.split()
    if len(split_msg) > 1:
        return

    potential_number = split_msg[0]

    if potential_number[0] not in string.digits and not potential_number[0].startswith("0x"):
        return

    try:
        potential_math_op = ast.parse(potential_number, mode="eval").body
        potential_number = eval_(potential_math_op)
    except SyntaxError:
        return

    #wait to obtain lock, if nec
    while 1:
        if client.info.lock:
            continue
        break

    client.info.lock = True
    if potential_number != client.info.last_number+1:
        await msg.add_reaction("❌")
        await msg.reply(
                f"Le Epic Fail! Should've been {client.info.last_number+1}, "
                f"not {potential_number}!\n\n"
                f"{msg.author.mention} is now a {baka_role.mention}"
        )
        await msg.author.add_roles(baka_role)
        client.info.last_round_info = {
            "last_number": client.info.last_number,
            "last_guesser_id": client.info.last_guesser_id,
        }
        client.info.token_info["next_token_progress"] = 0.0
        client.info.last_number = 0
        client.info.last_guesser_id = 0
    else:
        await msg.add_reaction("✅")
        client.info.last_number += 1
        if client.info.last_number > client.info.highest_number:
            client.info.highest_number = client.info.last_number+1
        client.info.last_guesser_id = msg.author.id
        if client.info.token_info["token_count"] < 2:
            client.info.token_info["next_token_progress"] += 0.02
            client.info.token_info["next_token_progress"] = round(client.info.token_info["next_token_progress"], 2)
            if client.info.token_info["next_token_progress"] == 1.0:
                client.info.token_info["next_token_progress"] = 0.0
                client.info.token_info["token_count"] += 1

    client.info.save_to_disk()
    client.info.lock = False
    return

@client.slash_command()
async def revive(ctx: discord.ApplicationContext):
    if client.info.last_number != 0:
        await ctx.respond("You are in the middle of an active counting session!", ephemeral=True)
        return
    if client.info.last_round_info["last_number"] < client.info.token_info["cooldown_end"]:
        await ctx.respond("You failed the count before the cooldown ended! ):", ephemeral=True)
        return
    if client.info.token_info["token_count"] == 0:
        await ctx.respond("You don't have any revive tokens! ):", ephemeral=True)
        return
    
    client.info.last_number = client.info.last_round_info["last_number"]
    client.info.last_guesser_id = client.info.last_round_info["last_guesser_id"]
    client.info.last_round_info = {
        "last_number": 0,
        "last_guesser_id": 0
    }
    client.info.token_info["token_count"] -= 1
    client.info.token_info["cooldown_end"] = client.info.last_number + 50
    client.info.save_to_disk()

    await ctx.respond("You have successfully used a revive token!\n\n"
             f"You can not use another one until you get to the number {client.info.token_info['cooldown_end']}\n"
             f"Resume counting from {client.info.last_number}!"
             )

    return

@client.slash_command()
async def info(ctx: discord.ApplicationContext):
    emb = discord.Embed(
        title="Current session information",
        description=f"Current number: {client.info.last_number}\n"
        f"Revive tokens remaining: {client.info.token_info['token_count']}\n"
        f"Progress towards next token: {client.info.token_info['next_token_progress']:.0%} {'(Max tokens)' if client.info.token_info['token_count'] == 2 else ''}\n"
        f"Highest number: {client.info.highest_number}\n"
    )
    await ctx.respond(
        "",
        embed=emb,
        ephemeral=True
    )
    return


@client.slash_command()
async def help(ctx: discord.ApplicationContext):
    emb = discord.Embed(
        title="Counting bot help",
        description="The counting bot will only accept messages under the following circumstances:\n"
        "- The message has no spaces\n"
        "- The message only contains numbers (decimal (2) or hexadecimal (0x02)) and math operators\n"
        "- Math operations will ONLY be counted if they contain no spaces\n"
        "\n"
        "The counting bot accepts the following math operators:\n"
        "- ( + ) Addition\n"
        "- ( - ) Subtraction\n"
        "- ( * ) Multiplication\n"
        "- ( / ) Division\n"
        "- ( ** ) Exponent/Power\n"
        "\n"
        "The counting bot also accepts the following bitwise operators:\n"
        "- ( | ) OR\n"
        "- ( & ) AND\n"
        "- ( ^ ) XOR\n"
        "- ( >> ) Right Shift\n"
        "- ( << ) Left Shift\n"
    )

    await ctx.respond(
        "",
        embed=emb,
        ephemeral=True
    )
    return

client.run(os.environ["BOT_TOKEN"])
