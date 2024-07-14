import os
import ast
import json
import string
import discord
import dotenv

dotenv.load_dotenv()

client = discord.Client(intents=discord.Intents.all())

global last_number
global last_guesser_id
try:
    with open("info.json", 'r') as f:
        data = json.load(f)
        last_number = data.get("last_number", 0)
        last_guesser_id = data.get("last_guesser_id", 0)
except FileNotFoundError:
    last_number = 0
    last_guesser_id = 0
global guild
global baka_role


def eval_(node):
    try:
        op
    except NameError:
        import operator as op

    operators = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul,
                 ast.Div: op.truediv, ast.Pow: op.pow, ast.BitXor: op.xor,
                 ast.USub: op.neg}

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


@client.event
async def on_message(msg):
    global last_number
    global last_guesser_id
    global baka_role

    if msg.author.id == last_guesser_id:
        return

    if msg.channel.id != int(os.environ["COUNTING_CHANNEL_ID"]):
        return

    split_msg = msg.content.split()
    if len(split_msg) > 1:
        return

    potential_number = split_msg[0]

    if potential_number[0] not in string.digits:
        return

    try:
        potential_math_op = ast.parse(potential_number, mode="eval").body
        potential_number = eval_(potential_math_op)
    except SyntaxError:
        return

    if potential_number != last_number+1:
        await msg.add_reaction("❌")
        await msg.reply(
                f"Le Epic Fail! Should've been {last_number+1}, "
                f"not {potential_number}!\n\n"
                f"{msg.author.mention} is now a {baka_role.mention}"
        )
        await msg.author.add_roles(baka_role)
        last_number = 0
        last_guesser_id = 0
    else:
        await msg.add_reaction("✅")
        last_number += 1
        last_guesser_id = msg.author.id

    with open("info.json", "w") as f:
        json.dump(
                {"last_number": last_number,
                 "last_guesser_id": last_guesser_id}, f
                )
    return


client.run(os.environ["BOT_TOKEN"])
