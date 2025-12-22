"""
Учебный модуль к занятию №1 курса Tel-Tan
«Первые шаги в Python и Искусственном интеллекте».

Тема занятия:
    - основы Python;
    - переменные;
    - операции ввода и вывода данных.

Назначение модуля
-----------------
В стандартном Python за ввод и вывод чаще всего отвечают встроенные функции
input() и print(). Эти функции не «магические»: под капотом они работают с
потоками ввода/вывода.

Этот модуль реализует две функции — stdin() и stdout() — как учебные аналоги
input() и print(), но через sys.stdin / sys.stdout и интерфейс текстовых потоков
(TextIO). Это позволяет:
    - увидеть, как устроен ввод/вывод на уровне потоков;
    - научиться отделять источник ввода от места вывода;
    - писать тестируемый код, где ввод/вывод можно подменять (например, на StringIO).

Что внутри
----------
stdout(...)
    Аналог print(). Преобразует аргументы в строки, соединяет их через sep,
    добавляет end и записывает результат в указанный текстовый поток.

stdin(...)
    Аналог input(). Выводит приглашение в REPL-стиле и читает одну строку из
    указанного текстового потока.

Ключевые особенности
--------------------
1) Поддержка произвольных потоков TextIO
   - stdin(..., file=...) читает из переданного потока (например, StringIO).
   - stdin(..., out=...) печатает приглашение в переданный поток.
   - stdout(..., file=...) печатает в переданный поток.

2) Поведение stdin() при EOF
   Если readline() возвращает пустую строку '', возбуждается EOFError, также
пробрасывается KeyboardInterrupt (аналогично input()).

3) Обработка переводов строк
   stdin() удаляет ровно один завершающий символ '\\n' и, при необходимости,
   символ '\\r' перед ним (случай Windows CRLF: '\\r\\n').

Важно: отличие от input(prompt)
------------------------------
stdin() специально печатает приглашение в REPL-стиле:
    - если prompt задан: "{prompt}\\n>>> "
    - если prompt пустой: ">>> "
Это сделано как учебный пример «интерактивного ввода», и потому поведение
не является полной копией input(prompt), который печатает prompt без '\\n'.

Примеры использования
---------------------
Обычное использование (консоль):

    name = stdin("Введите имя")
    stdout("Привет,", name)

Тестирование / подмена потоков (без реальной консоли):

    import io
    fake_in = io.StringIO("42\\n")
    fake_out = io.StringIO()

    value = stdin("Введите число", file=fake_in, out=fake_out)
    stdout("Введено:", value, file=fake_out)

    assert value == "42"
    assert fake_out.getvalue() == "Введите число\\n>>> Введено: 42\\n"

Рекомендации по изучению
------------------------
- Посмотрите на sys.stdin и sys.stdout (это объекты потоков).
- Поэкспериментируйте с параметрами sep/end/flush.
- Попробуйте направить вывод в файл или в io.StringIO().
- Запустите pytest-тесты, чтобы увидеть, какой контракт функций мы фиксируем.

Версия: учебная
Автор/курс: Tel-Ran, «Первые шаги в Python и Искусственном интеллекте»
Переработал во время занятия: @KAMomotov
"""
import sys
from typing import TextIO


def stdin(
        prompt: str = "",
        *,
        file: TextIO | None = None,
        out: TextIO | None = None,
        flush: bool = True
) -> str:
    """
    Аналог input(), читающий одну строку из текстового потока.

    В отличие от input(), по умолчанию выводит приглашение в REPL-стиле:
        - если prompt задан: "{prompt}\\n>>> "
        - если prompt пустой: ">>> "

    :param prompt: Текст приглашения.
    :param file: Поток ввода (readline() -> str). По умолчанию sys.stdin.
    :param out: Поток для вывода приглашения. По умолчанию sys.stdout.
    :param flush: Если True, делает flush() после печати приглашения.

    :return: Считанная строка без завершающего '\\n' и (при наличии) '\\r'.

    :raises EOFError: Если достигнут EOF (readline() вернул '').
    :raises KeyboardInterrupt: Пробрасывается (как у input()).
    """
    if file is None:
        file = sys.stdin
    if out is None:
        out = sys.stdout

    prompt_text = (prompt + '\n>>>') if prompt else '>>>'
    stdout(prompt_text, end=" ", file=out, flush=flush)

    line = file.readline()

    if line == '':
        raise EOFError

    if line.endswith('\n'):
        line = line[:-1]
        if line.endswith('\r'):
            line = line[:-1]

    return line


def stdout(
        *args: object,
        sep: str = ' ',
        end: str = '\n',
        file: TextIO | None = None,
        flush: bool = False
) -> None:
    """
    Аналог встроенной функции print(), реализованный через текстовый поток вывода.

    Функция преобразует каждый аргумент в строку через str(), соединяет их через
    разделитель sep, добавляет суффикс end и записывает результат в указанный
    текстовый поток.

    :param args: Набор объектов для вывода. Каждый объект преобразуется в строку
    через str().
    :param sep: Разделитель между аргументами после преобразования в строки.
    По умолчанию: " " (пробел).
    :param end: Строка, добавляемая в конце вывода.
    По умолчанию: '\\n' (перевод строки).
    :param file: Текстовый поток вывода (должен поддерживать file.write(str)).
    Если None, используется sys.stdout.
    :param flush: Если True, выполнить принудительный сброс буфера file.flush()
    после записи. По умолчанию: False.
    :return: None
    """
    if file is None:
        file = sys.stdout

    text = sep.join(map(str, args)) + end
    file.write(text)

    if flush:
        file.flush()


def linebreak() -> None:
    stdout('\n–––\n')


def main():
    # Начало занятия
    linebreak()

    # Переменные
    x = 5
    stdout(f'x={x}')
    linebreak()

    # Типы данных
    age: int = 34
    height: float = 1.75
    surname: str = 'Cohen'
    stdout(f'age: {age}')
    stdout(f'height: {height}')
    stdout(f'surname: {surname}')
    linebreak()

    # Операции ввода-вывода
    name = stdin('Введите ваше имя:')
    stdout(f'name: {name}')
    doc_id = stdin('Введите id документа:')
    stdout(f'ID: {doc_id}')
    usr_input = stdin('Введите ваш возраст:')
    try:
        age = int(usr_input)
    except ValueError:
        stdout(f'Недопустимое значение возраста: {usr_input}')
    else:
        stdout(f'age: {age}')
    linebreak()


if __name__ == '__main__':
    main()
