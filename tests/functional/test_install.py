
import os
import textwrap
import glob

from os.path import join, curdir, pardir

import pytest

from pip.utils import appdirs, rmtree
from tests.lib import (pyversion, pyversion_tuple,
                       _create_test_package, _create_svn_repo, path_to_url)
from tests.lib.local_repos import local_checkout
from tests.lib.path import Path


def test_without_setuptools(script, data):
    script.run("pip", "uninstall", "setuptools", "-y")
    result = script.run(
        "python", "-c",
        "import pip; pip.main(["
        "'install', "
        "'INITools==0.2', "
        "'-f', '%s', "
        "'--no-binary=:all:'])" % data.packages,
        expect_error=True,
    )
    assert (
        "setuptools must be installed to install from a source distribution"
        in result.stderr
    )


def test_pip_second_command_line_interface_works(script, data):
    """
    Check if ``pip<PYVERSION>`` commands behaves equally
    """
    # On old versions of Python, urllib3/requests will raise a warning about
    # the lack of an SSLContext.
    kwargs = {}
    if pyversion_tuple < (2, 7, 9):
        kwargs['expect_stderr'] = True

    args = ['pip%s' % pyversion]
    args.extend(['install', 'INITools==0.2'])
    args.extend(['-f', data.packages])
    result = script.run(*args, **kwargs)
    egg_info_folder = (
        script.site_packages / 'INITools-0.2-py%s.egg-info' % pyversion
    )
    initools_folder = script.site_packages / 'initools'
    assert egg_info_folder in result.files_created, str(result)
    assert initools_folder in result.files_created, str(result)


@pytest.mark.network
def test_install_from_pypi(script):
    """
    Test installing a package from PyPI.
    """
    result = script.pip('install', '-vvv', 'INITools==0.2')
    egg_info_folder = (
        script.site_packages / 'INITools-0.2-py%s.egg-info' % pyversion
    )
    initools_folder = script.site_packages / 'initools'
    assert egg_info_folder in result.files_created, str(result)
    assert initools_folder in result.files_created, str(result)


def test_editable_install(script):
    """
    Test editable installation.
    """
    result = script.pip('install', '-e', 'INITools==0.2', expect_error=True)
    assert (
        "INITools==0.2 should either be a path to a local project or a VCS url"
        in result.stderr
    )
    assert not result.files_created
    assert not result.files_updated


def test_install_editable_from_svn(script):
    """
    Test checking out from svn.
    """
    checkout_path = _create_test_package(script)
    repo_url = _create_svn_repo(script, checkout_path)
    result = script.pip(
        'install',
        '-e', 'svn+' + repo_url + '#egg=version-pkg'
    )
    result.assert_installed('version-pkg', with_files=['.svn'])


@pytest.mark.network
def test_download_editable_to_custom_path(script, tmpdir):
    """
    Test downloading an editable using a relative custom src folder.
    """
    script.scratch_path.join("customdl").mkdir()
    result = script.pip(
        'install',
        '-e',
        '%s#egg=initools-dev' %
        local_checkout(
            'svn+http://svn.colorstudy.com/INITools/trunk',
            tmpdir.join("cache")
        ),
        '--src',
        'customsrc',
        '--download',
        'customdl',
    )
    customsrc = Path('scratch') / 'customsrc' / 'initools'
    assert customsrc in result.files_created, (
        sorted(result.files_created.keys())
    )
    assert customsrc / 'setup.py' in result.files_created, (
        sorted(result.files_created.keys())
    )

    customdl = Path('scratch') / 'customdl' / 'initools'
    customdl_files_created = [
        filename for filename in result.files_created
        if filename.startswith(customdl)
    ]
    assert customdl_files_created


@pytest.mark.network
def test_install_dev_version_from_pypi(script):
    """
    Test using package==dev.
    """
    result = script.pip(
        'install', 'INITools===dev',
        '--allow-external', 'INITools',
        '--allow-unverified', 'INITools',
        expect_error=True,
    )
    assert (script.site_packages / 'initools') in result.files_created, (
        str(result.stdout)
    )


