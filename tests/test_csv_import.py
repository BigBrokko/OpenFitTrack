import pytest
from sqlmodel import select

from core.csv_import import (
    ColumnMapping,
    foods_from_table,
    guess_mapping,
    parse_number,
    read_csv_table,
)
from core.foods import upsert_foods
from core.models import Food

MAPPING = ColumnMapping(name="name", kcal="kcal", protein_g="protein", carbs_g="carbs", fat_g="fat")
HEADER = "name,kcal,protein,carbs,fat\n"


def table(csv_text: str):
    return read_csv_table(csv_text.encode("utf-8")).frame


# --- Reading -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("header", "delimiter"),
    [("a,b,c", ","), ("a;b;c", ";"), ("a|b|c", "|"), ("a\tb\tc", "\t"), ('"x, y";b;c', ";")],
)
def test_detects_the_delimiter(header, delimiter):
    result = read_csv_table(f"{header}\n1,2,3\n".encode())

    assert result.delimiter == delimiter


def test_reads_a_semicolon_file_with_decimal_commas():
    result = read_csv_table(b"name;kcal;protein\nKwark;51;8,4\n")

    assert list(result.frame.columns) == ["name", "kcal", "protein"]
    assert result.frame.iloc[0].tolist() == ["Kwark", "51", "8,4"]


def test_falls_back_to_latin_1_and_strips_a_bom():
    latin = "name,kcal\nCrème,50\n".encode("latin-1")
    bom = b"\xef\xbb\xbfname,kcal\nTest,50\n"

    assert read_csv_table(latin).encoding == "latin-1"
    assert read_csv_table(latin).frame.iloc[0, 0] == "Crème"
    assert list(read_csv_table(bom).frame.columns) == ["name", "kcal"]


@pytest.mark.parametrize("data", [b"", b"   \n  "])
def test_empty_file_is_rejected(data):
    with pytest.raises(ValueError):
        read_csv_table(data)


def test_header_only_file_gives_an_empty_table():
    assert read_csv_table(b"name,kcal\n").frame.empty


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("12", 12.0),
        ("12.5", 12.5),
        ("12,5", 12.5),
        ("1.234,5", 1234.5),
        ("1,234.5", 1234.5),
        (" 7 ", 7.0),
        ("", None),
        ("tr", None),
        ("<0.1", None),
        ("nan", None),
        ("inf", None),
    ],
)
def test_parse_number(text, expected):
    assert parse_number(text) == expected


# --- Guessing the mapping ------------------------------------------------------


def test_guesses_english_headers():
    guess = guess_mapping(["id", "description", "Energy (kcal)", "Protein", "Carbohydrate", "Fat"])

    assert guess["name"] == "description"
    assert guess["kcal"] == "Energy (kcal)"
    assert guess["protein_g"] == "Protein"
    assert guess["carbs_g"] == "Carbohydrate"
    assert guess["fat_g"] == "Fat"
    assert guess["source_id"] == "id"


def test_guesses_dutch_headers():
    guess = guess_mapping(["Naam", "Calorieën", "Eiwit (g)", "Koolhydraten (g)", "Vet (g)"])

    assert guess["name"] == "Naam"
    assert guess["kcal"] == "Calorieën"
    assert guess["fat_g"] == "Vet (g)"


def test_guesses_the_nevo_headers():
    columns = [
        "Voedingsmiddelgroep",
        "Food group",
        "NEVO-code",
        "Voedingsmiddelnaam/Dutch food name",
        "Engelse naam/Food name",
        "ENERCJ (kJ)",
        "ENERCC (kcal)",
        "PROT (g)",
        "PROTPL (g)",
        "FAT (g)",
        "FASAT (g)",
        "CHO (g)",
        "SUGAR (g)",
        "CHORL (mg)",
    ]

    assert guess_mapping(columns) == {
        "name": "Voedingsmiddelnaam/Dutch food name",
        "kcal": "ENERCC (kcal)",
        "kj": "ENERCJ (kJ)",
        "protein_g": "PROT (g)",
        "carbs_g": "CHO (g)",
        "fat_g": "FAT (g)",
        "source_id": "NEVO-code",
    }


def test_guess_skips_sub_values_like_saturated_fat_and_sugars():
    guess = guess_mapping(["saturated-fat_100g", "fat_100g", "sugars_100g", "carbohydrates_100g"])

    assert guess["fat_g"] == "fat_100g"
    assert guess["carbs_g"] == "carbohydrates_100g"


def test_guess_leaves_unknown_fields_empty():
    assert set(guess_mapping(["foo", "bar"]).values()) == {None}


# --- Converting ----------------------------------------------------------------


def test_converts_rows_to_foods():
    frame = table(HEADER + "Quark,51,8.4,3.8,0\nBanana,90,1,20,0.3\n")

    parsed = foods_from_table(frame, MAPPING, "mylist")

    assert [f.name for f in parsed.foods] == ["Quark", "Banana"]
    assert parsed.skipped == []
    quark = parsed.foods[0]
    assert (quark.source, quark.source_id, quark.kcal, quark.protein_g) == ("mylist", None, 51, 8.4)


def test_decimal_comma_values_are_understood():
    frame = read_csv_table(b"name;kcal;protein;carbs;fat\nKwark;51;8,4;3,8;0\n").frame

    (food,) = foods_from_table(frame, MAPPING, "mylist").foods

    assert (food.protein_g, food.carbs_g) == (8.4, 3.8)


