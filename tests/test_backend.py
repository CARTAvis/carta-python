import os
import subprocess

import pytest

from carta.backend import Backend
from carta import backend as backend_module


@pytest.fixture
def launch_home(tmp_path, mocker, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    mocker.patch("carta.backend.pathlib.Path.home", return_value=home)
    mocker.patch("carta.backend._MACOS_APP_EXECUTABLE", tmp_path / "system/Applications/CARTA.app/Contents/MacOS/CARTA")
    monkeypatch.setattr("carta.backend.sys.platform", "darwin")
    monkeypatch.setenv("PATH", str(tmp_path / "empty-path"))
    return home


@pytest.fixture
def popen(mocker):
    process = mocker.Mock()
    process.stdout.readline.return_value = b""
    process.poll.return_value = 0
    mocker.patch("carta.backend.os.set_blocking")
    return mocker.patch("carta.backend.subprocess.Popen", return_value=process)


def make_executable(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/sh\nexit 0\n")
    path.chmod(0o755)
    return path


@pytest.mark.parametrize("command", [
    "default", "absolute_symlink", "chained_symlink", "absolute_executable",
    "relative_symlink", "relative_executable",
])
def test_start_resolves_macos_executable(command, launch_home, popen, monkeypatch):
    executable = make_executable(launch_home / "Applications/CARTA Test.app/Contents/MacOS/CARTA")
    bin_dir = launch_home / "bin"
    bin_dir.mkdir()
    link = bin_dir / "carta"
    link.symlink_to(executable)
    chain = bin_dir / "carta-chain"
    chain.symlink_to("carta")
    monkeypatch.setenv("PATH", "bin")
    commands = {
        "default": "carta",
        "absolute_symlink": str(link),
        "chained_symlink": str(chain),
        "absolute_executable": str(executable),
        "relative_symlink": "bin/carta",
        "relative_executable": "Applications/CARTA Test.app/Contents/MacOS/CARTA",
    }
    backend = Backend(("--enable_scripting", "--verbosity", 5), executable_path=commands[command])

    assert backend.start() is False

    popen.assert_called_once_with(
        (str(executable), "--enable_scripting", "--verbosity", "5"),
        stdout=subprocess.PIPE,
        cwd=launch_home,
        preexec_fn=os.setpgrp,
    )


@pytest.mark.parametrize("path_kind", ["absolute", "relative", "empty", "unset"])
def test_start_resolves_macos_path_entries(path_kind, launch_home, popen, monkeypatch):
    executable = make_executable(launch_home / "CARTA.app/Contents/MacOS/CARTA")
    bin_dir = launch_home if path_kind == "empty" else launch_home / "bin"
    bin_dir.mkdir(exist_ok=True)
    (bin_dir / "carta").symlink_to(executable)
    if path_kind == "unset":
        monkeypatch.delenv("PATH", raising=False)
        monkeypatch.setattr(os, "defpath", str(bin_dir))
    else:
        monkeypatch.setenv("PATH", {"absolute": str(bin_dir), "relative": "bin", "empty": ""}[path_kind])
    backend = Backend(())

    assert backend.start() is False

    assert popen.call_args.args[0] == (str(executable),)
    assert popen.call_args.kwargs["cwd"] == launch_home


def test_start_keeps_macos_path_search_order(launch_home, popen, monkeypatch):
    first = make_executable(launch_home / "first/carta")
    make_executable(launch_home / "second/carta")
    monkeypatch.setenv("PATH", os.pathsep.join(("first", "second")))

    Backend(()).start()

    assert popen.call_args.args[0] == (str(first),)


def test_start_finds_macos_app_without_alias(launch_home, popen):
    system_app = make_executable(backend_module._MACOS_APP_EXECUTABLE)

    assert Backend(("--enable_scripting",)).start() is False

    popen.assert_called_once_with(
        (str(system_app), "--enable_scripting"),
        stdout=subprocess.PIPE,
        cwd=launch_home,
        preexec_fn=os.setpgrp,
    )


def test_start_prefers_macos_app_to_path(launch_home, popen, monkeypatch):
    system_app = make_executable(backend_module._MACOS_APP_EXECUTABLE)
    make_executable(launch_home / "bin/carta")
    monkeypatch.setenv("PATH", "bin")

    Backend(()).start()

    assert popen.call_args.args[0] == (str(system_app),)


@pytest.mark.parametrize("definition", [
    "alias carta='{path}'",
    '  alias carta="{path}" # custom CARTA installation',
    "alias carta='{path}'; # custom CARTA installation",
    "alias carta='{path}'; export CARTA_HOME=/tmp",
    "export CARTA_HOME=/tmp; alias carta='{path}'",
    "alias ll='ls -l' carta='{path}'",
])
def test_start_prefers_custom_carta_alias(definition, launch_home, popen, monkeypatch):
    executable = make_executable(launch_home / "Apps/CARTA 2.app/Contents/MacOS/CARTA")
    alias_path = launch_home / "custom-carta"
    alias_path.symlink_to(executable)
    (launch_home / ".zshrc").write_text(
        "# unrelated shell configuration\nalias ls='ls -l'\n"
        + definition.format(path=alias_path) + "\n"
    )
    make_executable(backend_module._MACOS_APP_EXECUTABLE)
    make_executable(launch_home / "bin/carta")
    monkeypatch.setenv("PATH", "bin")

    Backend(("--enable_scripting",)).start()

    popen.assert_called_once_with(
        (str(executable), "--enable_scripting"),
        stdout=subprocess.PIPE,
        cwd=launch_home,
        preexec_fn=os.setpgrp,
    )


def test_start_reads_alias_path_with_spaces(launch_home, popen):
    executable = make_executable(launch_home / "Apps/CARTA 2.app/Contents/MacOS/CARTA")
    (launch_home / ".zshrc").write_text(f"alias carta='{executable}'\n")

    Backend(()).start()

    assert popen.call_args.args[0] == (str(executable),)


def test_start_expands_home_in_alias(launch_home, popen):
    executable = make_executable(launch_home / "Applications/CARTA.app/Contents/MacOS/CARTA")
    make_executable(backend_module._MACOS_APP_EXECUTABLE)
    (launch_home / ".zshrc").write_text("alias carta='~/Applications/CARTA.app/Contents/MacOS/CARTA'\n")

    Backend(()).start()

    assert popen.call_args.args[0] == (str(executable),)


def test_start_passes_browser_mode_alias_arguments(launch_home, popen):
    app = launch_home / "CARTA 6.app/Contents/Resources/app"
    backend_executable = make_executable(app / "carta-backend/bin/carta_backend")
    make_executable(backend_module._MACOS_APP_EXECUTABLE)
    (launch_home / ".zshrc").write_text(
        f"alias carta=\"'{backend_executable}' --frontend_folder '{app}/'\"\n"
    )

    Backend(("--enable_scripting", "--verbosity", 5)).start()

    popen.assert_called_once_with(
        (str(backend_executable), "--frontend_folder", f"{app}/", "--enable_scripting", "--verbosity", "5"),
        stdout=subprocess.PIPE,
        cwd=launch_home,
        preexec_fn=os.setpgrp,
    )


def test_start_expands_home_in_alias_arguments(launch_home, popen):
    backend_executable = make_executable(launch_home / "CARTA.app/Contents/Resources/app/carta-backend/bin/carta_backend")
    (launch_home / ".zshrc").write_text(
        "alias carta='~/CARTA.app/Contents/Resources/app/carta-backend/bin/carta_backend"
        " --frontend_folder ~/CARTA.app/Contents/Resources/app/'\n"
    )

    Backend(()).start()

    assert popen.call_args.args[0] == (
        str(backend_executable), "--frontend_folder", f"{launch_home}/CARTA.app/Contents/Resources/app/",
    )


def test_start_resolves_alias_executable_with_arguments(launch_home, popen):
    executable = make_executable(launch_home / "CARTA.app/Contents/MacOS/CARTA")
    link = launch_home / "carta-link"
    link.symlink_to(executable)
    (launch_home / ".zshrc").write_text(f"alias carta='{link} --debug'\n")

    Backend(()).start()

    assert popen.call_args.args[0] == (str(executable), "--debug")


@pytest.mark.parametrize("executable", ["missing", "relative"])
def test_start_skips_unusable_alias_with_arguments(executable, launch_home, popen):
    system_app = make_executable(backend_module._MACOS_APP_EXECUTABLE)
    path = "/missing/carta_backend" if executable == "missing" else "bin/carta_backend"
    make_executable(launch_home / "bin/carta_backend")
    (launch_home / ".zshrc").write_text(f"alias carta='{path} --frontend_folder /tmp'\n")

    Backend(()).start()

    assert popen.call_args.args[0] == (str(system_app),)


def test_start_uses_last_alias_definition(launch_home, popen):
    first = make_executable(launch_home / "CARTA1.app/Contents/MacOS/CARTA")
    last = make_executable(launch_home / "CARTA2.app/Contents/MacOS/CARTA")
    (launch_home / ".zshrc").write_text(f"alias carta='{first}'\nalias carta={last}\n")

    Backend(()).start()

    assert popen.call_args.args[0] == (str(last),)


@pytest.mark.parametrize("invalid_app", ["missing", "directory", "not_executable", "broken_symlink"])
def test_start_skips_unusable_carta_alias(invalid_app, launch_home, popen):
    alias_path = launch_home / "CARTA2.app/Contents/MacOS/CARTA"
    (launch_home / ".zshrc").write_text(f"alias carta='{alias_path}'\n")
    if invalid_app == "directory":
        alias_path.mkdir(parents=True)
    elif invalid_app == "not_executable":
        make_executable(alias_path).chmod(0o644)
    elif invalid_app == "broken_symlink":
        alias_path.parent.mkdir(parents=True)
        alias_path.symlink_to("missing-executable")
    system_app = make_executable(backend_module._MACOS_APP_EXECUTABLE)

    Backend(()).start()

    assert popen.call_args.args[0] == (str(system_app),)


@pytest.mark.parametrize("configuration", [
    "# alias carta='{path}'",
    "alias carta='{path}",
    "alias carta='$CARTA_EXECUTABLE'",
    "alias carta='$(echo {path})'",
    "alias carta='{path} $FRONTEND_FOLDER'",
    "alias carta='{path} --verbosity 5 | tee carta.log'",
    "alias carta='{path} --frontend_folder *'",
    "alias carta='{path} \"unterminated'",
    "alias carta='relative/CARTA'",
    "if true; then alias carta='{path}'; fi",
    "alias carta='{path}'\nunalias carta",
    "alias carta='{path}'; unalias carta",
    "alias carta='{path}'\nunalias -a",
    "alias carta='~user/CARTA'",
    "alias carta='{path}'\nalias carta='/missing/CARTA'",
])
def test_start_falls_back_for_unsupported_alias(configuration, launch_home, popen):
    custom_app = make_executable(launch_home / "CARTA2.app/Contents/MacOS/CARTA")
    system_app = make_executable(backend_module._MACOS_APP_EXECUTABLE)
    (launch_home / ".zshrc").write_text(configuration.format(path=custom_app) + "\n")

    Backend(()).start()

    assert popen.call_args.args[0] == (str(system_app),)


@pytest.mark.parametrize("configuration", ["directory", "invalid_encoding"])
def test_start_falls_back_for_unreadable_zshrc(configuration, launch_home, popen):
    system_app = make_executable(backend_module._MACOS_APP_EXECUTABLE)
    zshrc = launch_home / ".zshrc"
    if configuration == "directory":
        zshrc.mkdir()
    else:
        zshrc.write_bytes(b"\xff")

    Backend(()).start()

    assert popen.call_args.args[0] == (str(system_app),)


def test_start_uses_explicit_executable_before_alias(launch_home, popen):
    explicit = make_executable(launch_home / "explicit/CARTA")
    custom_app = make_executable(launch_home / "CARTA2.app/Contents/MacOS/CARTA")
    make_executable(backend_module._MACOS_APP_EXECUTABLE)
    (launch_home / ".zshrc").write_text(f"alias carta='{custom_app}'\n")

    Backend((), executable_path=str(explicit)).start()

    assert popen.call_args.args[0] == (str(explicit),)


@pytest.mark.parametrize("filename", [".bash_profile", ".bash_login", ".profile", ".bashrc"])
def test_start_reads_bash_alias_configuration(filename, launch_home, popen):
    executable = make_executable(launch_home / "CARTA2.app/Contents/MacOS/CARTA")
    (launch_home / filename).write_text(f"alias carta='{executable}'\n")
    make_executable(backend_module._MACOS_APP_EXECUTABLE)

    Backend(()).start()

    assert popen.call_args.args[0] == (str(executable),)


def test_start_prefers_first_bash_login_profile(launch_home, popen):
    executables = []
    for index, filename in enumerate((".bash_profile", ".bash_login", ".profile", ".bashrc")):
        executable = make_executable(launch_home / f"CARTA{index}.app/Contents/MacOS/CARTA")
        executables.append(executable)
        (launch_home / filename).write_text(f"alias carta='{executable}'\n")

    Backend(()).start()

    assert popen.call_args.args[0] == (str(executables[0]),)


@pytest.mark.parametrize("profile_content", ["# no CARTA alias", "alias carta='/missing/CARTA'"])
def test_start_searches_bashrc_after_selected_profile(profile_content, launch_home, popen):
    ignored = make_executable(launch_home / "ignored/CARTA")
    executable = make_executable(launch_home / "bashrc/CARTA")
    (launch_home / ".bash_profile").write_text(profile_content + "\n")
    (launch_home / ".bash_login").write_text(f"alias carta='{ignored}'\n")
    (launch_home / ".bashrc").write_text(f"alias carta='{executable}'\n")

    Backend(()).start()

    assert popen.call_args.args[0] == (str(executable),)


def test_start_prefers_zshrc_to_bash_configuration(launch_home, popen, monkeypatch):
    zsh_executable = make_executable(launch_home / "zsh/CARTA")
    (launch_home / ".zshrc").write_text(f"alias carta='{zsh_executable}'\n")
    bash_executable = make_executable(launch_home / "bash/CARTA")
    (launch_home / ".bash_profile").write_text(f"alias carta='{bash_executable}'\n")
    (launch_home / ".bashrc").write_text(f"alias carta='{bash_executable}'\n")
    make_executable(backend_module._MACOS_APP_EXECUTABLE)
    monkeypatch.setenv("SHELL", "/bin/bash")

    Backend(()).start()

    assert popen.call_args.args[0] == (str(zsh_executable),)


@pytest.mark.parametrize("shell", ["/bin/zsh", "/bin/bash", "/usr/local/bin/fish", None])
def test_start_discovers_alias_independently_of_shell(shell, launch_home, popen, monkeypatch):
    executable = make_executable(launch_home / "bashrc/CARTA")
    (launch_home / ".bashrc").write_text(f"alias carta='{executable}'\n")
    make_executable(backend_module._MACOS_APP_EXECUTABLE)
    if shell is None:
        monkeypatch.delenv("SHELL", raising=False)
    else:
        monkeypatch.setenv("SHELL", shell)

    Backend(()).start()

    assert popen.call_args.args[0] == (str(executable),)


def test_start_preserves_missing_default_error(launch_home, popen, monkeypatch):
    monkeypatch.setenv("PATH", "")
    popen.side_effect = FileNotFoundError(2, "No such file or directory", "carta")

    with pytest.raises(FileNotFoundError) as error:
        Backend(()).start()

    assert error.value.filename == "carta"
    assert popen.call_args.args[0] == ("carta",)


@pytest.mark.parametrize("executable", ["custom-carta", "./missing-carta"])
def test_start_does_not_replace_custom_executable(executable, launch_home, popen, monkeypatch):
    make_executable(backend_module._MACOS_APP_EXECUTABLE)
    (launch_home / ".zshrc").write_text(f"alias carta='{backend_module._MACOS_APP_EXECUTABLE}'\n")
    monkeypatch.setenv("PATH", "")
    popen.side_effect = FileNotFoundError(2, "No such file or directory", executable)

    with pytest.raises(FileNotFoundError):
        Backend((), executable_path=executable).start()

    expected = str(launch_home / "missing-carta") if executable.startswith("./") else executable
    assert popen.call_args.args[0] == (expected,)


def test_start_preserves_missing_executable_error(launch_home, popen, monkeypatch):
    monkeypatch.setenv("PATH", "")
    popen.side_effect = FileNotFoundError(2, "No such file or directory", "missing-carta")
    backend = Backend((), executable_path="missing-carta")

    with pytest.raises(FileNotFoundError) as error:
        backend.start()

    assert error.value.filename == "missing-carta"
    assert popen.call_args.args[0] == ("missing-carta",)


@pytest.mark.parametrize("platform,remote_host,expected", [
    ("linux", None, ("carta", "--enable_scripting")),
    ("darwin", "server", ("ssh", "-tt", "server", "carta", "--enable_scripting")),
    ("darwin", "server", ("ssh", "-tt", "server", "/remote/CARTA", "--enable_scripting")),
])
def test_start_preserves_other_launch_commands(platform, remote_host, expected, launch_home, popen, monkeypatch, mocker):
    monkeypatch.setattr("carta.backend.sys.platform", platform)
    resolve = mocker.patch("carta.backend._resolve_local_executable", side_effect=AssertionError("Local resolution is unexpected"))
    executable = expected[-2]
    backend = Backend(("--enable_scripting",), executable_path=executable, remote_host=remote_host)

    assert backend.start() is False

    resolve.assert_not_called()
    popen.assert_called_once_with(expected, stdout=subprocess.PIPE, cwd=launch_home, preexec_fn=os.setpgrp)
