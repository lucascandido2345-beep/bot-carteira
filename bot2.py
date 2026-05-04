import discord
from discord import app_commands
import gspread
from oauth2client.service_account import ServiceAccountCredentials

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import requests
from io import BytesIO
import unicodedata

TOKEN = "MTUwMDE5NzQwNTkxOTAyMzIwNg.GNGmpb.r0rBaiHLjFBdx8-pnDr8bRpwsGEWl9U3Uilt5k"

# ================= NORMALIZAR =================
def normalizar(texto):
    texto = texto.lower().strip()
    texto = unicodedata.normalize('NFD', texto)
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
    return texto

# ================= GOOGLE =================
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_name("credenciais.json", scope)
client = gspread.authorize(creds)
planilha = client.open_by_url("https://docs.google.com/spreadsheets/d/1CR6_sIrnryHl209JFUUM_EC5_D4Z69iGkGyZCaBTKH4/edit?usp=sharinghttps://docs.google.com/spreadsheets/d/1CR6_sIrnryHl209JFUUM_EC5_D4Z69iGkGyZCaBTKH4/edit?usp=sharing")

# ================= HORAS =================
def pegar_horas(user_id):
    aba = planilha.worksheet("Semanas")
    dados = aba.get_all_values()

    for linha in dados[1:]:
        if len(linha) < 6:
            continue

        if str(linha[0]) == str(user_id):
            return {
                "semana1": linha[2],
                "semana2": linha[3],
                "semana3": linha[4],
                "semana4": linha[5]
            }

    return {
        "semana1": "0h 0m",
        "semana2": "0h 0m",
        "semana3": "0h 0m",
        "semana4": "0h 0m"
    }

# ================= NOMES =================
def pegar_nomes_planilha():
    aba = planilha.worksheet("Semanas")
    dados = aba.get_all_values()
    return [(l[0], l[1]) for l in dados[1:] if len(l) >= 2]

# ================= FORMATAR NOME =================
def formatar_nome(member):
    nome = member.display_name

    if "|" in nome:
        p = nome.split("|")
        nome_limpo = p[0].split("]")[-1].strip()
        registro = p[1].strip()
        return nome_limpo, registro

    return nome, str(member.id)[-6:]

# ================= FILTRO =================
def cargo_valido(nome):
    nome_lower = normalizar(nome)

    if "alto escalao" in nome_lower:
        return False

    if any(p in nome_lower for p in ["subdivisoes", "cursos", "patente"]):
        return False

    if nome_lower == "caveira":
        return False

    letras = "".join(c for c in nome_lower if c.isalpha())
    if len(letras) < 3:
        return False

    return True

# ================= ORGANIZAR =================
def organizar_cargos(cargos):
    patente, cursos, subdiv, funcoes = [], [], [], []

    for cargo in cargos:
        nome = normalizar(cargo)

        if not cargo_valido(cargo):
            continue

        if nome in ["major","coronel","capitao","tenente","sargento"]:
            patente.append(cargo)

        elif any(x in nome for x in [
            "abordagem","acompanhamento","conduta",
            "geolocalizacao","modulacao","prisao"
        ]):
            cursos.append(cargo)

        elif "gam" in nome:
            subdiv.append(cargo)

        else:
            funcoes.append(cargo)

    return patente, cursos, subdiv, funcoes

