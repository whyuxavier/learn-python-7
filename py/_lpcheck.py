"""Тихий запуск коду учня для автоперевірки завдань (7 клас).
Програма виконується з підготовленими даними для input(), а її виведення
повертається сторінці як текст. Нічого не з'являється в полі «Результат»."""
import builtins
import io
import json
import random
import sys

import _lp

LIMIT = 200000          # скільки рядків коду учня можна виконати в одному тесті


class _NoInput(Exception):
    pass


class _TooLong(Exception):
    pass


def _run_one(code, inputs, seed):
    buf = io.StringIO()
    queue = list(inputs)
    steps = [0]

    def fake_input(prompt=''):
        # підказку й введене значення позначаємо, щоб не плутати їх з виведенням програми
        if not queue:
            buf.write('\x01' + str(prompt) + '\x02')
            raise _NoInput()
        v = str(queue.pop(0))
        buf.write('\x01' + str(prompt) + v + '\n\x02')
        return v

    def tracer(frame, event, arg):
        if frame.f_code.co_filename != '<учень>':
            return None
        return local

    def local(frame, event, arg):
        if event == 'line':
            steps[0] += 1
            if steps[0] > LIMIT:
                raise _TooLong()
        return local

    old_out, old_err, old_in = sys.stdout, sys.stderr, builtins.input
    sys.stdout = buf
    sys.stderr = buf
    builtins.input = fake_input
    random.seed(seed)
    res = {'out': '', 'err': '', 'left': 0}
    g = {'__name__': '__main__', '__builtins__': builtins}
    try:
        c = compile(code, '<учень>', 'exec')
        sys.settrace(tracer)
        exec(c, g)
    except _NoInput:
        res['err'] = 'Програма просить більше даних, ніж передбачено в тесті.'
    except _TooLong:
        res['err'] = 'Програма виконується надто довго. Можливо, цикл ніколи не закінчується.'
    except SystemExit:
        pass
    except BaseException as e:
        try:
            t, h = _lp.explain(e)
        except Exception:
            t, h = 'Помилка', ''
        line = None
        if isinstance(e, SyntaxError):
            line = e.lineno
        else:
            tb = e.__traceback__
            while tb is not None:
                if tb.tb_frame.f_code.co_filename == '<учень>':
                    line = tb.tb_lineno
                tb = tb.tb_next
        res['err'] = ('Рядок %s: ' % line if line else '') + t + ('. ' + h if h else '')
    finally:
        sys.settrace(None)
        sys.stdout, sys.stderr, builtins.input = old_out, old_err, old_in
    res['out'] = buf.getvalue()[:4000]
    res['left'] = len(queue)
    return res


def run(payload):
    p = json.loads(str(payload))
    code = p['code']
    out = []
    for k, t in enumerate(p['tests']):
        out.append(_run_one(code, t.get('i') or [], t.get('seed', 7 + k)))
    return json.dumps(out, ensure_ascii=False)


# ---------- інтерактивна оболонка (як >>> в IDLE) ----------
_shell_g = {'__name__': '__main__', '__builtins__': builtins}


def _shell_input(prompt=''):
    raise RuntimeError('input() у цій оболонці не працює. Програми з input() пиши в редакторі й запускай кнопкою «Запустити».')


def shell(src):
    """Виконує один рядок, як інтерактивна оболонка: значення виразу друкується саме."""
    src = str(src)
    buf = io.StringIO()
    old_out, old_err, old_in, old_hook = sys.stdout, sys.stderr, builtins.input, sys.displayhook
    sys.stdout = buf
    sys.stderr = buf
    builtins.input = _shell_input
    steps = [0]

    def hook(v):
        if v is not None:
            _shell_g['_'] = v
            buf.write(repr(v) + '\n')

    def tracer(frame, event, arg):
        if frame.f_code.co_filename != '<оболонка>':
            return None
        return local

    def local(frame, event, arg):
        if event == 'line':
            steps[0] += 1
            if steps[0] > LIMIT:
                raise _TooLong()
        return local

    sys.displayhook = hook
    err = ''
    try:
        c = compile(src, '<оболонка>', 'single')
        sys.settrace(tracer)
        exec(c, _shell_g)
    except _TooLong:
        err = 'Команда виконується надто довго.'
    except SystemExit:
        pass
    except BaseException as e:
        try:
            t, h = _lp.explain(e)
        except Exception:
            t, h = 'Помилка', ''
        if isinstance(e, RuntimeError) and 'input()' in str(e):
            err = str(e)
        else:
            err = t + ('. ' + h if h else '') + '\n' + type(e).__name__ + ': ' + (e.msg if isinstance(e, SyntaxError) else str(e))
    finally:
        sys.settrace(None)
        sys.stdout, sys.stderr, builtins.input, sys.displayhook = old_out, old_err, old_in, old_hook
    return json.dumps({'out': buf.getvalue()[:4000], 'err': err}, ensure_ascii=False)


def shell_reset():
    _shell_g.clear()
    _shell_g.update({'__name__': '__main__', '__builtins__': builtins})
