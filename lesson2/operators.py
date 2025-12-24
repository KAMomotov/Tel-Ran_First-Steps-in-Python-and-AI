"""
Операторы Python — лекционные примечания (коротко)

1) and / or (короткое замыкание + возвращают операнд, а не bool):
   - a and b -> если a "ложный" (falsy), вернёт a, иначе вернёт b
   - a or b -> если a "истинный" (truthy), вернёт a, иначе вернёт b
   Это удобно для "значение по умолчанию", но важно помнить: результат может быть НЕ bool.

2) is vs ==:
   - == сравнивает значения (value equality): a == b
   - is сравнивает идентичность объекта (same object): a is b
   Обычно:
   - для чисел/строк/кортежей почти всегда нужен ==
   - is используют для сравнения с None: x is None

3) Почему a < b не работает для complex:
   Complex числа в Python не имеют естественного порядка ("больше/меньше"),
   поэтому операторы <, >, <=, >= для complex вызывают TypeError.
   При этом == и != для complex работают (равенство по значению).

4) Битовые операции и двоичный вид:
   Для int полезно смотреть двоичное представление:
   - bin(x) -> строка вида '0b101010'
   Ниже в Bitwise.show_all() дополнительно печатается bin() для x/y и результата.
"""

from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping, Union

# ---- Типы ----
Real = Union[int, float]
Numeric = Union[int, float, complex]  # подходит для "+", "-", "*", "/", "**", но НЕ для "//" и "%"


# ---- Общая инфраструктура для show_all() ----
@dataclass(frozen=True)
class Operation:
    """Описывает одну операцию для вывода в show_all()."""
    template: str
    func: Callable[[], object]


class ShowAllMixin:
    """
    Миксин для единообразного show_all().

    Каждый класс определяет:
      - _operands()    -> значения для подстановки в шаблон
      - _operations()  -> список Operation(template, func)

    show_all() печатает:
      <выражение> -> <результат> (<тип>)

    Если операция падает (ZeroDivisionError, TypeError, ...),
    печатает:
      <выражение> -> <Ошибка>: <сообщение>
    """

    def _operands(self) -> Mapping[str, object]:
        raise NotImplementedError

    def _operations(self) -> Iterable[Operation]:
        raise NotImplementedError

    def _stringify(self, value: object) -> str:
        """Как показывать операнды в выражении. По умолчанию — str()."""
        return str(value)

    def _format_result(self, result: object) -> str:
        """Формат результата. Можно переопределять (например, для битовых)."""
        return f"{result} ({type(result).__name__})"

    def show_all(self) -> None:
        operand_strings = {k: self._stringify(v) for k, v in self._operands().items()}
        lines: list[str] = []

        for op in self._operations():
            expr = op.template.format(**operand_strings)
            try:
                result = op.func()
                lines.append(f"{expr} -> {self._format_result(result)}")
            except Exception as exc:
                lines.append(f"{expr} -> {type(exc).__name__}: {exc}")

        print("\n".join(lines))


# -------------------------
# 1) АРИФМЕТИКА
# -------------------------
@dataclass(frozen=True)
class Arithmetic(ShowAllMixin):
    """
    АРИФМЕТИКА / ARITHMETICS:
    "+"  – Оператор "сложения"                 | Addition operator
    "-"  – Оператор "вычитания"                | Subtraction operator
    "*"  – Оператор "умножения"                | Multiplication operator
    "/"  – Оператор "деления"                  | Division operator
    "**" – Оператор "возведения в степень"     | Power operator
    "//" – Оператор "целочисленного деления"   | Integer division operator
    "%"  – Оператор "деления по модулю"        | Modulo operator

    Примечание по типам:
    - +, -, *, /, ** поддерживают и complex
    - // и % для complex НЕ поддерживаются (будет TypeError)
    """
    a: Numeric
    b: Numeric

    def addition(self) -> Numeric:
        return self.a + self.b

    def subtraction(self) -> Numeric:
        return self.a - self.b

    def multiplication(self) -> Numeric:
        return self.a * self.b

    def division(self) -> complex | float:
        if self.b == 0:
            raise ZeroDivisionError('Нельзя делить на ноль (/)')  # для complex тоже релевантно
        return self.a / self.b

    def power(self) -> Numeric:
        return self.a ** self.b

    def integer_division(self) -> Real:
        if isinstance(self.a, complex) or isinstance(self.b, complex):
            raise TypeError("Оператор '//' не поддерживается для complex")
        if self.b == 0:
            raise ZeroDivisionError("Нельзя делить на ноль (//)")
        return self.a // self.b  # type: ignore[return-value]

    def modulo(self) -> Real:
        if isinstance(self.a, complex) or isinstance(self.b, complex):
            raise TypeError("Оператор '%' не поддерживается для complex")
        if self.b == 0:
            raise ZeroDivisionError("Нельзя делить на ноль (%)")
        return self.a % self.b  # type: ignore[return-value]

    def _operands(self) -> Mapping[str, object]:
        return {"a": self.a, "b": self.b}

    def _operations(self) -> Iterable[Operation]:
        return [
            Operation("{a} + {b}", self.addition),
            Operation("{a} - {b}", self.subtraction),
            Operation("{a} * {b}", self.multiplication),
            Operation("{a} / {b}", self.division),
            Operation("{a} ** {b}", self.power),
            Operation("{a} // {b}", self.integer_division),
            Operation("{a} % {b}", self.modulo),
        ]


