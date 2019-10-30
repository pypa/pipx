from pipx.pipx_metadata_file import PipxMetadata, PackageInfo


# test to make sure we never have duplicate injected packages
#   this might happen during reinstall_all if we don't properly uninstall
#       injected packages or don't remove their metadata


def test_pipx_metadata_file_create():
    pass
    #assert False