# ================= CRIAR RG =================
def criar_rg(member, horas, cargos):
    from PIL import Image, ImageDraw, ImageFont, ImageEnhance
    import requests
    from io import BytesIO

    nome, registro = formatar_nome(member)
    patente, cursos, subdiv, funcoes = organizar_cargos(cargos)

    W, H = 1200, 600

    # ===== FUNDO =====
    base = Image.open("fundo_boep.png").resize((W, H))

    # escurecer fundo (SEM ERRO)
    enhancer = ImageEnhance.Brightness(base)
    base = enhancer.enhance(0.6)

    draw = ImageDraw.Draw(base)

    # ===== FONTES =====
    fonte_t = ImageFont.truetype("Montserrat-Bold.ttf", 44)
    fonte = ImageFont.truetype("Montserrat-Regular.ttf", 22)

    # ===== TITULO =====
    titulo = "BOPE - IDENTIFICAÇÃO"
    w_text = draw.textlength(titulo, font=fonte_t)
    draw.text(((W - w_text)//2, 30), titulo, font=fonte_t, fill=(255,255,255))

    # ===== FOTO =====
    resp = requests.get(member.display_avatar.url)
    avatar = Image.open(BytesIO(resp.content)).resize((200,200))

    mask = Image.new("L",(200,200),0)
    ImageDraw.Draw(mask).ellipse((0,0,200,200),fill=255)
    avatar.putalpha(mask)

    x_foto, y_foto = 100, 160
    base.paste(avatar,(x_foto,y_foto),avatar)

    # glow vermelho
    for i in range(4):
        draw.ellipse(
            (x_foto-i, y_foto-i, x_foto+200+i, y_foto+200+i),
            outline=(255,0,0)
        )

    # ===== INFO CENTRAL =====
    x_info = 380

    draw.text((x_info,150),f"NOME: {nome}",font=fonte,fill=(255,255,255))
    draw.text((x_info,185),f"REGISTRO: {registro}",font=fonte,fill=(255,255,255))

    draw.text((x_info,220),"HORAS:",font=fonte,fill=(255,255,255))

    draw.text((x_info,250),f"Semana 1: {horas['semana1']}",font=fonte,fill=(200,200,200))
    draw.text((x_info,275),f"Semana 2: {horas['semana2']}",font=fonte,fill=(200,200,200))
    draw.text((x_info,300),f"Semana 3: {horas['semana3']}",font=fonte,fill=(200,200,200))
    draw.text((x_info,325),f"Semana 4: {horas['semana4']}",font=fonte,fill=(200,200,200))

    # ===== CURSOS =====
    y_c = 370
    draw.text((100,y_c),"CURSOS:",font=fonte,fill=(255,255,255))
    y_c += 25

    for c in cursos[:5]:
        draw.text((120,y_c),f"• {c}",font=fonte,fill=(200,200,200))
        y_c += 22

    # ===== DIREITA =====
    x_dir = 760

    y_f = 230
    draw.text((x_dir,y_f),"FUNÇÕES:",font=fonte,fill=(255,255,255))
    y_f += 25

    for f in funcoes[:2]:
        draw.text((x_dir,y_f),f"• {f}",font=fonte,fill=(200,200,200))
        y_f += 22

    y_s = y_f + 10
    draw.text((x_dir,y_s),"SUBDIVISÕES:",font=fonte,fill=(255,255,255))
    y_s += 25

    for s in subdiv[:2]:
        draw.text((x_dir,y_s),f"• {s}",font=fonte,fill=(200,200,200))
        y_s += 22

    # ===== RODAPÉ (CORRIGIDO) =====
    texto_final = "BATALHÃO DE OPERAÇÕES ESPECIAIS"
    w_final = draw.textlength(texto_final, font=fonte)
    draw.text(((W - w_final)//2, 530), texto_final, font=fonte, fill=(180,180,180))

    caminho = f"rg_{member.id}.png"
    base.save(caminho)
    return caminho

# ================= DISCORD =================
intents = discord.Intents.default()
intents.members = True

bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

@tree.command(name="carteira")
@app_commands.describe(nome="Nome do membro")
async def carteira(interaction: discord.Interaction, nome: str):

    dados = pegar_nomes_planilha()

    user_id = None
    for uid, n in dados:
        if n.lower() == nome.lower():
            user_id = uid
            break

    if not user_id:
        await interaction.response.send_message("Nome não encontrado.", ephemeral=True)
        return

    member = interaction.guild.get_member(int(user_id))

    if not member:
        await interaction.response.send_message("Membro não encontrado.", ephemeral=True)
        return

    horas = pegar_horas(user_id)
    cargos = [r.name for r in member.roles if r.name != "@everyone"]

    caminho = criar_rg(member, horas, cargos)

    await interaction.response.send_message(file=discord.File(caminho), ephemeral=True)

@carteira.autocomplete("nome")
async def autocomplete_nome(interaction: discord.Interaction, current: str):
    dados = pegar_nomes_planilha()

    return [
        app_commands.Choice(name=n, value=n)
        for _, n in dados if current.lower() in n.lower()
    ][:25]

@bot.event
async def on_ready():
    await tree.sync()
    print("Bot online!")

bot.run(TOKEN)