def _test_install_editable_from_git(script, tmpdir, wheel):
    """Test cloning from Git."""
    if wheel:
        script.pip('install', 'wheel')
    pkg_path = _create_test_package(script, name='testpackage', vcs='git')
    args = ['install', '-e', 'git+%s#egg=testpackage' % path_to_url(pkg_path)]
    result = script.pip(*args, **{"expect_error": True})
    result.assert_installed('testpackage', with_files=['.git'])


def test_install_editable_from_git(script, tmpdir):
    _test_install_editable_from_git(script, tmpdir, False)


def test_install_editable_from_git_autobuild_wheel(script, tmpdir):
    _test_install_editable_from_git(script, tmpdir, True)


def test_install_editable_from_hg(script, tmpdir):
    """Test cloning from Mercurial."""
    pkg_path = _create_test_package(script, name='testpackage', vcs='hg')
    args = ['install', '-e', 'hg+%s#egg=testpackage' % path_to_url(pkg_path)]
    result = script.pip(*args, **{"expect_error": True})
    result.assert_installed('testpackage', with_files=['.hg'])


def test_vcs_url_final_slash_normalization(script, tmpdir):
    """
    Test that presence or absence of final slash in VCS URL is normalized.
    """
    pkg_path = _create_test_package(script, name='testpackage', vcs='hg')
    args = ['install', '-e', 'hg+%s/#egg=testpackage' % path_to_url(pkg_path)]
    result = script.pip(*args, **{"expect_error": True})
    result.assert_installed('testpackage', with_files=['.hg'])


def test_install_editable_from_bazaar(script, tmpdir):
    """Test checking out from Bazaar."""
    pkg_path = _create_test_package(script, name='testpackage', vcs='bazaar')
    args = ['install', '-e', 'bzr+%s/#egg=testpackage' % path_to_url(pkg_path)]
    result = script.pip(*args, **{"expect_error": True})
    result.assert_installed('testpackage', with_files=['.bzr'])


@pytest.mark.network
def test_vcs_url_urlquote_normalization(script, tmpdir):
    """
    Test that urlquoted characters are normalized for repo URL comparison.
    """
    script.pip(
        'install', '-e',
        '%s/#egg=django-wikiapp' %
        local_checkout(
            'bzr+http://bazaar.launchpad.net/%7Edjango-wikiapp/django-wikiapp'
            '/release-0.1',
            tmpdir.join("cache"),
        ),
    )


def test_install_from_local_directory(script, data):
    """
    Test installing from a local directory.
    """
    to_install = data.packages.join("FSPkg")
    result = script.pip('install', to_install, expect_error=False)
    fspkg_folder = script.site_packages / 'fspkg'
    egg_info_folder = (
        script.site_packages / 'FSPkg-0.1.dev0-py%s.egg-info' % pyversion
    )
    assert fspkg_folder in result.files_created, str(result.stdout)
    assert egg_info_folder in result.files_created, str(result)


def test_install_from_local_directory_with_symlinks_to_directories(
        script, data):
    """
    Test installing from a local directory containing symlinks to directories.
    """
    to_install = data.packages.join("symlinks")
    result = script.pip('install', to_install, expect_error=False)
    pkg_folder = script.site_packages / 'symlinks'
    egg_info_folder = (
        script.site_packages / 'symlinks-0.1.dev0-py%s.egg-info' % pyversion
    )
    assert pkg_folder in result.files_created, str(result.stdout)
    assert egg_info_folder in result.files_created, str(result)


def test_install_from_local_directory_with_no_setup_py(script, data):
    """
    Test installing from a local directory with no 'setup.py'.
    """
    result = script.pip('install', data.root, expect_error=True)
    assert not result.files_created
    assert "is not installable. File 'setup.py' not found." in result.stderr