# -------------------------
# 2) СРАВНЕНИЯ
# -------------------------
@dataclass(frozen=True)
class Comparison(ShowAllMixin):
    """
    СРАВНЕНИЯ / COMPARISONS:
    "<"  – Оператор "меньше"            | Less than operator
    ">"  – Оператор "больше"            | Greater than operator
    "<=" – Оператор "меньше или равно"  | Less than or equal operator
    ">=" – Оператор "больше или равно"  | Greater than or equal operator
    "==" – Оператор "равно"             | Equality operator
    "!=" – Оператор "не равно"          | Not equal operator

    Примечание по типам:
    - Упорядочивание (<, >, <=, >=) корректно для int/float (Real)
    - Для complex оно не определено (TypeError)
    """
    left: Real
    right: Real

    def lt(self) -> bool: return self.left < self.right
    def gt(self) -> bool: return self.left > self.right
    def le(self) -> bool: return self.left <= self.right
    def ge(self) -> bool: return self.left >= self.right
    def eq(self) -> bool: return self.left == self.right
    def ne(self) -> bool: return self.left != self.right

    def _operands(self) -> Mapping[str, object]:
        return {"a": self.left, "b": self.right}

    def _operations(self) -> Iterable[Operation]:
        return [
            Operation("{a} < {b}", self.lt),
            Operation("{a} > {b}", self.gt),
            Operation("{a} <= {b}", self.le),
            Operation("{a} >= {b}", self.ge),
            Operation("{a} == {b}", self.eq),
            Operation("{a} != {b}", self.ne),
        ]


