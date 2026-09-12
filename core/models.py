import re
from datetime import date

HEADER_DB_TRANSACOES = ["Banco", "Periodo", "Data", "Estabelecimento", "Tipo", "Parcela", "Valor"]
HEADER_CATEGORIAS = ["Estabelecimento", "Categoria"]

MESES_PT_BR = {
    "janeiro": 1, "fevereiro": 2,
    "marco": 3, "março": 3,
    "abril": 4, "maio": 5, "junho": 6, "julho": 7,
    "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12,
}

_VALOR_RE = re.compile(r"^-?[\d.]+(,\d+)?$")


def periodo_para_data(periodo: str) -> date | None:
    """'Março/2026' -> date(2026, 3, 1). None se o texto nao for reconhecido."""
    if not periodo:
        return None
    partes = periodo.strip().lstrip("'").split("/")
    if len(partes) != 2:
        return None

    mes_nome, ano_str = partes[0].strip().lower(), partes[1].strip()
    mes = MESES_PT_BR.get(mes_nome)
    if mes is None or not ano_str.isdigit():
        return None
    return date(int(ano_str), mes, 1)


def parse_valor_brl(valor: str) -> float:
    """'106,43' -> 106.43 ; '1.234,56' -> 1234.56. Retorna 0.0 se ilegivel."""
    if valor is None:
        return 0.0
    if isinstance(valor, (int, float)):
        return float(valor)

    texto = valor.strip()
    if not texto or not _VALOR_RE.match(texto):
        return 0.0

    return float(texto.replace(".", "").replace(",", "."))