def test_editable_install_from_local_directory_with_no_setup_py(script, data):
    """
    Test installing from a local directory with no 'setup.py'.
    """
    result = script.pip('install', '-e', data.root, expect_error=True)
    assert not result.files_created
    assert "is not installable. File 'setup.py' not found." in result.stderr


def test_install_as_egg(script, data):
    """
    Test installing as egg, instead of flat install.
    """
    to_install = data.packages.join("FSPkg")
    result = script.pip('install', to_install, '--egg', expect_error=False)
    fspkg_folder = script.site_packages / 'fspkg'
    egg_folder = script.site_packages / 'FSPkg-0.1.dev0-py%s.egg' % pyversion
    assert fspkg_folder not in result.files_created, str(result.stdout)
    assert egg_folder in result.files_created, str(result)
    assert join(egg_folder, 'fspkg') in result.files_created, str(result)


def test_install_curdir(script, data):
    """
    Test installing current directory ('.').
    """
    run_from = data.packages.join("FSPkg")
    # Python 2.4 Windows balks if this exists already
    egg_info = join(run_from, "FSPkg.egg-info")
    if os.path.isdir(egg_info):
        rmtree(egg_info)
    result = script.pip('install', curdir, cwd=run_from, expect_error=False)
    fspkg_folder = script.site_packages / 'fspkg'
    egg_info_folder = (
        script.site_packages / 'FSPkg-0.1.dev0-py%s.egg-info' % pyversion
    )
    assert fspkg_folder in result.files_created, str(result.stdout)
    assert egg_info_folder in result.files_created, str(result)


def test_install_pardir(script, data):
    """
    Test installing parent directory ('..').
    """
    run_from = data.packages.join("FSPkg", "fspkg")
    result = script.pip('install', pardir, cwd=run_from, expect_error=False)
    fspkg_folder = script.site_packages / 'fspkg'
    egg_info_folder = (
        script.site_packages / 'FSPkg-0.1.dev0-py%s.egg-info' % pyversion
    )
    assert fspkg_folder in result.files_created, str(result.stdout)
    assert egg_info_folder in result.files_created, str(result)


@pytest.mark.network
def test_install_global_option(script):
    """
    Test using global distutils options.
    (In particular those that disable the actual install action)
    """
    result = script.pip(
        'install', '--global-option=--version', "INITools==0.1",
    )
    assert '0.1\n' in result.stdout


def test_install_with_pax_header(script, data):
    """
    test installing from a tarball with pax header for python<2.6
    """
    script.pip('install', 'paxpkg.tar.bz2', cwd=data.packages)


def test_install_with_hacked_egg_info(script, data):
    """
    test installing a package which defines its own egg_info class
    """
    run_from = data.packages.join("HackedEggInfo")
    result = script.pip('install', '.', cwd=run_from)
    assert 'Successfully installed hackedegginfo-0.0.0\n' in result.stdout


@pytest.mark.network
def test_install_using_install_option_and_editable(script, tmpdir):
    """
    Test installing a tool using -e and --install-option
    """
    folder = 'script_folder'
    script.scratch_path.join(folder).mkdir()
    url = 'git+git://github.com/pypa/pip-test-package'
    result = script.pip(
        'install', '-e', '%s#egg=pip-test-package' %
        local_checkout(url, tmpdir.join("cache")),
        '--install-option=--script-dir=%s' % folder
    )
    script_file = (
        script.venv / 'src' / 'pip-test-package' /
        folder / 'pip-test-package' + script.exe
    )
    assert script_file in result.files_created


@pytest.mark.network
def test_install_global_option_using_editable(script, tmpdir):
    """
    Test using global distutils options, but in an editable installation
    """
    url = 'hg+http://bitbucket.org/runeh/anyjson'
    result = script.pip(
        'install', '--global-option=--version', '-e',
        '%s@0.2.5#egg=anyjson' % local_checkout(url, tmpdir.join("cache"))
    )
    assert 'Successfully installed anyjson' in result.stdout


