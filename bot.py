import discord
from discord.ext import commands
from discord import app_commands
import random
import os
import threading
from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "DevCodeBot działa!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_web, daemon=True).start()


# ============================================================
# KONFIGURACJA
# ============================================================

TOKEN= "MTU0ODAyMDgwNTY5NzU0NDI5Mg.GB45Rp.KI0Pxz7q9Eb_2iOa328Z-pOq6u4Wo60dqR1fwo"

SERVER_NAME = "DevCode"

LOBBY_CHANNEL = "『👋』lobby"
TICKET_CATEGORY = "Tickety"
SCREEN_CHANNEL = "『📸』screeny"

VERIFY_ROLE = "Dostęp"
FREE_ACCESS_ROLE = "Free Dostęp"

SERVER_BANNER = "https://i.imgur.com/pPSCfsl.png"


# ============================================================
# INTENTS
# ============================================================

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.presences = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


# ============================================================
# FUNKCJE POMOCNICZE
# ============================================================

def is_admin(interaction: discord.Interaction):
    return (
        interaction.user.guild_permissions.administrator
        or interaction.user.id == interaction.guild.owner_id
    )


def can_review_screen(interaction: discord.Interaction):
    return (
        interaction.user.guild_permissions.administrator
        or interaction.user.id == interaction.guild.owner_id
    )


async def get_ticket_owner(channel):
    if not channel.topic:
        return None

    if not channel.topic.startswith("ticket_owner:"):
        return None

    try:
        return int(channel.topic.split(":")[1])
    except ValueError:
        return None


def can_close_ticket(interaction: discord.Interaction):
    if interaction.user.guild_permissions.administrator:
        return True

    if interaction.user.id == interaction.guild.owner_id:
        return True

    # sprawdzimy właściciela ticketu później
    return False


# ============================================================
# ZAMYKANIE TICKETA
# ============================================================

class CloseTicketView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Zamknij ticket",
        emoji="🔒",
        style=discord.ButtonStyle.danger,
        custom_id="close_ticket"
    )
    async def close_ticket(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        owner_id = await get_ticket_owner(interaction.channel)

        allowed = (
            interaction.user.guild_permissions.administrator
            or interaction.user.id == interaction.guild.owner_id
            or interaction.user.id == owner_id
        )

        if not allowed:
            await interaction.response.send_message(
                "❌ Nie masz uprawnień do zamknięcia tego ticketa.",
                ephemeral=True
            )
            return

        await interaction.response.defer()

        try:
            await interaction.channel.delete()
        except discord.Forbidden:
            await interaction.followup.send(
                "❌ Bot nie może usunąć tego kanału.",
                ephemeral=True
            )


# ============================================================
# TWORZENIE TICKETA
# ============================================================

async def create_ticket(
    interaction: discord.Interaction,
    ticket_name: str
):

    guild = interaction.guild
    member = interaction.user

    category = discord.utils.get(
        guild.categories,
        name=TICKET_CATEGORY
    )

    if category is None:
        await interaction.response.send_message(
            f"❌ Nie znaleziono kategorii **{TICKET_CATEGORY}**.",
            ephemeral=True
        )
        return

    # sprawdzanie czy użytkownik ma już ticket
    for channel in category.channels:
        if isinstance(channel, discord.TextChannel):

            owner_id = await get_ticket_owner(channel)

            if owner_id == member.id:
                await interaction.response.send_message(
                    "❌ Masz już otwarty ticket.",
                    ephemeral=True
                )
                return

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(
            view_channel=False
        ),

        member: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True,
            embed_links=True
        )
    }

    bot_member = guild.get_member(bot.user.id)

    if bot_member:
        overwrites[bot_member] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            manage_channels=True,
            manage_messages=True
        )

    channel = await guild.create_text_channel(
        name=ticket_name,
        category=category,
        overwrites=overwrites,
        topic=f"ticket_owner:{member.id}"
    )

    embed = discord.Embed(
        title="🎫 Ticket",
        description=(
            f"👤 **Użytkownik:** {member.mention}\n\n"
            "Opisz tutaj swój problem.\n"
            "Administracja odpowie tak szybko, jak to możliwe."
        ),
        color=discord.Color.blurple()
    )

    embed.set_image(url=SERVER_BANNER)

    await channel.send(
        content=member.mention,
        embed=embed,
        view=CloseTicketView()
    )

    await interaction.response.send_message(
        f"✅ Ticket został utworzony: {channel.mention}",
        ephemeral=True
    )


