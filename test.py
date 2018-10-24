import subprocess


def main():
    files = ["get-pipx.py", "pipx", "tests"]
    subprocess.run(["python3", "-m", "tests"], check=True)
    subprocess.run(["flake8", "--no-py2", "--py3"] + files, check=True)
    subprocess.run(["mypy"] + files, check=True)
    subprocess.run(["black", "--check"] + files, check=True)


if __name__ == "__main__":
    main()
