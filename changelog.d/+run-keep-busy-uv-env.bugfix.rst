On Windows under the uv backend, ``pipx run --refresh`` or ``--no-cache`` of a local script no longer deletes the cached
environment while another run of the same script is still executing in it, and neither does the expiry sweep. Such a
run builds a throwaway environment for itself instead, and after ``--refresh`` the next run to find the cached one idle
rebuilds it.