# ============================================================
# MODAL — INNE
# ============================================================

class OtherTicketModal(discord.ui.Modal, title="Inny problem"):

    problem = discord.ui.TextInput(
        label="Opisz swój problem",
        placeholder="Napisz, w czym potrzebujesz pomocy...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1000
    )

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        guild = interaction.guild
        member = interaction.user

        category = discord.utils.get(
            guild.categories,
            name=TICKET_CATEGORY
        )

        if category is None:
            await interaction.response.send_message(
                f"❌ Nie znaleziono kategorii **{TICKET_CATEGORY}**.",
                ephemeral=True
            )
            return

        for channel in category.channels:
            if isinstance(channel, discord.TextChannel):

                owner_id = await get_ticket_owner(channel)

                if owner_id == member.id:
                    await interaction.response.send_message(
                        "❌ Masz już otwarty ticket.",
                        ephemeral=True
                    )
                    return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(
                view_channel=False
            ),

            member: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True
            )
        }

        bot_member = guild.get_member(bot.user.id)

        if bot_member:
            overwrites[bot_member] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_channels=True,
                manage_messages=True
            )

        channel = await guild.create_text_channel(
            name=f"inne-{member.name}",
            category=category,
            overwrites=overwrites,
            topic=f"ticket_owner:{member.id}"
        )

        embed = discord.Embed(
            title="🎫 Ticket — Inne",
            description=(
                f"👤 **Użytkownik:** {member.mention}\n\n"
                f"📝 **Problem:**\n{self.problem.value}"
            ),
            color=discord.Color.blurple()
        )

        embed.set_image(url=SERVER_BANNER)

        await channel.send(
            content=member.mention,
            embed=embed,
            view=CloseTicketView()
        )

        await interaction.response.send_message(
            f"✅ Ticket został utworzony: {channel.mention}",
            ephemeral=True
        )


# ============================================================
# PANEL TICKETÓW
# ============================================================