@pytest.mark.network
def test_install_package_with_same_name_in_curdir(script):
    """
    Test installing a package with the same name of a local folder
    """
    script.scratch_path.join("mock==0.6").mkdir()
    result = script.pip('install', 'mock==0.6')
    egg_folder = script.site_packages / 'mock-0.6.0-py%s.egg-info' % pyversion
    assert egg_folder in result.files_created, str(result)


mock100_setup_py = textwrap.dedent('''\
                        from setuptools import setup
                        setup(name='mock',
                              version='100.1')''')


def test_install_folder_using_dot_slash(script):
    """
    Test installing a folder using pip install ./foldername
    """
    script.scratch_path.join("mock").mkdir()
    pkg_path = script.scratch_path / 'mock'
    pkg_path.join("setup.py").write(mock100_setup_py)
    result = script.pip('install', './mock')
    egg_folder = script.site_packages / 'mock-100.1-py%s.egg-info' % pyversion
    assert egg_folder in result.files_created, str(result)


def test_install_folder_using_slash_in_the_end(script):
    r"""
    Test installing a folder using pip install foldername/ or foldername\
    """
    script.scratch_path.join("mock").mkdir()
    pkg_path = script.scratch_path / 'mock'
    pkg_path.join("setup.py").write(mock100_setup_py)
    result = script.pip('install', 'mock' + os.path.sep)
    egg_folder = script.site_packages / 'mock-100.1-py%s.egg-info' % pyversion
    assert egg_folder in result.files_created, str(result)


def test_install_folder_using_relative_path(script):
    """
    Test installing a folder using pip install folder1/folder2
    """
    script.scratch_path.join("initools").mkdir()
    script.scratch_path.join("initools", "mock").mkdir()
    pkg_path = script.scratch_path / 'initools' / 'mock'
    pkg_path.join("setup.py").write(mock100_setup_py)
    result = script.pip('install', Path('initools') / 'mock')
    egg_folder = script.site_packages / 'mock-100.1-py%s.egg-info' % pyversion
    assert egg_folder in result.files_created, str(result)


@pytest.mark.network
def test_install_package_which_contains_dev_in_name(script):
    """
    Test installing package from pypi which contains 'dev' in name
    """
    result = script.pip('install', 'django-devserver==0.0.4')
    devserver_folder = script.site_packages / 'devserver'
    egg_info_folder = (
        script.site_packages / 'django_devserver-0.0.4-py%s.egg-info' %
        pyversion
    )
    assert devserver_folder in result.files_created, str(result.stdout)
    assert egg_info_folder in result.files_created, str(result)


def test_install_package_with_target(script):
    """
    Test installing a package using pip install --target
    """
    target_dir = script.scratch_path / 'target'
    result = script.pip_install_local('-t', target_dir, "simple==1.0")
    assert Path('scratch') / 'target' / 'simple' in result.files_created, (
        str(result)
    )

    # Test repeated call without --upgrade, no files should have changed
    result = script.pip_install_local(
        '-t', target_dir, "simple==1.0", expect_stderr=True,
    )
    assert not Path('scratch') / 'target' / 'simple' in result.files_updated

    # Test upgrade call, check that new version is installed
    result = script.pip_install_local('--upgrade', '-t',
                                      target_dir, "simple==2.0")
    assert Path('scratch') / 'target' / 'simple' in result.files_updated, (
        str(result)
    )
    egg_folder = (
        Path('scratch') / 'target' / 'simple-2.0-py%s.egg-info' % pyversion)
    assert egg_folder in result.files_created, (
        str(result)
    )

    # Test install and upgrade of single-module package
    result = script.pip_install_local('-t', target_dir, 'singlemodule==0.0.0')
    singlemodule_py = Path('scratch') / 'target' / 'singlemodule.py'
    assert singlemodule_py in result.files_created, str(result)

    result = script.pip_install_local('-t', target_dir, 'singlemodule==0.0.1',
                                      '--upgrade')
    assert singlemodule_py in result.files_updated, str(result)


