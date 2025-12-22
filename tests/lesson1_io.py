import io
import pytest

from lesson1.io import stdin, stdout


class FlushSpy(io.StringIO):
    """StringIO, который считает вызовы flush()."""
    def __init__(self):
        super().__init__()
        self.flush_called = 0

    def flush(self):
        self.flush_called += 1
        super().flush()


class ReadlineEOF:
    """Поток, который сразу даёт EOF (readline -> '')."""
    def readline(self) -> str:
        return ""


class ReadlineInterrupt:
    """Поток, который имитирует Ctrl+C (readline -> KeyboardInterrupt)."""
    def readline(self) -> str:
        raise KeyboardInterrupt


def test_stdout_writes_joined_args_with_default_sep_end():
    out = io.StringIO()
    stdout("a", 1, 2, file=out)
    assert out.getvalue() == "a 1 2\n"


def test_stdout_custom_sep_end():
    out = io.StringIO()
    stdout("a", 1, 2, sep=":", end="!", file=out)
    assert out.getvalue() == "a:1:2!"


def test_stdout_writes_only_to_given_file():
    out1 = io.StringIO()
    out2 = io.StringIO()

    stdout("X", file=out1)
    assert out1.getvalue() == "X\n"
    assert out2.getvalue() == ""  # никакой побочной записи


def test_stdout_flush_true_calls_flush_once():
    out = FlushSpy()
    stdout("hi", file=out, flush=True)

    assert out.getvalue() == "hi\n"
    assert out.flush_called == 1


def test_stdout_flush_false_does_not_call_flush():
    out = FlushSpy()
    stdout("hi", file=out, flush=False)

    assert out.getvalue() == "hi\n"
    assert out.flush_called == 0


def test_stdin_without_prompt_prints_repl_prompt_and_reads_line():
    inp = io.StringIO("hello\n")
    out = io.StringIO()

    s = stdin(file=inp, out=out)

    assert s == "hello"
    assert out.getvalue() == ">>> "


def test_stdin_with_prompt_prints_prompt_newline_and_repl_marker():
    inp = io.StringIO("42\n")
    out = io.StringIO()

    s = stdin("Введите число", file=inp, out=out)

    assert s == "42"
    assert out.getvalue() == "Введите число\n>>> "


def test_stdin_strips_lf():
    inp = io.StringIO("hello\n")
    out = io.StringIO()

    assert stdin(file=inp, out=out) == "hello"


def test_stdin_strips_crlf():
    inp = io.StringIO("hello\r\n")
    out = io.StringIO()

    assert stdin(file=inp, out=out) == "hello"


def test_stdin_does_not_strip_other_trailing_spaces_or_chars():
    inp = io.StringIO("hello  \n")  # два пробела перед \n должны остаться
    out = io.StringIO()

    assert stdin(file=inp, out=out) == "hello  "


def test_stdin_eof_raises_and_still_prints_prompt():
    inp = ReadlineEOF()
    out = io.StringIO()

    with pytest.raises(EOFError):
        stdin(file=inp, out=out)

    # prompt печатается до попытки чтения — так устроена функция
    assert out.getvalue() == ">>> "


def test_stdin_flush_true_flushes_out():
    inp = io.StringIO("ok\n")
    out = FlushSpy()

    s = stdin(file=inp, out=out, flush=True)

    assert s == "ok"
    assert out.getvalue() == ">>> "
    assert out.flush_called == 1  # flush после печати prompt


def test_stdin_flush_false_does_not_flush_out():
    inp = io.StringIO("ok\n")
    out = FlushSpy()

    s = stdin(file=inp, out=out, flush=False)

    assert s == "ok"
    assert out.getvalue() == ">>> "
    assert out.flush_called == 0


def test_stdin_keyboardinterrupt_is_propagated_and_prompt_is_printed():
    inp = ReadlineInterrupt()
    out = io.StringIO()

    with pytest.raises(KeyboardInterrupt):
        stdin(file=inp, out=out)

    assert out.getvalue() == ">>> "
