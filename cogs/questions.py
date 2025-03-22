import discord
from discord.ext import commands

from settings import settings


class QuestionModal(discord.ui.Modal, title="Ask a Question"):
    def __init__(self, course_name: str, cog):
        super().__init__()
        self.course_name = course_name
        self.cog = cog  # Para poder guardar datos en la Cog

        self.question = discord.ui.TextInput(
            label="Question",
            style=discord.TextStyle.paragraph,
            required=True
        )
        self.context = discord.ui.TextInput(
            label="What did you try? (optional)",
            style=discord.TextStyle.paragraph,
            required=False
        )
        self.add_item(self.question)
        self.add_item(self.context)

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="New Question",
            description=(
                f"**Course:** {self.course_name}\n\n"
                f"**Question:** {self.question.value}\n\n"
                f"**Context:** {self.context.value or 'Not provided'}"
            ),
            color=discord.Color.blurple()
        )
        embed.set_footer(
            text=f"Asked by {interaction.user}",
            icon_url=interaction.user.display_avatar.url
        )

        # 1) Canal del curso: crear el mensaje y el hilo
        await interaction.response.send_message(
            "✅ Your question was submitted successfully!",
            ephemeral=True
        )
        course_msg = await interaction.channel.send(embed=embed)
        course_thread = await course_msg.create_thread(name=self.question.value[:90])
        await course_thread.send(
            f"{interaction.user.mention}, your question has been received. You can continue the discussion here."
        )

        # 2) Canal central (pending-questions): solo mandamos un mensaje con link al hilo del curso
        question_channel = discord.utils.get(
            interaction.guild.text_channels,
            name=settings.PENDING_QUESTION_CHANNEL
        )
        pending_msg = None

        if question_channel:
            # Agregamos un campo o linea extra en la descripción
            embed_pending = embed.copy()
            embed_pending.description += (
                f"\n\n[Go to Thread in **{interaction.channel.name}** Channel]({course_thread.jump_url})"
            )

            pending_msg = await question_channel.send(embed=embed_pending)

        # 3) Registrar la pregunta en la estructura interna para poder manejarla luego
        #    Guardamos IDs y referencias en self.cog.question_pairs para usarlas en la View
        #    De este modo, al presionar el botón en cualquiera de los 2 canales sabremos
        #    qué hilos y mensajes actualizar.
        if pending_msg:
            pair = {
                "guild_id": interaction.guild.id,
                "course_channel_id": course_msg.channel.id,
                "course_msg_id": course_msg.id,
                "course_thread_id": course_thread.id,
                "pending_channel_id": pending_msg.channel.id,
                "pending_msg_id": pending_msg.id
            }
            self.cog.question_pairs[course_msg.id] = pair
            self.cog.question_pairs[pending_msg.id] = pair

            # 4) Agregar el mismo View (botón) en ambos mensajes
            view = MarkAsAnsweredView(self.cog)
            await course_msg.edit(view=view)
            await pending_msg.edit(view=view)


class MarkAsAnsweredView(discord.ui.View):
    """Vista que contiene el botón para marcar una pregunta como respondida."""
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog  # Para acceder a question_pairs

    @discord.ui.button(label="✅ Mark as Answered", style=discord.ButtonStyle.success)
    async def mark_answered(self, interaction: discord.Interaction, button: discord.ui.Button):
        # 1) Ubicar la referencia (par) de este mensaje
        pair = self.cog.question_pairs.get(interaction.message.id)
        if not pair:
            # No se encontró la info. Posiblemente ya se marcó o algo pasó.
            await interaction.response.send_message(
                "Error: I can't find the original question data.",
                ephemeral=True
            )
            return

        guild = self.cog.bot.get_guild(pair["guild_id"])
        if not guild:
            await interaction.response.send_message(
                "Error: Guild not found.",
                ephemeral=True
            )
            return

        # 2) Obtener referencias a los dos mensajes
        course_channel = guild.get_channel(pair["course_channel_id"])
        pending_channel = guild.get_channel(pair["pending_channel_id"])
        if not course_channel or not pending_channel:
            await interaction.response.send_message(
                "Error: Missing channels.",
                ephemeral=True
            )
            return

        try:
            course_msg = await course_channel.fetch_message(pair["course_msg_id"])
            pending_msg = await pending_channel.fetch_message(pair["pending_msg_id"])
        except discord.NotFound:
            await interaction.response.send_message(
                "Error: One of the messages no longer exists.",
                ephemeral=True
            )
            return

        # 3) Actualizar ambos embeds a verde y "Question Answered"
        to_update = [course_msg, pending_msg]
        for msg in to_update:
            if msg and msg.embeds:
                embed = msg.embeds[0]
                embed.color = discord.Color.green()
                embed.title = "✅ Question Answered"
                await msg.edit(embed=embed, view=None)  # Quitar el botón

        # 4) Archivar/cerrar el hilo en el canal del curso
        course_thread = guild.get_thread(pair["course_thread_id"])
        if course_thread:
            await course_thread.edit(archived=True, locked=True)

        # 5) Limpiar el diccionario para no acumular datos viejos
        self.cog.question_pairs.pop(pair["course_msg_id"], None)
        self.cog.question_pairs.pop(pair["pending_msg_id"], None)

        # 6) Notificar
        await interaction.response.send_message(
            "✅ This question has been marked as answered and the course thread is now closed.",
            ephemeral=True
        )


class QuestionView(discord.ui.View):
    @discord.ui.button(label="Ask a Question", style=discord.ButtonStyle.primary, custom_id="ask_question")
    async def ask_question(self, interaction: discord.Interaction, button: discord.ui.Button):
        course_name = interaction.channel.name.replace("-", " ").title()

        # Usamos `cog = ...` para pasarle la referencia a QuestionModal
        cog = interaction.client.get_cog("Questions")
        await interaction.response.send_modal(QuestionModal(course_name, cog))


class Questions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Aquí iremos almacenando pares de mensajes: { message_id: {...datos...} }
        self.question_pairs = {}

    @commands.command(name="preguntar")
    @commands.has_permissions(manage_messages=True)
    async def pin_button(self, ctx):
        """Pins a message with the Ask a Question button"""
        view = QuestionView()
        await ctx.send("Got a question? Click below!", view=view)


async def setup(bot):
    await bot.add_cog(Questions(bot))