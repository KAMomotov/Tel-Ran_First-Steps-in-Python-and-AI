import pytest

from lesson2.operators import (
    Arithmetic,
    Comparison,
    Assignment,
    Logical,
    Membership,
    Identity,
    Bitwise,
)


# -------------------------
# Arithmetic: методы
# -------------------------
def test_arithmetic_basic_methods():
    a = Arithmetic(10, 3)
    assert a.addition() == 13
    assert a.subtraction() == 7
    assert a.multiplication() == 30
    assert a.division() == pytest.approx(10 / 3)
    assert a.power() == 1000
    assert a.integer_division() == 3
    assert a.modulo() == 1


def test_arithmetic_division_by_zero_raises():
    a = Arithmetic(10, 0)
    with pytest.raises(ZeroDivisionError):
        _ = a.division()


def test_arithmetic_integer_division_by_zero_raises():
    a = Arithmetic(10, 0)
    with pytest.raises(ZeroDivisionError):
        _ = a.integer_division()


def test_arithmetic_modulo_by_zero_raises():
    a = Arithmetic(10, 0)
    with pytest.raises(ZeroDivisionError):
        _ = a.modulo()


def test_arithmetic_complex_floor_and_mod_raise_typeerror():
    a = Arithmetic(2 + 3j, 1 + 1j)
    with pytest.raises(TypeError):
        _ = a.integer_division()
    with pytest.raises(TypeError):
        _ = a.modulo()


# -------------------------
# Arithmetic: show_all output
# -------------------------
def test_arithmetic_show_all_prints_lines(capsys):
    Arithmetic(10, 3).show_all()
    out = capsys.readouterr().out.strip().splitlines()

    # Должны быть все 7 операций
    assert len(out) == 7

    assert any("10 + 3" in line and "-> 13 (int)" in line for line in out)
    assert any("10 - 3" in line and "-> 7 (int)" in line for line in out)
    assert any("10 * 3" in line and "-> 30 (int)" in line for line in out)
    assert any("10 / 3" in line and "->" in line for line in out)
    assert any("10 ** 3" in line and "-> 1000 (int)" in line for line in out)
    assert any("10 // 3" in line and "-> 3 (int)" in line for line in out)
    assert any("10 % 3" in line and "-> 1 (int)" in line for line in out)


def test_arithmetic_show_all_complex_includes_typeerror_lines(capsys):
    Arithmetic(2 + 3j, 1 + 1j).show_all()
    out = capsys.readouterr().out

    # // и % должны отразиться как TypeError
    assert "-> TypeError:" in out
    assert "//" in out
    assert "%" in out


# -------------------------
# Comparison: методы + show_all
# -------------------------
def test_comparison_methods():
    c = Comparison(10, 3)
    assert c.lt() is False
    assert c.gt() is True
    assert c.le() is False
    assert c.ge() is True
    assert c.eq() is False
    assert c.ne() is True


def test_comparison_show_all_output(capsys):
    Comparison(10, 3).show_all()
    out = capsys.readouterr().out.strip().splitlines()
    assert len(out) == 6
    assert any("10 > 3 -> True (bool)" in line for line in out)
    assert any("10 == 3 -> False (bool)" in line for line in out)


# -------------------------
# Assignment: методы + show_all + ошибки
# -------------------------
def test_assignment_basic_numeric():
    a = Assignment(10, 3)
    assert a.assign() == 3
    assert a.iadd() == 13
    assert a.isub() == 7
    assert a.imul() == 30


def test_assignment_string_iadd_ok_and_isub_fails_in_show_all(capsys):
    # "Py" += "thon" ок, но "Py" -= "thon" даст TypeError
    Assignment("Py", "thon").show_all()
    out = capsys.readouterr().out

    assert "'Py' += 'thon' -> 'Python' (str)" in out
    # Ошибка на -=
    assert "'Py' -= 'thon' -> TypeError:" in out


# -------------------------
# Logical: поведение and/or
# -------------------------
@pytest.mark.parametrize(
    "a,b,expected_and,expected_or",
    [
        ("", "fallback", "", "fallback"),
        ("value", "fallback", "fallback", "value"),
        (0, 5, 0, 5),
        (7, 0, 0, 7),
    ],
)
def test_logical_and_or_return_operands(a, b, expected_and, expected_or):
    l = Logical(a, b)
    assert l.and_op() == expected_and
    assert l.or_op() == expected_or


def test_logical_show_all_contains_repr(capsys):
    Logical("", "fallback").show_all()
    out = capsys.readouterr().out
    # repr должны быть с кавычками
    assert "'' and 'fallback'" in out
    assert "'' or 'fallback'" in out


# -------------------------
# Membership
# -------------------------
def test_membership_methods():
    m = Membership(3, [1, 2, 3])
    assert m.contains() is True
    assert m.not_contains() is False


def test_membership_show_all_output(capsys):
    Membership("a", "cat").show_all()
    out = capsys.readouterr().out
    assert "'a' in 'cat' -> True (bool)" in out
    assert "'a' not in 'cat' -> False (bool)" in out


# -------------------------
# Identity
# -------------------------
def test_identity_is_and_is_not():
    x = [1, 2]
    y = [1, 2]
    z = x

    assert Identity(x, y).is_() is False
    assert Identity(x, y).is_not() is True

    assert Identity(x, z).is_() is True
    assert Identity(x, z).is_not() is False


def test_identity_show_all_output(capsys):
    x = []
    y = x
    Identity(x, y).show_all()
    out = capsys.readouterr().out
    assert "is" in out
    assert "-> True (bool)" in out


# -------------------------
# Bitwise: методы + show_all (bin)
# -------------------------
def test_bitwise_methods():
    b = Bitwise(10, 3)
    assert b.and_() == (10 & 3)
    assert b.or_() == (10 | 3)
    assert b.xor() == (10 ^ 3)
    assert b.invert_x() == (~10)
    assert b.lshift() == (10 << 3)
    assert b.rshift() == (10 >> 3)


def test_bitwise_show_all_includes_bin(capsys):
    Bitwise(10, 3).show_all()
    out = capsys.readouterr().out

    # первые "лекционные" строки
    assert "x = 10 (0b1010)" in out
    assert "y = 3 (0b11)" in out

    # результаты должны содержать bin=
    assert "bin=0b" in out

    # пример конкретной операции
    assert "10 & 3 ->" in out
