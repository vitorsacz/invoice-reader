import unicodedata

import pandas as pd

CATEGORIAS = [
    "Alimentação", "Mercado", "Transporte", "Saúde", "Lazer", "Educação",
    "Vestuário", "Moradia", "Assinaturas", "Compras Online", "Serviços",
    "Não categorizado",
]

NAO_CATEGORIZADO = "Não categorizado"

# Regras avaliadas em ordem - a primeira palavra-chave que bater no nome
# normalizado do estabelecimento vence. Categorias mais especificas/propensas
# a falso-positivo (ex: "AMAZON PRIME" vs "AMAZON") vem antes das genericas.
REGRAS = [
    ("Assinaturas", [
        "APPLE.COM", "APPLECOMBILL", "AMAZON PRIME", "AMAZONPRIME",
        "GOOGLE YOUTUB", "YOUTUBEPREMIUM", "ANTHROPIC", "CLAUDE SUB",
    ]),
    ("Compras Online", [
        "MERCADOLIVRE", "AMAZONMKTPLC", "AMAZON BR", "ALIEXPRESS", "SHOPEE", "*OLX",
    ]),
    ("Mercado", [
        "SUPERMERCADO", "MERCADO VIOLETA", "MINI EXTRA", "QUALITY SUPERMERCADO",
    ]),
    ("Transporte", [
        "POSTO", "RODOPOSTO", "UBER", "ALLPARK", "CASA DO OLEO", "MMG PARK", "BKD TERMINAL",
    ]),
    ("Saúde", [
        "DENTAL", "DROGASIL", "DROGARIA", "RAIA", "SOUSMILE", "SMILECLOUD",
        "WELLHUB", "FACIALCLASS", "CABELEIREIRO", "RD SAUDE", "*DRA ",
    ]),
    ("Lazer", [
        "CINEMARK", "CSFLOAT", "UNIMUSIC", "RODEIO", "BEST WESTERN", "FORMATURAS",
    ]),
    ("Educação", [
        "FIAP", "PAPELARIA",
    ]),
    ("Vestuário", [
        "INDITEX", "DECATHLON",
    ]),
    ("Moradia", [
        "LUMI PLANEJADOS", "LUMINI PLANEJADOS",
    ]),
    ("Serviços", [
        "CONTABILIZEI",
    ]),
    ("Alimentação", [
        "RESTAURANTE", "RESTA ", "PIZZARIA", "HAMBURGUER", "HAMBURGUERI", "BURGUER", "BURGER",
        "KFC", "OUTBACK", "CHURROS", "ACAI", "PICANHA", "GRILL", "BAR ", "CAFE", "PADARIA",
        "DOCES", "CONFEITARIA", "CHOCOLAT", "SORVETE", "SUSHI", "IFD*", "IFOOD", "PASTEL",
        "FRANBOI", "TASCA", "ESFIHA", "MILK SHAKE", "BUFFET", "BBQ", "COSTELAO", "COMERCIO DE ALIMEN",
        "LINDT", "BACIO DI LATTE", "99FOOD", "PAES E DOCES", "NAOKO",
    ]),
]


def _normalizar(nome: str) -> str:
    if not nome:
        return ""
    sem_acento = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode("ascii")
    return " ".join(sem_acento.upper().split())


def sugerir_categoria(nome_estabelecimento: str) -> str:
    """Heuristica de palavras-chave, usada so na seed inicial da aba
    'Categorias' - depois disso a planilha manda (ver scripts/seed_categorias.py)."""
    normalizado = _normalizar(nome_estabelecimento)
    for categoria, palavras_chave in REGRAS:
        chaves_normalizadas = [_normalizar(p) for p in palavras_chave]
        if any(chave in normalizado for chave in chaves_normalizadas):
            return categoria
    return NAO_CATEGORIZADO


def aplicar_categorias(df_transacoes: pd.DataFrame, df_categorias: pd.DataFrame) -> pd.DataFrame:
    """Left join por Estabelecimento; sem match -> Nao categorizado."""
    if df_categorias.empty:
        return df_transacoes.assign(Categoria=NAO_CATEGORIZADO)

    mapa = df_categorias.drop_duplicates(subset="Estabelecimento").set_index("Estabelecimento")["Categoria"]
    resultado = df_transacoes.copy()
    resultado["Categoria"] = resultado["Estabelecimento"].map(mapa).fillna(NAO_CATEGORIZADO)
    resultado.loc[resultado["Categoria"].str.strip() == "", "Categoria"] = NAO_CATEGORIZADO
    return resultado
