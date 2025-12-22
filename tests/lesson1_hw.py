import io
import json
import sys
import types
import pytest

import lesson1.hw as app  # <-- если модуль называется иначе, поменяй тут


# --------------------
# Helpers / fixtures
# --------------------

def feed_stdin(lines: list[str]) -> io.StringIO:
    """
    Подготовить "ввод пользователя" для sys.stdin.
    Каждый элемент -> отдельная строка (как Enter).
    """
    return io.StringIO("".join(line + "\n" for line in lines))


class RandBelowSeq:
    """Детерминированная последовательность для secrets.randbelow()."""
    def __init__(self, values):
        self._it = iter(values)

    def __call__(self, _n: int) -> int:
        return next(self._it)


@pytest.fixture
def io_env(monkeypatch):
    """
    Изолируем stdin/stdout для каждого теста.
    """
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    return out


@pytest.fixture
def storage(tmp_path):
    return app.JsonStorage(path=str(tmp_path / "atm_data.json"))


@pytest.fixture
def deterministic_secrets(monkeypatch):
    """
    Делаем генерацию аккаунта и соли предсказуемой.
    """
    # Номер счёта -> "0000000123"
    monkeypatch.setattr(app.secrets, "randbelow", RandBelowSeq([123, 456, 789]))
    # Соль -> 16 байт нулей (hex = "00"*16)
    monkeypatch.setattr(app.secrets, "token_bytes", lambda n: b"\x00" * n)


@pytest.fixture
def fixed_datetime(monkeypatch):
    """
    Фиксируем created_at, чтобы тесты не зависели от времени.
    Подстраховка: работает и для datetime.utcnow(), и для datetime.now(timezone.utc),
    в зависимости от того, какую реализацию ты оставил.
    """
    class FakeDT:
        @staticmethod
        def utcnow():
            # если у тебя еще utcnow()
            return app.datetime(2025, 1, 1, 0, 0, 0)

        @staticmethod
        def now(tz=None):
            if tz is None:
                return app.datetime(2025, 1, 1, 0, 0, 0)
            return app.datetime(2025, 1, 1, 0, 0, 0, tzinfo=tz)

    # подменяем имя datetime внутри модуля
    monkeypatch.setattr(app, "datetime", FakeDT)


def read_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# --------------------
# Tests: stdout/stdin
# --------------------

def test_stdout_basic(io_env):
    out = io.StringIO()
    app.stdout("a", 1, 2, file=out)
    assert out.getvalue() == "a 1 2\n"


def test_stdout_sep_end_flush_called():
    class FlushSpy(io.StringIO):
        def __init__(self):
            super().__init__()
            self.flush_calls = 0

        def flush(self):
            self.flush_calls += 1
            super().flush()

    spy = FlushSpy()
    app.stdout("x", "y", sep=":", end="!", file=spy, flush=True)
    assert spy.getvalue() == "x:y!"
    assert spy.flush_calls == 1


def test_stdin_reads_and_strips_lf(monkeypatch, io_env):
    monkeypatch.setattr(sys, "stdin", feed_stdin(["hello"]))
    assert app.stdin(out=sys.stdout) == "hello"


def test_stdin_strips_crlf(monkeypatch, io_env):
    monkeypatch.setattr(sys, "stdin", io.StringIO("hello\r\n"))
    assert app.stdin(out=sys.stdout) == "hello"


def test_stdin_eof_raises(monkeypatch, io_env):
    monkeypatch.setattr(sys, "stdin", io.StringIO(""))
    with pytest.raises(EOFError):
        app.stdin(out=sys.stdout)


# --------------------
# Tests: JsonStorage
# --------------------

def test_storage_load_when_missing(storage):
    data = storage.load()
    assert data == {"accounts": {}}


def test_storage_save_and_load_roundtrip(storage):
    storage.save({"accounts": {"1": {"account_number": "1"}}})
    assert storage.load()["accounts"]["1"]["account_number"] == "1"


