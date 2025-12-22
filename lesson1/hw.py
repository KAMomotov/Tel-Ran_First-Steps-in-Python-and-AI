"""
Homework :
Write dialog with cash machine
name
surname
id
account
(number)
pin
(code)
money
(amount)

hw@tel-ran.com
"""
# =========================
# Python library
# =========================

import sys
import json
import os
import secrets
import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation


# =========================
# Lesson 1 module
# I/O helpers (stdin/stdout)
# =========================

from lesson1.io import stdout, stdin


# =========
#  Model(s)
# =========

@dataclass
class Account:
    account_number: str
    name: str
    surname: str
    id_number: str
    pin_salt_hex: str
    pin_hash_hex: str
    balance_cents: int = 0
    created_at: str = ""  # ISO string


# ===============
# Storage / Repo
# ===============

class JsonStorage:
    """
    Хранит Accounts в одном JSON файле.

    Формат:
    {
      "accounts": {
        "<account_number>": { ...Account... },
        ...
      }
    }
    """

    def __init__(self, path: str = "atm_data.json") -> None:
        self.path = path

    def load(self) -> dict:
        if not os.path.exists(self.path):
            return {"accounts": {}}
        with open(self.path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "accounts" not in data or not isinstance(data["accounts"], dict):
            return {"accounts": {}}
        return data

    def save(self, data: dict) -> None:
        tmp_path = self.path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, self.path)

    def has_any_accounts(self) -> bool:
        data = self.load()
        return bool(data["accounts"])

    def get_account(self, account_number: str) -> Account | None:
        data = self.load()
        raw = data["accounts"].get(account_number)
        if not raw:
            return None
        return Account(**raw)

    def upsert_account(self, account: Account) -> None:
        data = self.load()
        data["accounts"][account.account_number] = asdict(account)
        self.save(data)

    def account_exists(self, account_number: str) -> bool:
        data = self.load()
        return account_number in data["accounts"]

    def generate_unique_account_number(self, digits: int = 10) -> str:
        """
        Генерация уникального номера счёта из digits цифр.
        """
        # secrets.randbelow даёт криптостойкую случайность (стандартная библиотека)
        while True:
            n = secrets.randbelow(10**digits)
            acc = str(n).zfill(digits)
            if not self.account_exists(acc):
                return acc


# ========
#  View
# ========

class ConsoleView:
    def show_title(self) -> None:
        stdout("=" * 44)
        stdout("  Tel-Tan ATM — учебный банкомат (MVC)")
        stdout("=" * 44)

    def pause(self, message: str = "Нажмите Enter, чтобы продолжить...") -> None:
        stdout(message, end="")
        sys.stdin.readline()

    def info(self, message: str) -> None:
        stdout(message)

    def warn(self, message: str) -> None:
        stdout(f"[!]{' ' if message else ''}{message}")

    def error(self, message: str) -> None:
        stdout(f"[Ошибка] {message}")

    def ask_text(self, prompt: str, *, min_len: int = 1) -> str:
        while True:
            s = stdin(prompt).strip()
            if len(s) >= min_len:
                return s
            self.error(f"Введите минимум {min_len} символ(а/ов).")

    def ask_digits(self, prompt: str, *, min_len: int = 1, max_len: int | None = None) -> str:
        while True:
            s = stdin(prompt).strip()
            if not s.isdigit():
                self.error("Разрешены только цифры.")
                continue
            if len(s) < min_len:
                self.error(f"Минимум {min_len} цифр.")
                continue
            if max_len is not None and len(s) > max_len:
                self.error(f"Максимум {max_len} цифр.")
                continue
            return s

    def ask_pin_create(self) -> str:
        """
        Просим создать PIN: 4–8 цифр, два раза.
        """
        self.info("Создайте PIN-код (4–8 цифр).")
        while True:
            pin1 = self.ask_digits("Введите PIN", min_len=4, max_len=8)
            pin2 = self.ask_digits("Повторите PIN", min_len=4, max_len=8)
            if pin1 == pin2:
                return pin1
            self.error("PIN не совпадает. Попробуйте ещё раз.")

    def ask_pin_login(self) -> str:
        return self.ask_digits("Введите PIN", min_len=4, max_len=8)

    def ask_money_amount(self, prompt: str) -> int:
        """
        Возвращает сумму в центах (целое число).
        Принимает ввод вида: 100, 100.50, 100,50
        """
        while True:
            raw = stdin(prompt).strip().replace(",", ".")
            try:
                d = Decimal(raw)
            except (InvalidOperation, ValueError):
                self.error("Введите корректное число (например: 100 или 100.50).")
                continue

            if d.is_nan() or d.is_infinite():
                self.error("Некорректное значение суммы.")
                continue
            if d < 0:
                self.error("Сумма не может быть отрицательной.")
                continue

            cents = int((d * 100).quantize(Decimal("1")))
            return cents

    def show_account_created(self, account_number: str) -> None:
        self.info("")
        self.info("Счёт создан ✅")
        self.warn("ВНИМАНИЕ: номер счёта показывается только один раз.")
        self.info(f"Ваш номер счёта: {account_number}")
        self.info("")

    def show_balance(self, balance_cents: int) -> None:
        self.info(f"Текущий баланс: {self.format_money(balance_cents)}")

    @staticmethod
    def format_money(cents: int) -> str:
        sign = "-" if cents < 0 else ""
        cents_abs = abs(cents)
        return f"{sign}{cents_abs // 100}.{cents_abs % 100:02d}"

    def menu_startup(self) -> str:
        stdout("")
        stdout("1) Создать новый счёт")
        stdout("2) Войти в существующий счёт")
        stdout("0) Выход")
        return stdin("Выберите действие").strip()

    def menu_main(self) -> str:
        stdout("")
        stdout("1) Внести деньги на счёт")
        stdout("2) Снять деньги со счёта")
        stdout("3) Показать баланс")
        stdout("0) Выход")
        return stdin("Выберите действие").strip()


