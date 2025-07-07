import os
import discord 
from discord.ext import commands 
from discord import app_commands, File
from dotenv import load_dotenv 
import random
from datetime import timedelta

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Casino-style timeout messages
GAMBLER_MESSAGES = {
    1: "got a quick slap on the wrist - back in 1 minute!",
    5: "busted with a pair of deuces! 5 minute cool-off",
    10: "went all-in and crapped out! 10 minute penalty",
    15: "pushed their luck too far! 15 minute timeout",
    20: "hit the MAXIMUM SECURITY LOCKOUT! 20 minutes in the cooler"
}

vote_sessions = {}

class VoteSession:
    def __init__(self, target, initiator):
        self.target = target
        self.initiator = initiator
        self.voters = set()
        self.voters.add(initiator.id)
        self.message = None

    def add_vote(self, voter_id):
        self.voters.add(voter_id)
    
    def count_votes(self):
        return len(self.voters)

@bot.event 
async def on_ready():
    await bot.tree.sync()
    print(f"{bot.user} is online and ready to deal!")

@bot.tree.command(name="timeout_vote", description="Start a vote to send someone to timeout jail")
@app_commands.describe(player="The gambler to send to the penalty box")
async def timeout_vote(interaction: discord.Interaction, player: discord.Member):
    if player.id == interaction.guild.owner_id:
        await interaction.response.send_message("🚨 The House always wins! Can't timeout the boss!", ephemeral=True)
        return
    
    if player.id in vote_sessions:
        await interaction.response.send_message(
            f"⚠️ We're already voting on {player.mention}'s fate!",
            ephemeral=True
        )
        return
    
    vote_sessions[player.id] = VoteSession(player, interaction.user)
    
    embed = discord.Embed(
        title="🎲 TIME OUT VOTE",
        description=f"The table is voting on {player.mention}'s fate!\n\n"
                   f"✅ - Send 'em to the cooler\n"
                   f"❌ - Let 'em ride\n\n"
                   f"1 vote (need 2 to convict)",
        color=0xFFD700  # Gold
    )
    message = await interaction.channel.send(embed=embed)
    vote_sessions[player.id].message = message
    await message.add_reaction("✅")
    await message.add_reaction("❌")
    
    await interaction.response.send_message(
        f"🎰 Started timeout vote for {player.mention}!",
        ephemeral=True
    )

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return
    
    for player_id, session in list(vote_sessions.items()):
        if session.message and session.message.id == reaction.message.id:
            if str(reaction.emoji) == "✅":
                session.add_vote(user.id)
                
                if session.count_votes() >= 2:
                    # Casino-style random timeout (1-20 mins)
                    duration = random.choice([1, 5, 10, 15, 20])
                    message = GAMBLER_MESSAGES[duration]
                    
                    try:
                        await session.target.timeout(timedelta(minutes=duration), reason="Vote timeout")
                        
                        # Deal the GIF card
                        with open("gambling-gamble.gif", "rb") as f:
                            file = File(f, filename="busted.gif")
                        
                        embed = discord.Embed(
                            title="💥 BUSTED! 💥",
                            description=f"**{session.target.mention}** {message}",
                            color=0xFF0000  # Red
                        )
                        embed.set_image(url="attachment://busted.gif")
                        
                        await session.message.delete()
                        await session.message.channel.send(
                            file=file,
                            embed=embed
                        )
                        
                    except discord.Forbidden:
                        embed = discord.Embed(
                            title="🚨 HOUSE RULES",
                            description=f"The House protects {session.target.mention}!", 
                            color=0x00FF00  # Green
                        )
                        await session.message.edit(embed=embed)
                    
                    del vote_sessions[player_id]
                else:
                    embed = session.message.embeds[0]
                    embed.description = (
                        f"The table is voting on {session.target.mention}'s fate!\n\n"
                        f"✅ - Send 'em to the cooler\n"
                        f"❌ - Let 'em ride\n\n"
                        f"{session.count_votes()} votes (need 2 to convict)"
                    )
                    await session.message.edit(embed=embed)
            
            elif str(reaction.emoji) == "❌" and user.id == session.initiator.id:
                await session.message.delete()
                await session.message.channel.send(
                    f"🃏 {session.target.mention} gets a walk! Vote cancelled."
                )
                del vote_sessions[player_id]

bot.run(TOKEN)