class TicketView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Pomoc z pluginem/skryptem",
        emoji="🧩",
        style=discord.ButtonStyle.primary,
        custom_id="ticket_plugin"
    )
    async def plugin_ticket(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await create_ticket(
            interaction,
            f"plugin-{interaction.user.name}"
        )

    @discord.ui.button(
        label="Pogadać z administracją",
        emoji="👮",
        style=discord.ButtonStyle.secondary,
        custom_id="ticket_admin"
    )
    async def admin_ticket(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await create_ticket(
            interaction,
            f"admin-{interaction.user.name}"
        )

    @discord.ui.button(
        label="Inne",
        emoji="❓",
        style=discord.ButtonStyle.secondary,
        custom_id="ticket_other"
    )
    async def other_ticket(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await interaction.response.send_modal(
            OtherTicketModal()
        )


# ============================================================
# WERYFIKACJA — MATEMATYKA
# ============================================================

def generate_math_question():

    a = random.randint(0, 20)
    b = random.randint(0, 20)

    return a, b, a + b


# ============================================================
# MODAL ODPOWIEDZI
# ============================================================

class VerifyAnswerModal(discord.ui.Modal):

    def __init__(self, correct_answer):

        super().__init__(
            title="Weryfikacja"
        )

        self.correct_answer = correct_answer

    answer = discord.ui.TextInput(
        label="Podaj wynik",
        placeholder="Wpisz odpowiedź...",
        required=True,
        max_length=10
    )

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        try:
            answer = int(self.answer.value)
        except ValueError:

            await interaction.response.send_message(
                "❌ Podaj liczbę.",
                ephemeral=True
            )
            return

        if answer == self.correct_answer:

            role = discord.utils.get(
                interaction.guild.roles,
                name=VERIFY_ROLE
            )

            if role is None:
                await interaction.response.send_message(
                    f"❌ Nie znaleziono roli **{VERIFY_ROLE}**.",
                    ephemeral=True
                )
                return

            bot_member = interaction.guild.get_member(
                bot.user.id
            )

            if bot_member is None:
                await interaction.response.send_message(
                    "❌ Nie znaleziono bota.",
                    ephemeral=True
                )
                return

            if role >= bot_member.top_role:

                await interaction.response.send_message(
                    f"❌ Nie mogę nadać roli **{VERIFY_ROLE}**.\n\n"
                    "Przenieś rolę bota wyżej niż tę rolę.",
                    ephemeral=True
                )
                return

            if role in interaction.user.roles:

                await interaction.response.send_message(
                    "✅ Jesteś już zweryfikowany!",
                    ephemeral=True
                )
                return

            try:

                await interaction.user.add_roles(
                    role,
                    reason="Pomyślna weryfikacja"
                )

            except discord.Forbidden:

                await interaction.response.send_message(
                    "❌ Bot nie może nadać roli.",
                    ephemeral=True
                )
                return

            await interaction.response.send_message(
                "✅ **Poprawna odpowiedź!**\n"
                "Otrzymałeś dostęp.",
                ephemeral=True
            )

        else:

            a, b, result = generate_math_question()

            await interaction.response.send_message(
                f"❌ Zła odpowiedź!\n\n"
                f"Nowe działanie: **{a} + {b} = ?**",
                ephemeral=True
            )

            # nowe pytanie zostanie pokazane w następnej wiadomości
            try:

                await interaction.followup.send(
                    view=VerifyQuestionView(
                        a,
                        b,
                        result
                    ),
                    ephemeral=True
                )

            except discord.HTTPException:
                pass


# ============================================================
# PYTANIE WERYFIKACYJNE
# ============================================================

class VerifyQuestionView(discord.ui.View):

    def __init__(
        self,
        a,
        b,
        result
    ):

        super().__init__(timeout=300)

        self.a = a
        self.b = b
        self.result = result

    @discord.ui.button(
        label="Podaj odpowiedź",
        emoji="✏️",
        style=discord.ButtonStyle.primary
    )
    async def answer_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await interaction.response.send_modal(
            VerifyAnswerModal(
                self.result
            )
        )


# ============================================================
# PANEL WERYFIKACJI
# ============================================================

class VerifyView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Zweryfikuj się",
        emoji="✅",
        style=discord.ButtonStyle.success,
        custom_id="verify_access"
    )
    async def verify(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        role = discord.utils.get(
            interaction.guild.roles,
            name=VERIFY_ROLE
        )

        if role is None:

            await interaction.response.send_message(
                f"❌ Nie znaleziono roli **{VERIFY_ROLE}**.",
                ephemeral=True
            )
            return

        if role in interaction.user.roles:

            await interaction.response.send_message(
                "✅ Jesteś już zweryfikowany!",
                ephemeral=True
            )
            return

        a, b, result = generate_math_question()

        embed = discord.Embed(
            title="🧮 Weryfikacja",
            description=(
                "Rozwiąż działanie:\n\n"
                f"## **{a} + {b} = ?**\n\n"
                "Kliknij przycisk i wpisz wynik."
            ),
            color=discord.Color.green()
        )

        await interaction.response.send_message(
            embed=embed,
            view=VerifyQuestionView(
                a,
                b,
                result
            ),
            ephemeral=True
        )


# ============================================================
# SYSTEM SCREENÓW
# ============================================================

class ScreenReviewView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    # --------------------------------------------------------
    # NADAJ
    # --------------------------------------------------------

    @discord.ui.button(
        label="Nadaj",
        emoji="🟢",
        style=discord.ButtonStyle.success,
        custom_id="screen_accept"
    )
    async def accept(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not can_review_screen(interaction):

            await interaction.response.send_message(
                "❌ Tylko właściciel serwera lub administrator "
                "może sprawdzać screeny.",
                ephemeral=True
            )
            return

        target_id = None

        if interaction.message.embeds:

            embed = interaction.message.embeds[0]

            if embed.footer and embed.footer.text:

                try:

                    target_id = int(
                        embed.footer.text.split(":")[-1]
                    )

                except ValueError:
                    pass

        if target_id is None:

            await interaction.response.send_message(
                "❌ Nie udało się znaleźć autora screena.",
                ephemeral=True
            )
            return

        member = interaction.guild.get_member(
            target_id
        )

        if member is None:

            await interaction.response.send_message(
                "❌ Nie znaleziono użytkownika.",
                ephemeral=True
            )
            return

        role = discord.utils.get(
            interaction.guild.roles,
            name=FREE_ACCESS_ROLE
        )

        if role is None:

            await interaction.response.send_message(
                f"❌ Nie znaleziono roli **{FREE_ACCESS_ROLE}**.",
                ephemeral=True
            )
            return

        bot_member = interaction.guild.get_member(
            bot.user.id
        )

        if bot_member is None:

            await interaction.response.send_message(
                "❌ Nie znaleziono bota.",
                ephemeral=True
            )
            return

        if role >= bot_member.top_role:

            await interaction.response.send_message(
                f"❌ Nie mogę nadać roli **{FREE_ACCESS_ROLE}**.\n\n"
                "Przenieś rolę bota wyżej niż tę rolę.",
                ephemeral=True
            )
            return

        try:

            await member.add_roles(
                role,
                reason=(
                    f"Screen zaakceptowany przez "
                    f"{interaction.user}"
                )
            )

        except discord.Forbidden:

            await interaction.response.send_message(
                f"❌ Nie mogę nadać roli **{FREE_ACCESS_ROLE}**.",
                ephemeral=True
            )
            return

        except discord.HTTPException as error:

            print(
                f"[SCREEN] Błąd nadawania roli: {error}"
            )

            await interaction.response.send_message(
                "❌ Wystąpił błąd podczas nadawania roli.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            f"🎉 **Brawo {member.mention}!** "
            "Dostałeś dostęp do darmowych "
            "pluginów/skryptów."
        )

        # wyłączenie przycisków

        for item in self.children:
            item.disabled = True

        try:

            await interaction.message.edit(
                view=self
            )

        except discord.HTTPException as error:

            print(
                f"[SCREEN] Nie udało się wyłączyć przycisków: "
                f"{error}"
            )

    # --------------------------------------------------------
    # ODRZUĆ
    # --------------------------------------------------------

    @discord.ui.button(
        label="Odrzuć",
        emoji="🔴",
        style=discord.ButtonStyle.danger,
        custom_id="screen_reject"
    )
    async def reject(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not can_review_screen(interaction):

            await interaction.response.send_message(
                "❌ Tylko właściciel serwera lub administrator "
                "może sprawdzać screeny.",
                ephemeral=True
            )
            return

        target_message_id = None

        if interaction.message.embeds:

            embed = interaction.message.embeds[0]

            if embed.description:

                try:

                    target_message_id = int(
                        embed.description.split(
                            "MESSAGE_ID:"
                        )[1]
                    )

                except (ValueError, IndexError):
                    pass

        await interaction.response.defer(
            ephemeral=True
        )

        # usuwanie oryginalnego screena

        if target_message_id:

            try:

                screen_message = (
                    await interaction.channel.fetch_message(
                        target_message_id
                    )
                )

                await screen_message.delete()

            except discord.NotFound:
                pass

            except discord.Forbidden:

                await interaction.followup.send(
                    "❌ Bot nie może usunąć wiadomości "
                    "ze screenem.\n\n"
                    "Nadaj botowi uprawnienie "
                    "**Zarządzanie wiadomościami**.",
                    ephemeral=True
                )
                return

            except discord.HTTPException as error:

                print(
                    f"[SCREEN] Błąd usuwania screena: {error}"
                )

        # usuwanie wiadomości bota z przyciskami

        try:

            await interaction.message.delete()

        except discord.HTTPException:
            pass


# ============================================================
# ON READY
# ============================================================

@bot.event
async def on_ready():

    print("===================================")
    print(f"Zalogowano jako: {bot.user}")
    print(f"ID: {bot.user.id}")
    print("===================================")

    # status

    activity = discord.Activity(
        type=discord.ActivityType.watching,
        name="najlepszy serwer code"
    )

    await bot.change_presence(
        status=discord.Status.online,
        activity=activity
    )

    # persistent views

    bot.add_view(TicketView())
    bot.add_view(CloseTicketView())
    bot.add_view(VerifyView())
    bot.add_view(ScreenReviewView())

    try:

        synced = await bot.tree.sync()

        print(
            f"Zsynchronizowano {len(synced)} komend."
        )

    except Exception as error:

        print(
            f"Błąd synchronizacji komend: {error}"
        )


# ============================================================
# WELCOME
# ============================================================

@bot.event
async def on_member_join(member):

    channel = discord.utils.get(
        member.guild.text_channels,
        name=LOBBY_CHANNEL
    )

    if channel is None:
        return

    embed = discord.Embed(
        title="👋 Witaj na DevCode!",
        description=(
            f"Cześć {member.mention}!\n\n"
            "Miło Cię widzieć na naszym serwerze."
        ),
        color=discord.Color.green()
    )

    embed.set_image(
        url=SERVER_BANNER
    )

    await channel.send(
        embed=embed
    )


# ============================================================
# LEAVE
# ============================================================

@bot.event
async def on_member_remove(member):

    channel = discord.utils.get(
        member.guild.text_channels,
        name=LOBBY_CHANNEL
    )

    if channel is None:
        return

    await channel.send(
        f"👋 **{member}** opuścił serwer."
    )


# ============================================================
# ON MESSAGE — SCREENY
# ============================================================

@bot.event
async def on_message(message):

    if message.author.bot:
        return

    # --------------------------------------------------------
    # SCREENY
    # --------------------------------------------------------

    if message.channel.name == SCREEN_CHANNEL:

        has_image = False

        for attachment in message.attachments:

            if attachment.content_type:

                if attachment.content_type.startswith(
                    "image/"
                ):
                    has_image = True
                    break

            else:

                if attachment.filename.lower().endswith(
                    (
                        ".png",
                        ".jpg",
                        ".jpeg",
                        ".webp",
                        ".gif"
                    )
                ):
                    has_image = True
                    break

        if has_image:

            print(
                f"[SCREEN] Wykryto screen od: "
                f"{message.author} "
                f"({message.author.id})"
            )

            embed = discord.Embed(
                title="📸 Screen do sprawdzenia",
                description=(
                    f"👤 **Autor:** "
                    f"{message.author.mention}\n\n"
                    f"🔗 [Przejdź do screena]"
                    f"({message.jump_url})\n\n"
                    f"MESSAGE_ID:{message.id}"
                ),
                color=discord.Color.orange()
            )

            embed.set_thumbnail(
                url=message.author.display_avatar.url
            )

            embed.set_footer(
                text=f"USER_ID:{message.author.id}"
            )

            try:

                # WAŻNE:
                # bot wysyła WŁASNĄ wiadomość
                # zamiast edytować wiadomość użytkownika

                await message.channel.send(
                    embed=embed,
                    view=ScreenReviewView()
                )

                print(
                    "[SCREEN] Wysłano przyciski."
                )

            except discord.Forbidden as error:

                print(
                    "[SCREEN] BRAK UPRAWNIEŃ "
                    "DO WYSŁANIA WIADOMOŚCI:"
                )

                print(error)

            except discord.HTTPException as error:

                print(
                    "[SCREEN] Błąd Discord API:"
                )

                print(error)

            except Exception as error:

                print(
                    "[SCREEN] Nieznany błąd:"
                )

                print(error)

    await bot.process_commands(message)


# ============================================================
# /PANEL
# ============================================================

@bot.tree.command(
    name="panel",
    description="Wyślij panel ticketów."
)
async def panel(
    interaction: discord.Interaction
):

    if not is_admin(interaction):

        await interaction.response.send_message(
            "❌ Nie masz uprawnień do tej komendy.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="🎫 Centrum pomocy DevCode",
        description=(
            "Potrzebujesz pomocy?\n\n"
            "🧩 **Pomoc z pluginem/skryptem**\n"
            "👮 **Pogadać z administracją**\n"
            "❓ **Inne**\n\n"
            "Wybierz odpowiednią opcję poniżej."
        ),
        color=discord.Color.blurple()
    )

    embed.set_image(
        url=SERVER_BANNER
    )

    await interaction.response.send_message(
        embed=embed,
        view=TicketView()
    )


# ============================================================
# /WERYFIKACJA
# ============================================================

@bot.tree.command(
    name="weryfikacja",
    description="Wyślij panel weryfikacji."
)
async def verification(
    interaction: discord.Interaction
):

    if not is_admin(interaction):

        await interaction.response.send_message(
            "❌ Nie masz uprawnień do tej komendy.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="✅ Weryfikacja DevCode",
        description=(
            "Aby uzyskać dostęp do serwera,\n"
            "musisz przejść prostą weryfikację.\n\n"
            "Kliknij przycisk **Zweryfikuj się**."
        ),
        color=discord.Color.green()
    )

    embed.set_image(
        url=SERVER_BANNER
    )

    await interaction.response.send_message(
        embed=embed,
        view=VerifyView()
    )


# ============================================================
# /PING
# ============================================================

@bot.tree.command(
    name="ping",
    description="Sprawdź ping bota."
)
async def ping(
    interaction: discord.Interaction
):

    latency = round(
        bot.latency * 1000
    )

    await interaction.response.send_message(
        f"🏓 Pong! **{latency}ms**"
    )


# ============================================================
# START
# ============================================================


bot.run(os.getenv("DISCORD_TOKEN"))