def test_install_package_with_root(script, data):
    """
    Test installing a package using pip install --root
    """
    root_dir = script.scratch_path / 'root'
    result = script.pip(
        'install', '--root', root_dir, '-f', data.find_links, '--no-index',
        'simple==1.0',
    )
    normal_install_path = (
        script.base_path / script.site_packages / 'simple-1.0-py%s.egg-info' %
        pyversion
    )
    # use distutils to change the root exactly how the --root option does it
    from distutils.util import change_root
    root_path = change_root(
        os.path.join(script.scratch, 'root'),
        normal_install_path
    )
    assert root_path in result.files_created, str(result)


# skip on win/py3 for now, see issue #782
@pytest.mark.skipif("sys.platform == 'win32' and sys.version_info >= (3,)")
def test_install_package_that_emits_unicode(script, data):
    """
    Install a package with a setup.py that emits UTF-8 output and then fails.

    Refs https://github.com/pypa/pip/issues/326
    """
    to_install = data.packages.join("BrokenEmitsUTF8")
    result = script.pip(
        'install', to_install, expect_error=True, expect_temp=True, quiet=True,
    )
    assert (
        'FakeError: this package designed to fail on install' in result.stdout
    )
    assert 'UnicodeDecodeError' not in result.stdout


def test_install_package_with_utf8_setup(script, data):
    """Install a package with a setup.py that declares a utf-8 encoding."""
    to_install = data.packages.join("SetupPyUTF8")
    script.pip('install', to_install)


def test_install_package_with_latin1_setup(script, data):
    """Install a package with a setup.py that declares a latin-1 encoding."""
    to_install = data.packages.join("SetupPyLatin1")
    script.pip('install', to_install)


def test_url_req_case_mismatch_no_index(script, data):
    """
    tar ball url requirements (with no egg fragment), that happen to have upper
    case project names, should be considered equal to later requirements that
    reference the project name using lower case.

    tests/data/packages contains Upper-1.0.tar.gz and Upper-2.0.tar.gz
    'requiresupper' has install_requires = ['upper']
    """
    Upper = os.path.join(data.find_links, 'Upper-1.0.tar.gz')
    result = script.pip(
        'install', '--no-index', '-f', data.find_links, Upper, 'requiresupper'
    )

    # only Upper-1.0.tar.gz should get installed.
    egg_folder = script.site_packages / 'Upper-1.0-py%s.egg-info' % pyversion
    assert egg_folder in result.files_created, str(result)
    egg_folder = script.site_packages / 'Upper-2.0-py%s.egg-info' % pyversion
    assert egg_folder not in result.files_created, str(result)


def test_url_req_case_mismatch_file_index(script, data):
    """
    tar ball url requirements (with no egg fragment), that happen to have upper
    case project names, should be considered equal to later requirements that
    reference the project name using lower case.

    tests/data/packages3 contains Dinner-1.0.tar.gz and Dinner-2.0.tar.gz
    'requiredinner' has install_requires = ['dinner']

    This test is similar to test_url_req_case_mismatch_no_index; that test
    tests behaviour when using "--no-index -f", while this one does the same
    test when using "--index-url". Unfortunately this requires a different
    set of packages as it requires a prepared index.html file and
    subdirectory-per-package structure.
    """
    Dinner = os.path.join(data.find_links3, 'Dinner', 'Dinner-1.0.tar.gz')
    result = script.pip(
        'install', '--index-url', data.find_links3, Dinner, 'requiredinner'
    )

    # only Upper-1.0.tar.gz should get installed.
    egg_folder = script.site_packages / 'Dinner-1.0-py%s.egg-info' % pyversion
    assert egg_folder in result.files_created, str(result)
    egg_folder = script.site_packages / 'Dinner-2.0-py%s.egg-info' % pyversion
    assert egg_folder not in result.files_created, str(result)


