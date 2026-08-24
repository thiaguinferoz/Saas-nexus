import io

import pytest
from openpyxl import Workbook

from app.routers.catalog import parse_price, spreadsheet_rows


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (12.5, "12.50"),
        ("R$ 1.234,56", "1234.56"),
        ("1,234.56", "1234.56"),
        ("1.234", "1234.00"),
        ("19,90", "19.90"),
    ],
)
def test_parse_price_recognizes_excel_and_brazilian_values(raw: object, expected: str) -> None:
    assert str(parse_price(raw)) == expected


def test_xlsx_finds_table_after_title_and_common_commercial_headers() -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["CATÁLOGO DE PRODUTOS"])
    sheet.append([])
    sheet.append(["Código do produto", "Nome do produto", "Preço de venda", "Grupo"])
    sheet.append([101, "Produto teste", 29.9, "Geral"])
    output = io.BytesIO()
    workbook.save(output)

    rows = spreadsheet_rows("catalogo.xlsx", output.getvalue())

    assert len(rows) == 1
    row_number, row = rows[0]
    assert row_number == 4
    assert row["codigodoproduto"] == 101
    assert row["nomedoproduto"] == "Produto teste"
    assert row["precodevenda"] == 29.9


def test_semicolon_csv_recognizes_value_with_currency_header() -> None:
    rows = spreadsheet_rows(
        "catalogo.csv",
        "Produto;Valor (R$);Categoria\nConsulta;150,00;Serviços\n".encode(),
    )

    assert len(rows) == 1
    assert rows[0][1]["valorr"] == "150,00"
