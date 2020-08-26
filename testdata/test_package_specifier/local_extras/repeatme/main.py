import sys

try:
    import pycowsay.main

    has_pycowsay = True
except ImportError:
    has_pycowsay = False


def main():
    print(f"You said:\n    {' '.join(sys.argv[1:])}")

    if has_pycowsay:
        print()
        print("In cow, you said:")
        pycowsay.main.main()