# -------------------------
# 3) ПРИСВАИВАНИЕ (имитация без мутаций)
# -------------------------
@dataclass(frozen=True)
class Assignment(ShowAllMixin):
    """
    ПРИСВАИВАНИЕ / ASSIGNMENT (имитация, без мутаций):
    "="    – Оператор "присваивания"                 | Assignment operator
    "+="   – Присваивание с "сложением"              | Add and assign
    "-="   – Присваивание с "вычитанием"             | Subtract and assign
    "*="   – Присваивание с "умножением"             | Multiply and assign
    "/="   – Присваивание с "делением"               | Divide and assign
    "//="  – Присваивание с "целочисленным делением" | Floor-divide and assign
    "%="   – Присваивание с "делением по модулю"     | Modulo and assign
    "**="  – Присваивание с "возведением в степень"  | Power and assign
    "&="   – Присваивание с "AND"                    | Bitwise AND and assign
    "|="   – Присваивание с "OR"                     | Bitwise OR and assign
    "^="   – Присваивание с "XOR"                    | Bitwise XOR and assign
    "<<="  – Присваивание с "сдвигом влево"          | Left shift and assign
    ">>="  – Присваивание с "сдвигом вправо"         | Right shift and assign

    Почему Any:
    - операторы присваивания применимы к разным типам (int, str, list, set, …).
    - поведение зависит от типа (изменяемый/неизменяемый объект).
    Здесь мы возвращаем "значение, которое оказалось бы в переменной".
    """
    value: Any
    other: Any

    def assign(self) -> Any: return self.other
    def iadd(self) -> Any: return self.value + self.other
    def isub(self) -> Any: return self.value - self.other
    def imul(self) -> Any: return self.value * self.other
    def itruediv(self) -> Any: return self.value / self.other
    def ifloordiv(self) -> Any: return self.value // self.other
    def imod(self) -> Any: return self.value % self.other
    def ipow(self) -> Any: return self.value ** self.other
    def iand(self) -> Any: return self.value & self.other
    def ior(self) -> Any: return self.value | self.other
    def ixor(self) -> Any: return self.value ^ self.other
    def ilshift(self) -> Any: return self.value << self.other
    def irshift(self) -> Any: return self.value >> self.other

    def _stringify(self, value: object) -> str:
        return repr(value)

    def _operands(self) -> Mapping[str, object]:
        return {"a": self.value, "b": self.other}

    def _operations(self) -> Iterable[Operation]:
        return [
            Operation("{a} = {b}", self.assign),
            Operation("{a} += {b}", self.iadd),
            Operation("{a} -= {b}", self.isub),
            Operation("{a} *= {b}", self.imul),
            Operation("{a} /= {b}", self.itruediv),
            Operation("{a} //= {b}", self.ifloordiv),
            Operation("{a} %= {b}", self.imod),
            Operation("{a} **= {b}", self.ipow),
            Operation("{a} &= {b}", self.iand),
            Operation("{a} |= {b}", self.ior),
            Operation("{a} ^= {b}", self.ixor),
            Operation("{a} <<= {b}", self.ilshift),
            Operation("{a} >>= {b}", self.irshift),
        ]

    def _format_result(self, result: object) -> str:
        return f"{result!r} ({type(result).__name__})"


# -------------------------
# 4) ЛОГИКА
# -------------------------
@dataclass(frozen=True)
class Logical(ShowAllMixin):
    """
    ЛОГИКА / LOGICAL:
    "and" – Логическое И (короткое замыкание)   | Logical AND (short-circuit)
    "or"  – Логическое ИЛИ (короткое замыкание) | Logical OR (short-circuit)
    "not" – Логическое НЕ                      | Logical NOT

    Важно: `and/or` возвращают один из операндов (Any), а не bool.
    """
    a: Any
    b: Any

    def and_op(self) -> Any: return self.a and self.b
    def or_op(self) -> Any: return self.a or self.b
    def not_a(self) -> bool: return not self.a
    def not_b(self) -> bool: return not self.b

    def _stringify(self, value: object) -> str:
        return repr(value)

    def _operands(self) -> Mapping[str, object]:
        return {"a": self.a, "b": self.b}

    def _operations(self) -> Iterable[Operation]:
        return [
            Operation("{a} and {b}", self.and_op),
            Operation("{a} or {b}", self.or_op),
            Operation("not {a}", self.not_a),
            Operation("not {b}", self.not_b),
        ]

    def _format_result(self, result: object) -> str:
        return f"{result!r} ({type(result).__name__})"


# -------------------------
# 5) ПРИНАДЛЕЖНОСТЬ
# -------------------------
@dataclass(frozen=True)
class Membership(ShowAllMixin):
    """
    ПРИНАДЛЕЖНОСТЬ / MEMBERSHIP:
    "in"     – Оператор "входит в"     | Membership operator
    "not in" – Оператор "не входит в" | Not membership operator

    Почему Any:
    - item/container могут быть разными типами (строки, списки, множества, dict, …).
    """
    item: Any
    container: Any

    def contains(self) -> bool: return self.item in self.container
    def not_contains(self) -> bool: return self.item not in self.container

    def _stringify(self, value: object) -> str:
        return repr(value)

    def _operands(self) -> Mapping[str, object]:
        return {"x": self.item, "c": self.container}

    def _operations(self) -> Iterable[Operation]:
        return [
            Operation("{x} in {c}", self.contains),
            Operation("{x} not in {c}", self.not_contains),
        ]

    def _format_result(self, result: object) -> str:
        return f"{result!r} ({type(result).__name__})"