def test_source_id_is_used_when_mapped():
    frame = table("id,name,kcal,protein,carbs,fat\n7,Quark,51,8.4,3.8,0\n")
    mapping = ColumnMapping("name", "protein", "carbs", "fat", kcal="kcal", source_id="id")

    (food,) = foods_from_table(frame, mapping, "mylist").foods

    assert food.source_id == "7"


def test_kj_is_used_when_kcal_is_empty():
    frame = table("name,kcal,kj,protein,carbs,fat\nA,,418.4,1,1,1\nB,100,999,1,1,1\n")
    mapping = ColumnMapping("name", "protein", "carbs", "fat", kcal="kcal", kj="kj")

    a, b = foods_from_table(frame, mapping, "mylist").foods

    assert a.kcal == pytest.approx(100)
    assert b.kcal == 100  # an existing kcal value wins over kJ


def test_kj_alone_is_enough():
    frame = table("name,kj,protein,carbs,fat\nA,418.4,1,1,1\n")
    mapping = ColumnMapping("name", "protein", "carbs", "fat", kj="kj")

    assert foods_from_table(frame, mapping, "mylist").foods[0].kcal == pytest.approx(100)


@pytest.mark.parametrize(
    ("row", "reason"),
    [
        (",50,1,1,1", "empty name"),
        ("A,,1,1,1", "kcal"),
        ("A,50,,1,1", "protein"),
        ("A,50,1,tr,1", "carbs"),
        ("A,-5,1,1,1", "negative"),
        ("A,50,1,1,-1", "negative"),
        ("A,2000,1,1,1", "kJ"),
        ("A,500,50,40,20", "more than 100 g"),
    ],
)
def test_invalid_rows_are_skipped_with_a_reason(row, reason):
    frame = table(HEADER + f"{row}\nGood,50,1,1,1\n")

    parsed = foods_from_table(frame, MAPPING, "mylist")

    assert [f.name for f in parsed.foods] == ["Good"]
    (skipped,) = parsed.skipped
    assert skipped.row == 2  # the header is line 1
    assert reason in skipped.reason


def test_macros_slightly_above_100_from_rounding_are_accepted():
    frame = table(HEADER + "A,400,40,50.5,10\n")

    assert len(foods_from_table(frame, MAPPING, "mylist").foods) == 1


@pytest.mark.parametrize("source", ["", "  ", "manual", "Manual"])
def test_reserved_or_empty_source_is_rejected(source):
    with pytest.raises(ValueError):
        foods_from_table(table(HEADER), MAPPING, source)


def test_mapping_needs_kcal_or_kj():
    mapping = ColumnMapping("name", "protein", "carbs", "fat")

    with pytest.raises(ValueError, match="kcal"):
        foods_from_table(table("name,protein,carbs,fat\n"), mapping, "mylist")


def test_mapping_to_a_column_that_does_not_exist_is_rejected():
    mapping = ColumnMapping("nope", "protein", "carbs", "fat", kcal="kcal")

    with pytest.raises(ValueError, match="nope"):
        foods_from_table(table(HEADER), mapping, "mylist")


# --- Upsert --------------------------------------------------------------------


def import_text(session, text, mapping=MAPPING, source="mylist"):
    parsed = foods_from_table(table(text), mapping, source)
    return upsert_foods(session, parsed.foods, source)


def test_importing_twice_adds_nothing_the_second_time(session):
    text = HEADER + "Quark,51,8.4,3.8,0\nBanana,90,1,20,0.3\n"

    first = import_text(session, text)
    second = import_text(session, text)

    assert (first.added, first.updated) == (2, 0)
    assert (second.added, second.updated) == (0, 2)
    assert len(session.exec(select(Food)).all()) == 2


def test_names_are_matched_ignoring_case_without_an_id(session):
    import_text(session, HEADER + "Quark,51,8.4,3.8,0\n")

    result = import_text(session, HEADER + "QUARK,60,9,4,1\n")

    assert (result.added, result.updated) == (0, 1)
    assert session.exec(select(Food)).one().kcal == 60


def test_ids_are_used_to_update_a_renamed_food(session):
    mapping = ColumnMapping("name", "protein", "carbs", "fat", kcal="kcal", source_id="id")
    import_text(session, "id,name,kcal,protein,carbs,fat\n1,Quark,51,8.4,3.8,0\n", mapping)

    import_text(session, "id,name,kcal,protein,carbs,fat\n1,Skyr,60,11,4,0\n", mapping)

    food = session.exec(select(Food)).one()
    assert (food.name, food.kcal) == ("Skyr", 60)


def test_the_same_food_twice_in_one_file_is_added_once(session):
    result = import_text(session, HEADER + "Quark,51,8,4,0\nquark,60,9,4,1\n")

    assert (result.added, result.updated) == (1, 1)
    assert session.exec(select(Food)).one().kcal == 60


def test_other_sources_and_manual_foods_are_left_alone(session):
    session.add(Food(name="Quark", source="manual", kcal=1, protein_g=1, carbs_g=1, fat_g=0))
    session.add(Food(name="Quark", source="other", kcal=2, protein_g=1, carbs_g=1, fat_g=0))
    session.commit()

    import_text(session, HEADER + "Quark,51,8.4,3.8,0\n")

    by_source = {f.source: f.kcal for f in session.exec(select(Food)).all()}
    assert by_source == {"manual": 1, "other": 2, "mylist": 51}


def test_upsert_rejects_foods_of_another_source(session):
    food = Food(name="X", source="a", kcal=1, protein_g=1, carbs_g=1, fat_g=0)

    with pytest.raises(ValueError):
        upsert_foods(session, [food], "b")
