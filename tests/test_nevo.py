import pytest
from sqlmodel import select

from core.models import Food
from core.nevo import import_foods, load_nevo

HEADER = (
    '"NEVO-code"|"Voedingsmiddelnaam/Dutch food name"|"Hoeveelheid/Quantity"|'
    '"ENERCJ (kJ)"|"ENERCC (kcal)"|"PROT (g)"|"CHO (g)"|"FAT (g)"'
)


def write_csv(path, rows: list[str]):
    path.write_text("\n".join([HEADER, *rows]) + "\n", encoding="utf-8")
    return path


def test_load_parses_decimal_comma_and_columns(tmp_path):
    csv = write_csv(tmp_path / "nevo.csv", ["306|Kwark halfvolle|per 100g|323|77|7,5|4|3,2"])

    foods, skipped = load_nevo(csv)

    assert skipped == 0
    assert len(foods) == 1
    food = foods[0]
    assert food.name == "Kwark halfvolle"
    assert food.source == "nevo"
    assert food.source_id == "306"
    assert (food.kcal, food.protein_g, food.carbs_g, food.fat_g) == (77.0, 7.5, 4.0, 3.2)


def test_load_skips_per_100ml_and_missing_values(tmp_path):
    csv = write_csv(
        tmp_path / "nevo.csv",
        [
            "1|Aardappelen rauw|per 100g|371|88|2|19|0",
            "2|Babymelk p 100 ml|per 100ml|280|67|1,3|7,5|3,5",
            "3|Onbekend|per 100g|100|24||5|1",
        ],
    )

    foods, skipped = load_nevo(csv)

    assert [f.source_id for f in foods] == ["1"]
    assert skipped == 2


def test_load_derives_kcal_from_kj_when_missing(tmp_path):
    csv = write_csv(tmp_path / "nevo.csv", ["1|Test|per 100g|418,4||1|1|1"])

    foods, _ = load_nevo(csv)

    assert foods[0].kcal == pytest.approx(100.0)


def test_import_is_idempotent_and_updates(session, tmp_path):
    csv = write_csv(tmp_path / "nevo.csv", ["1|Kwark|per 100g|217|51|8,4|3,8|0"])
    foods, _ = load_nevo(csv)

    first = import_foods(session, foods)
    second = import_foods(session, load_nevo(csv)[0])

    assert (first.added, first.updated) == (1, 0)
    assert (second.added, second.updated) == (0, 1)
    assert len(session.exec(select(Food)).all()) == 1


def test_import_updates_changed_values_and_keeps_manual_foods(session, tmp_path):
    session.add(
        Food(name="Eigen recept", source="manual", kcal=100, protein_g=5, carbs_g=10, fat_g=2)
    )
    session.commit()
    csv = write_csv(tmp_path / "nevo.csv", ["1|Kwark|per 100g|217|51|8,4|3,8|0"])
    import_foods(session, load_nevo(csv)[0])

    csv = write_csv(tmp_path / "nevo2.csv", ["1|Kwark magere|per 100g|217|55|8,4|3,8|0"])
    import_foods(session, load_nevo(csv)[0])

    nevo = session.exec(select(Food).where(Food.source == "nevo")).one()
    assert (nevo.name, nevo.kcal) == ("Kwark magere", 55.0)
    assert session.exec(select(Food).where(Food.source == "manual")).one().name == "Eigen recept"