# -------------------------
# 6) ТОЖДЕСТВЕННОСТЬ
# -------------------------
@dataclass(frozen=True)
class Identity(ShowAllMixin):
    """
    ТОЖДЕСТВЕННОСТЬ / IDENTITY:
    "is"     – Оператор "тот же объект"     | Identity operator
    "is not" – Оператор "не тот же объект"  | Negated identity operator

    Важно: `is` — про идентичность объекта, `==` — про равенство значений.
    """
    a: object
    b: object

    def is_(self) -> bool: return self.a is self.b
    def is_not(self) -> bool: return self.a is not self.b

    def _stringify(self, value: object) -> str:
        return repr(value)

    def _operands(self) -> Mapping[str, object]:
        return {"a": self.a, "b": self.b}

    def _operations(self) -> Iterable[Operation]:
        return [
            Operation("{a} is {b}", self.is_),
            Operation("{a} is not {b}", self.is_not),
        ]

    def _format_result(self, result: object) -> str:
        return f"{result!r} ({type(result).__name__})"


# -------------------------
# 7) БИТОВЫЕ ОПЕРАЦИИ
# -------------------------
@dataclass(frozen=True)
class Bitwise(ShowAllMixin):
    """
    БИТОВЫЕ ОПЕРАЦИИ / BITWISE:
    "&"   – Побитовое И (AND)                 | Bitwise AND
    "|"   – Побитовое ИЛИ (OR)                | Bitwise OR
    "^"   – Побитовое исключающее ИЛИ (XOR)   | Bitwise XOR
    "~"   – Побитовое НЕ (инверсия)           | Bitwise NOT (invert)
    "<<"  – Сдвиг влево                       | Left shift
    ">>"  – Сдвиг вправо                      | Right shift

    Обычно применяются к int.
    """
    x: int
    y: int

    def and_(self) -> int: return self.x & self.y
    def or_(self) -> int: return self.x | self.y
    def xor(self) -> int: return self.x ^ self.y
    def invert_x(self) -> int: return ~self.x
    def lshift(self) -> int: return self.x << self.y
    def rshift(self) -> int: return self.x >> self.y

    def _operands(self) -> Mapping[str, object]:
        return {"x": self.x, "y": self.y}

    def _operations(self) -> Iterable[Operation]:
        return [
            Operation("{x} & {y}", self.and_),
            Operation("{x} | {y}", self.or_),
            Operation("{x} ^ {y}", self.xor),
            Operation("~{x}", self.invert_x),
            Operation("{x} << {y}", self.lshift),
            Operation("{x} >> {y}", self.rshift),
        ]

    def show_all(self) -> None:
        # Чуть "лекционнее": покажем двоичный вид операндов один раз,
        # а затем — операции, где результат тоже в bin().
        print(f"x = {self.x} ({bin(self.x)})")
        print(f"y = {self.y} ({bin(self.y)})")
        super().show_all()

    def _format_result(self, result: object) -> str:
        # Для битовых результатов полезно показывать bin().
        if isinstance(result, int):
            return f"{result} ({type(result).__name__}), bin={bin(result)}"
        return super()._format_result(result)


# -------------------------
# Mini demo (для лекции)
# -------------------------
def _title(text: str) -> None:
    line = "=" * len(text)
    print(f"\n{line}\n{text}\n{line}")


if __name__ == "__main__":
    _title("ARITHMETIC (int/float)")
    Arithmetic(10, 3).show_all()

    _title("ARITHMETIC (complex: // и % не работают)")
    Arithmetic(2 + 3j, 1 + 1j).show_all()

    _title("COMPARISON")
    Comparison(10, 3).show_all()

    _title("ASSIGNMENT (имитация)")
    Assignment(10, 3).show_all()
    _title("ASSIGNMENT (строки: += работает, -= нет)")
    Assignment("Py", "thon").show_all()

    _title("LOGICAL (and/or возвращают операнд)")
    Logical("", "fallback").show_all()
    Logical("value", "fallback").show_all()

    _title("MEMBERSHIP")
    Membership("a", "cat").show_all()
    Membership(3, [1, 2, 3]).show_all()

    _title("IDENTITY (is vs ==)")
    x = [1, 2, 3]
    y = [1, 2, 3]
    z = x
    Identity(x, y).show_all()  # обычно: is False, == True (но == здесь не показываем)
    Identity(x, z).show_all()  # is True

    _title("BITWISE (bin() в выводе)")
    Bitwise(10, 3).show_all()