# ============
#  Controller
# ============

class ATMController:
    def __init__(self, storage: JsonStorage, view: ConsoleView) -> None:
        self.storage = storage
        self.view = view

    # --- security helpers ---
    @staticmethod
    def _hash_pin(pin: str, salt: bytes) -> bytes:
        # простой, но адекватный для учебки вариант:
        # hash = sha256(salt + pin)
        return hashlib.sha256(salt + pin.encode("utf-8")).digest()

    def _make_pin_record(self, pin: str) -> tuple[str, str]:
        salt = secrets.token_bytes(16)
        h = self._hash_pin(pin, salt)
        return salt.hex(), h.hex()

    def _verify_pin(self, pin: str, salt_hex: str, hash_hex: str) -> bool:
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
        actual = self._hash_pin(pin, salt)
        # сравнение без утечек по времени (для приличия)
        return secrets.compare_digest(actual, expected)

    # --- flows ---
    def run(self) -> None:
        self.view.show_title()

        # Первый запуск: если в хранилище нет ни одного аккаунта
        if not self.storage.has_any_accounts():
            self.view.info("Похоже, это первый запуск: аккаунтов ещё нет.")
            self.view.pause()
            account = self.flow_create_account()
            self.flow_session(account)
            self.view.info("До свидания!")
            return

        # Не первый запуск
        while True:
            choice = self.view.menu_startup()
            if choice == "1":
                account = self.flow_create_account()
                self.flow_session(account)
            elif choice == "2":
                account = self.flow_login()
                if account:
                    self.flow_session(account)
            elif choice == "0":
                self.view.info("До свидания!")
                return
            else:
                self.view.error("Неизвестный пункт меню.")

    def flow_create_account(self) -> Account:
        self.view.info("")
        self.view.info("=== Создание нового счёта ===")

        name = self.view.ask_text("Введите ваше имя")
        surname = self.view.ask_text("Введите вашу фамилию")
        id_number = self.view.ask_text("Введите ваш ID (можно цифры/буквы)")

        account_number = self.storage.generate_unique_account_number(digits=10)

        pin = self.view.ask_pin_create()
        salt_hex, hash_hex = self._make_pin_record(pin)

        account = Account(
            account_number=account_number,
            name=name,
            surname=surname,
            id_number=id_number,
            pin_salt_hex=salt_hex,
            pin_hash_hex=hash_hex,
            balance_cents=0,
            created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )

        self.storage.upsert_account(account)
        self.view.show_account_created(account.account_number)

        # Первичный взнос
        deposit = self.view.ask_money_amount("Внесите сумму на счёт (например 100 или 100.50)")
        if deposit > 0:
            account.balance_cents += deposit
            self.storage.upsert_account(account)
            self.view.info(f"Зачислено: {self.view.format_money(deposit)}")
            self.view.show_balance(account.balance_cents)
        else:
            self.view.info("Сумма 0 — пропускаем пополнение.")
            self.view.show_balance(account.balance_cents)

        return account

    def flow_login(self) -> Account | None:
        self.view.info("")
        self.view.info("=== Вход в существующий счёт ===")

        acc_num = self.view.ask_digits("Введите номер счёта", min_len=10, max_len=10)
        account = self.storage.get_account(acc_num)
        if not account:
            self.view.error("Счёт не найден.")
            return None

        pin = self.view.ask_pin_login()
        if not self._verify_pin(pin, account.pin_salt_hex, account.pin_hash_hex):
            self.view.error("Неверный PIN.")
            return None

        self.view.info(f"Успешный вход. Добро пожаловать, {account.name} {account.surname}!")
        self.view.show_balance(account.balance_cents)
        return account

    def flow_session(self, account: Account) -> None:
        """
        Главная сессия после создания/логина.
        """
        while True:
            choice = self.view.menu_main()

            if choice == "1":
                amount = self.view.ask_money_amount("Сколько внести?")
                if amount <= 0:
                    self.view.error("Сумма пополнения должна быть больше 0.")
                    continue
                account.balance_cents += amount
                self.storage.upsert_account(account)
                self.view.info(f"Зачислено: {self.view.format_money(amount)}")
                self.view.show_balance(account.balance_cents)

            elif choice == "2":
                amount = self.view.ask_money_amount("Сколько снять?")
                if amount <= 0:
                    self.view.error("Сумма снятия должна быть больше 0.")
                    continue
                if amount > account.balance_cents:
                    self.view.error("Недостаточно средств.")
                    self.view.show_balance(account.balance_cents)
                    continue
                account.balance_cents -= amount
                self.storage.upsert_account(account)
                self.view.info(f"Выдано: {self.view.format_money(amount)}")
                self.view.show_balance(account.balance_cents)

            elif choice == "3":
                self.view.show_balance(account.balance_cents)

            elif choice == "0":
                self.view.info("Выход в главное меню.")
                return

            else:
                self.view.error("Неизвестный пункт меню.")


# ==========
#  __main__
# ==========

def main() -> None:
    storage = JsonStorage(path="atm_data.json")
    view = ConsoleView()
    controller = ATMController(storage, view)
    controller.run()


if __name__ == "__main__":
    main()