def test_url_incorrect_case_no_index(script, data):
    """
    Same as test_url_req_case_mismatch_no_index, except testing for the case
    where the incorrect case is given in the name of the package to install
    rather than in a requirements file.
    """
    result = script.pip(
        'install', '--no-index', '-f', data.find_links, "upper",
    )

    # only Upper-2.0.tar.gz should get installed.
    egg_folder = script.site_packages / 'Upper-1.0-py%s.egg-info' % pyversion
    assert egg_folder not in result.files_created, str(result)
    egg_folder = script.site_packages / 'Upper-2.0-py%s.egg-info' % pyversion
    assert egg_folder in result.files_created, str(result)


def test_url_incorrect_case_file_index(script, data):
    """
    Same as test_url_req_case_mismatch_file_index, except testing for the case
    where the incorrect case is given in the name of the package to install
    rather than in a requirements file.
    """
    result = script.pip(
        'install', '--index-url', data.find_links3, "dinner",
        expect_stderr=True,
    )

    # only Upper-2.0.tar.gz should get installed.
    egg_folder = script.site_packages / 'Dinner-1.0-py%s.egg-info' % pyversion
    assert egg_folder not in result.files_created, str(result)
    egg_folder = script.site_packages / 'Dinner-2.0-py%s.egg-info' % pyversion
    assert egg_folder in result.files_created, str(result)


@pytest.mark.network
def test_compiles_pyc(script):
    """
    Test installing with --compile on
    """
    del script.environ["PYTHONDONTWRITEBYTECODE"]
    script.pip("install", "--compile", "--no-binary=:all:", "INITools==0.2")

    # There are many locations for the __init__.pyc file so attempt to find
    #   any of them
    exists = [
        os.path.exists(script.site_packages_path / "initools/__init__.pyc"),
    ]

    exists += glob.glob(
        script.site_packages_path / "initools/__pycache__/__init__*.pyc"
    )

    assert any(exists)


@pytest.mark.network
def test_no_compiles_pyc(script, data):
    """
    Test installing from wheel with --compile on
    """
    del script.environ["PYTHONDONTWRITEBYTECODE"]
    script.pip("install", "--no-compile", "--no-binary=:all:", "INITools==0.2")

    # There are many locations for the __init__.pyc file so attempt to find
    #   any of them
    exists = [
        os.path.exists(script.site_packages_path / "initools/__init__.pyc"),
    ]

    exists += glob.glob(
        script.site_packages_path / "initools/__pycache__/__init__*.pyc"
    )

    assert not any(exists)


def test_install_upgrade_editable_depending_on_other_editable(script):
    script.scratch_path.join("pkga").mkdir()
    pkga_path = script.scratch_path / 'pkga'
    pkga_path.join("setup.py").write(textwrap.dedent("""
        from setuptools import setup
        setup(name='pkga',
              version='0.1')
    """))
    script.pip('install', '--editable', pkga_path)
    result = script.pip('list')
    assert "pkga" in result.stdout

    script.scratch_path.join("pkgb").mkdir()
    pkgb_path = script.scratch_path / 'pkgb'
    pkgb_path.join("setup.py").write(textwrap.dedent("""
        from setuptools import setup
        setup(name='pkgb',
              version='0.1',
              install_requires=['pkga'])
    """))
    script.pip('install', '--upgrade', '--editable', pkgb_path)
    result = script.pip('list')
    assert "pkgb" in result.stdout


def test_install_topological_sort(script, data):
    args = ['install', 'TopoRequires4', '-f', data.packages]
    res = str(script.pip(*args, expect_error=False))
    order1 = 'TopoRequires, TopoRequires2, TopoRequires3, TopoRequires4'
    order2 = 'TopoRequires, TopoRequires3, TopoRequires2, TopoRequires4'
    assert order1 in res or order2 in res, res


