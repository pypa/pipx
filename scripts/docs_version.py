import mkdocs_gen_files

with mkdocs_gen_files.open("foo.md", "w") as f:
    print("Hello, world!", file=f)