def test_storage_load_invalid_shape(storage, tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{}", encoding="utf-8")
    st = app.JsonStorage(path=str(p))
    assert st.load() == {"accounts": {}}

    p.write_text('{"accounts": []}', encoding="utf-8")
    assert st.load() == {"accounts": {}}


def test_storage_upsert_get_exists(storage):
    acc = app.Account(
        account_number="0000000001",
        name="A",
        surname="B",
        id_number="ID",
        pin_salt_hex="00",
        pin_hash_hex="11",
        balance_cents=100,
        created_at="2025-01-01T00:00:00Z",
    )
    storage.upsert_account(acc)
    assert storage.account_exists("0000000001") is True

    loaded = storage.get_account("0000000001")
    assert loaded is not None
    assert loaded.balance_cents == 100
    assert loaded.name == "A"


def test_storage_generate_unique_account_number(storage, monkeypatch):
    # заставим randbelow выдавать 5 -> "0000000005"
    monkeypatch.setattr(app.secrets, "randbelow", lambda n: 5)
    acc_num = storage.generate_unique_account_number(digits=10)
    assert acc_num == "0000000005"


# --------------------
# Tests: ConsoleView
# --------------------

def test_view_ask_digits_validation(monkeypatch, io_env):
    v = app.ConsoleView()
    # сначала вводим "abc" (ошибка), потом "12" (корректно)
    monkeypatch.setattr(sys, "stdin", feed_stdin(["abc", "12"]))
    got = v.ask_digits("Введите цифры", min_len=2)
    assert got == "12"


def test_view_ask_money_amount_parsing(monkeypatch, io_env):
    v = app.ConsoleView()
    monkeypatch.setattr(sys, "stdin", feed_stdin(["100,50"]))
    cents = v.ask_money_amount("Сколько?")
    assert cents == 10050


def test_view_ask_pin_create_two_steps(monkeypatch, io_env):
    v = app.ConsoleView()
    # pin1 != pin2, потом совпали
    monkeypatch.setattr(sys, "stdin", feed_stdin(["1111", "2222", "1234", "1234"]))
    pin = v.ask_pin_create()
    assert pin == "1234"


# --------------------
# Tests: ATMController (end-to-end flows)
# --------------------

def test_first_run_creates_account_and_deposits_then_exit(
    monkeypatch, io_env, storage, deterministic_secrets, fixed_datetime
):
    """
    Первый запуск: нет аккаунтов -> создание -> первичный депозит -> меню -> выход
    """
    view = app.ConsoleView()
    controller = app.ATMController(storage, view)

    # Ввод пользователя:
    # 1) pause() -> Enter
    # 2) name, surname, id
    # 3) pin (двойной)
    # 4) initial deposit
    # 5) main menu: 3 (показать баланс), 0 (выход)
    monkeypatch.setattr(
        sys, "stdin",
        feed_stdin([
            "",              # pause
            "Kirill",        # name
            "Momotov",       # surname
            "ID123",         # id
            "1234",          # pin1
            "1234",          # pin2
            "10.00",         # deposit
            "3",             # show balance
            "0",             # exit session
        ])
    )

    controller.run()

    # Проверяем, что файл создан и аккаунт сохранён
    data = read_json(storage.path)
    assert "accounts" in data
    assert "0000000123" in data["accounts"]

    acc_raw = data["accounts"]["0000000123"]
    assert acc_raw["name"] == "Kirill"
    assert acc_raw["balance_cents"] == 1000

    out_text = io_env.getvalue()
    assert "Счёт создан" in out_text
    assert "Ваш номер счёта: 0000000123" in out_text
    assert "Текущий баланс: 10.00" in out_text


def test_login_success_deposit_withdraw_and_exit(
    monkeypatch, io_env, storage, deterministic_secrets, fixed_datetime
):
    """
    Не первый запуск:
      меню -> вход -> депозит -> снятие -> выход из сессии -> выход из приложения
    """
    view = app.ConsoleView()
    controller = app.ATMController(storage, view)

    # Подготовим аккаунт через официальный flow_create_account (с теми же secrets)
    monkeypatch.setattr(
        sys, "stdin",
        feed_stdin([
            "Kirill", "Momotov", "ID123",
            "1234", "1234",
            "0",  # initial deposit = 0 (покрываем ветку "пропускаем")
        ])
    )
    acc = controller.flow_create_account()
    assert acc.account_number == "0000000123"
    assert acc.balance_cents == 0

    # Теперь запускаем controller.run() в режиме "не первый запуск"
    # Ввод:
    # startup menu: 2 (login)
    # account number, pin
    # main menu: 1 deposit 5, 2 withdraw 2, 3 balance, 0 exit session
    # startup menu: 0 exit app
    monkeypatch.setattr(
        sys, "stdin",
        feed_stdin([
            "2",
            "0000000123",
            "1234",
            "1",
            "5.00",
            "2",
            "2.00",
            "3",
            "0",
            "0",
        ])
    )

    controller.run()

    loaded = storage.get_account("0000000123")
    assert loaded is not None
    assert loaded.balance_cents == 300  # 5.00 - 2.00

    out_text = io_env.getvalue()
    assert "Успешный вход" in out_text
    assert "Зачислено: 5.00" in out_text
    assert "Выдано: 2.00" in out_text
    assert "Текущий баланс: 3.00" in out_text


def test_login_wrong_pin_then_exit(
    monkeypatch, io_env, storage, deterministic_secrets, fixed_datetime
):
    view = app.ConsoleView()
    controller = app.ATMController(storage, view)

    # создадим аккаунт
    monkeypatch.setattr(
        sys, "stdin",
        feed_stdin([
            "A", "B", "ID",
            "1234", "1234",
            "0",
        ])
    )
    controller.flow_create_account()

    # не первый запуск: login с неверным PIN, потом выйти
    monkeypatch.setattr(
        sys, "stdin",
        feed_stdin([
            "2",
            "0000000123",
            "9999",  # wrong
            "0",
        ])
    )

    controller.run()
    assert "Неверный PIN" in io_env.getvalue()


def test_withdraw_insufficient_funds_branch(
    monkeypatch, io_env, storage, deterministic_secrets, fixed_datetime
):
    view = app.ConsoleView()
    controller = app.ATMController(storage, view)

    # создать аккаунт с 1.00
    monkeypatch.setattr(
        sys, "stdin",
        feed_stdin([
            "A", "B", "ID",
            "1234", "1234",
            "1.00",  # initial deposit
        ])
    )
    acc = controller.flow_create_account()
    assert acc.balance_cents == 100

    # попытка снять 2.00 -> недостаточно средств -> потом 0 выход
    monkeypatch.setattr(
        sys, "stdin",
        feed_stdin([
            "2",        # withdraw
            "2.00",     # too much
            "0",        # exit session
        ])
    )
    controller.flow_session(acc)

    out_text = io_env.getvalue()
    assert "Недостаточно средств" in out_text


def test_keyboardinterrupt_propagates_from_stdin(monkeypatch, io_env):
    """
    Подтверждаем контракт: KeyboardInterrupt не перехватывается stdin().
    """
    class InterruptIn:
        def readline(self) -> str:
            raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        app.stdin(file=InterruptIn(), out=sys.stdout)