def test_install_wheel_broken(script, data):
    script.pip('install', 'wheel')
    res = script.pip(
        'install', '--no-index', '-f', data.find_links, 'wheelbroken',
        expect_stderr=True)
    assert "Successfully installed wheelbroken-0.1" in str(res), str(res)


def test_install_builds_wheels(script, data):
    # NB This incidentally tests a local tree + tarball inputs
    # see test_install_editable_from_git_autobuild_wheel for editable
    # vcs coverage.
    script.pip('install', 'wheel')
    to_install = data.packages.join('requires_wheelbroken_upper')
    res = script.pip(
        'install', '--no-index', '-f', data.find_links,
        to_install, expect_stderr=True)
    expected = ("Successfully installed requires-wheelbroken-upper-0"
                " upper-2.0 wheelbroken-0.1")
    # Must have installed it all
    assert expected in str(res), str(res)
    root = appdirs.user_cache_dir('pip')
    wheels = []
    for top, dirs, files in os.walk(root):
        wheels.extend(files)
    # and built wheels for upper and wheelbroken
    assert "Running setup.py bdist_wheel for upper" in str(res), str(res)
    assert "Running setup.py bdist_wheel for wheelb" in str(res), str(res)
    # But not requires_wheel... which is a local dir and thus uncachable.
    assert "Running setup.py bdist_wheel for requir" not in str(res), str(res)
    # wheelbroken has to run install
    # into the cache
    assert wheels != [], str(res)
    # and installed from the wheel
    assert "Running setup.py install for upper" not in str(res), str(res)
    # the local tree can't build a wheel (because we can't assume that every
    # build will have a suitable unique key to cache on).
    assert "Running setup.py install for requires-wheel" in str(res), str(res)
    # wheelbroken has to run install
    assert "Running setup.py install for wheelb" in str(res), str(res)


def test_install_no_binary_disables_building_wheels(script, data):
    script.pip('install', 'wheel')
    to_install = data.packages.join('requires_wheelbroken_upper')
    res = script.pip(
        'install', '--no-index', '--no-binary=upper', '-f', data.find_links,
        to_install, expect_stderr=True)
    expected = ("Successfully installed requires-wheelbroken-upper-0"
                " upper-2.0 wheelbroken-0.1")
    # Must have installed it all
    assert expected in str(res), str(res)
    root = appdirs.user_cache_dir('pip')
    wheels = []
    for top, dirs, files in os.walk(root):
        wheels.extend(files)
    # and built wheels for wheelbroken only
    assert "Running setup.py bdist_wheel for wheelb" in str(res), str(res)
    # But not requires_wheel... which is a local dir and thus uncachable.
    assert "Running setup.py bdist_wheel for requir" not in str(res), str(res)
    # Nor upper, which was blacklisted
    assert "Running setup.py bdist_wheel for upper" not in str(res), str(res)
    # wheelbroken has to run install
    # into the cache
    assert wheels != [], str(res)
    # the local tree can't build a wheel (because we can't assume that every
    # build will have a suitable unique key to cache on).
    assert "Running setup.py install for requires-wheel" in str(res), str(res)
    # And these two fell back to sdist based installed.
    assert "Running setup.py install for wheelb" in str(res), str(res)
    assert "Running setup.py install for upper" in str(res), str(res)


def test_install_no_binary_disables_cached_wheels(script, data):
    script.pip('install', 'wheel')
    # Seed the cache
    script.pip(
        'install', '--no-index', '-f', data.find_links,
        'upper')
    script.pip('uninstall', 'upper', '-y')
    res = script.pip(
        'install', '--no-index', '--no-binary=:all:', '-f', data.find_links,
        'upper', expect_stderr=True)
    assert "Successfully installed upper-2.0" in str(res), str(res)
    # No wheel building for upper, which was blacklisted
    assert "Running setup.py bdist_wheel for upper" not in str(res), str(res)
    # Must have used source, not a cached wheel to install upper.
    assert "Running setup.py install for upper" in str(res), str(res)
