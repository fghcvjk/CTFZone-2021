import re

UNDEFINED = object()


def sandbox_exec(code: str):
    assert code.isascii()
    assert re.match(r'''^[^("R93i7')]+$''', code)
    assert '_s' not in code

    namespace = {
        '__builtins__': {},
        'result': UNDEFINED
    }

    exec(code, namespace)

    return namespace['result']


def task():
    secret = input()
    code = input()
    try:
        result = sandbox_exec(code)
        if result is UNDEFINED:
            msg = '[!] You forgot to assign something to `result` o_O'
        else:
            msg = repr(result)
    except AssertionError:
        msg = '[!] Recheck your payload. It stinks!'
    except Exception:
        msg = '[!] Something bad happened... And you like it, I know...'

    print(msg, end='')


if __name__ == '__main__':
    task()
