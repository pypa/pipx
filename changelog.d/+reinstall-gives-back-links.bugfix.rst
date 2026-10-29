When a rebuild fails during a parallel ``pipx reinstall-all``, the restored environment gets back the shared app, man
page or completion links another environment took while the rebuild had it in the trash, unless something outside this
run has replaced them since.
