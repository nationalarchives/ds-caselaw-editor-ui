import os
import signal
import subprocess
from contextlib import contextmanager, suppress
from pathlib import Path

from invoke import run as local
from invoke.exceptions import UnexpectedExit
from invoke.tasks import task

# Process .env file
if os.path.exists(".env"):
    with open(".env") as f:
        for line in f:
            if not line or line.startswith("#") or "=" not in line:
                continue
            var, value = line.strip().split("=", 1)
            os.environ.setdefault(var, value)


LOCAL_DATABASE_NAME = os.getenv("POSTGRES_DB")
LOCAL_DATABASE_USERNAME = os.getenv("POSTGRES_USER")
LOCAL_DB_DUMP_DIR = "database_dumps"


def _marklogic_repo_path() -> Path:
    if env_path := os.getenv("CASELAW_MARKLOGIC_PATH"):
        return Path(env_path).expanduser()
    candidates = [
        Path(__file__).resolve().parent.parent / "ds-caselaw-marklogic",
        Path("~/repositories/github.com/nationalarchives/ds-caselaw-marklogic").expanduser(),
    ]
    for candidate in candidates:
        if (candidate / "build.gradle").is_file():
            return candidate.resolve()
    return candidates[0].resolve()


def _api_client_repo_path() -> Path:
    if env_path := os.getenv("CASELAW_API_CLIENT_PATH"):
        return Path(env_path).expanduser()
    candidates = [
        Path(__file__).resolve().parent.parent / "ds-caselaw-custom-api-client",
        Path("/apiclient"),
        Path("~/repositories/github.com/nationalarchives/ds-caselaw-custom-api-client").expanduser(),
    ]
    for candidate in candidates:
        script = candidate / "script" / "create_marklogic_test_user"
        if script.is_file():
            return candidate.resolve()
    message = (
        "Could not find ds-caselaw-custom-api-client (script/create_marklogic_test_user). "
        "Set CASELAW_API_CLIENT_PATH or mount the repo at ../ds-caselaw-custom-api-client."
    )
    raise SystemExit(message)


def _create_local_marklogic_test_user(marklogic_repo: Path) -> None:
    """Create a non-admin MarkLogic user with caselaw-editor-ui roles (required for TDE SQL)."""
    script = _api_client_repo_path() / "script" / "create_marklogic_test_user"
    test_user = os.getenv("MARKLOGIC_USER", "caselaw-api-client-test")
    test_password = os.getenv("MARKLOGIC_PASSWORD", "local-marklogic-dev")
    manage_url = os.getenv("MARKLOGIC_MANAGE_URL", "http://127.0.0.1:8002")
    admin_user = os.getenv("MARKLOGIC_ADMIN_USER", "admin")
    admin_password = os.getenv("MARKLOGIC_ADMIN_PASSWORD", "admin")
    local(
        f"MARKLOGIC_USER={test_user} MARKLOGIC_PASSWORD={test_password} "
        f"MARKLOGIC_MANAGE_URL={manage_url} MARKLOGIC_ADMIN_USER={admin_user} "
        f"MARKLOGIC_ADMIN_PASSWORD={admin_password} {script} {marklogic_repo}",
    )


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def container_exec(cmd, container_name="django", check_returncode=False):
    result = subprocess.run(
        ["docker", "compose", "exec", "-T", container_name, "bash", "-c", cmd],
    )
    if check_returncode:
        result.check_returncode()
    return result


@contextmanager
def background_exec(cmd, logfile):
    """Run a child process for the duration of a task, capturing its logs."""
    with open(f"{logfile}.log", "w") as output:
        process = subprocess.Popen(
            cmd,
            stdout=output,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )

        try:
            yield process
        finally:
            # npm spawns Node, so stop the whole group rather than just npm.
            with suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGTERM)

            try:
                with suppress(subprocess.TimeoutExpired):
                    process.wait(timeout=5)
            finally:
                with suppress(ProcessLookupError):
                    os.killpg(process.pid, signal.SIGKILL)

                process.wait()


@contextmanager
def run_lifecycle(c):
    """Handle termination signals and stop services when `run` exits."""
    shutting_down = False

    def terminate(signum, frame):
        nonlocal shutting_down

        # Do not let a second signal interrupt cleanup.
        if shutting_down:
            return

        shutting_down = True
        raise SystemExit(128 + signum)

    signals = (signal.SIGTERM, signal.SIGHUP)
    previous_handlers = {sig: signal.signal(sig, terminate) for sig in signals}

    try:
        yield
    finally:
        shutting_down = True
        try:
            stop(c)
        finally:
            for sig, handler in previous_handlers.items():
                signal.signal(sig, handler)


def postgres_exec(cmd, check_returncode=False):
    "Execute something in the 'postgres' Docker container."
    return container_exec(cmd, "postgres", check_returncode)


def django_exec(cmd, check_returncode=False):
    "Execute something in the 'django' Docker container."
    return container_exec(cmd, "django", check_returncode)


# -----------------------------------------------------------------------------
# Container management
# -----------------------------------------------------------------------------


@task
def build(c):
    """
    Build (or rebuild) local development containers.
    """
    local("docker compose build")


@task
def start(c, container_name=None):
    """
    Start the local development environment.
    """
    cmd = "docker compose up -d"
    if container_name:
        cmd += f" {container_name}"
    local(cmd)


@task
def npm_install(c):
    """
    Install NPM packages and build frontend assets for local dev.
    """
    local("npm install")
    local("npm run build")


@task(optional=["noinput"])
def reset_fixtures(c, noinput=""):
    """
    Reload the MarkLogic test document corpus from the API client harness (local MarkLogic only).
    """
    flag = " --noinput" if noinput else ""
    django_exec(f"python manage.py reset_local_fixtures{flag}", check_returncode=True)


@task
def deploy_marklogic(c):
    """
    Deploy the caselaw MarkLogic application (same as API client CI integration tests).
    """
    marklogic_repo = _marklogic_repo_path()
    if not (marklogic_repo / "build.gradle").is_file():
        print(
            f"Could not find ds-caselaw-marklogic at {marklogic_repo}. Set CASELAW_MARKLOGIC_PATH to your checkout.",
        )
        raise SystemExit(1)

    local("docker network create caselaw || true")
    local(
        f"cd {marklogic_repo} && gradle mlWaitTillReady mlDeploy mlDeployViewSchemas mlReloadSchemas -PmlDatabaseNamesAndReplicaCounts=",
    )
    _create_local_marklogic_test_user(marklogic_repo)


@task
def collectstatic(c):
    """
    Update static assets
    """
    django_exec("rm -rf /app/staticfiles")
    django_exec("python manage.py collectstatic")


@task
def run(c):
    with run_lifecycle(c):
        try:
            start(c, "django")
            npm_install(c)

            with background_exec(["npm", "run", "watch"], "assets"):
                django_exec("pip install -r requirements/local.txt -U")
                django_exec("python manage.py migrate")
                collectstatic(c)

                try:
                    local("docker logs marklogic > marklogic.log")
                except UnexpectedExit:
                    print("Unable to collect MarkLogic logs!")

                django_exec("python manage.py runserver 0.0.0.0:3000")

        except KeyboardInterrupt:
            pass


@task
def stop(c, container_name=None):
    """
    Stop the local development environment.
    """
    cmd = "docker compose stop"
    if container_name:
        cmd += f" {container_name}"
    local(cmd)


@task
def restart(c):
    """
    Restart the local development environment.
    """
    stop(c)
    start(c)


@task
def sh(c):
    """
    Run bash in a local container (with access to dependencies)
    """
    subprocess.run(["docker", "compose", "exec", "django", "bash"])


@task
def type(c):  # noqa: A001
    """
    Run python tests in the web container
    """
    # Static analysis
    subprocess.run(
        [
            "docker",
            "compose",
            "exec",
            "django",
            "mypy",
            "ds_caselaw_editor_ui",
            "judgments",
        ],
    )


@task(optional=["test"])
def test(c, test=None):  # noqa: PT028
    """
    Run python tests in the web container
    """

    # Static analysis
    subprocess.run(
        [
            "docker",
            "compose",
            "exec",
            "django",
            "mypy",
            "ds_caselaw_editor_ui",
            "judgments",
        ],
    )
    # Pytest
    command = [
        "docker",
        "compose",
        "exec",
        "django",
        "pytest",
        "-v",
    ]
    if test:
        command.append(test)
    subprocess.run(command)


# -----------------------------------------------------------------------------
# Database operations
# -----------------------------------------------------------------------------


@task
def psql(c, command=None):
    """
    Connect to the local postgres DB using psql
    """
    cmd_list = [
        "docker",
        "compose",
        "exec",
        "postgres",
        "psql",
        *["-d", LOCAL_DATABASE_NAME],
        *["-U", LOCAL_DATABASE_USERNAME],
    ]
    if command:
        cmd_list.extend(["-c", command])

    subprocess.run(cmd_list)


def delete_db(c):
    postgres_exec(
        f"dropdb --if-exists --host db --username={LOCAL_DATABASE_USERNAME} {LOCAL_DATABASE_NAME}",
    )
    postgres_exec(
        f"createdb --host db --username={LOCAL_DATABASE_USERNAME} {LOCAL_DATABASE_NAME}",
    )


@task
def dump_db(c, filename):
    """Snapshot the database, files will be stored in the db container"""
    if not filename.endswith(".dmp"):
        filename += ".dmp"
    postgres_exec(
        f"pg_dump -d {LOCAL_DATABASE_NAME} -U {LOCAL_DATABASE_USERNAME} > {filename}",
    )
    print(f"Database dumped to: {filename}")


@task
def restore_db(c, filename, delete_dump_on_success=False, delete_dump_on_error=False):
    """Restore the database from a snapshot in the db container"""
    print("Stopping 'web' to sever DB connection")
    stop(c, "django")
    if not filename.endswith(".dmp"):
        filename += ".dmp"
    delete_db(c)

    try:
        print(f"Restoring datbase from: {filename}")
        postgres_exec(
            f"psql -d {LOCAL_DATABASE_NAME} -U {LOCAL_DATABASE_USERNAME} < {filename}",
            check_returncode=True,
        )
    except subprocess.CalledProcessError:
        if delete_dump_on_error:
            postgres_exec(f"rm {filename}")
        raise

    if delete_dump_on_success:
        print(f"Deleting dump file: {filename}")
        postgres_exec(f"rm {filename}")

    start(c, "django")


@task(optional=["baseUrl", "regenerateSnapshots", "testPath"])
def e2etest(c, baseUrl="http://django:3000", regenerateSnapshots="false", testPath=None):
    """
    Run end-to-end playwright tests against the given base url -
    the default is the running local django web container.
    """
    subprocess.run(
        [
            "docker",
            "compose",
            "build",
            "e2e_tests",
        ],
    )

    pytest_cmd = [
        "pytest",
        "--base-url",
        baseUrl,
    ]

    if testPath:
        pytest_cmd.append(testPath)

    subprocess.run(
        [
            "docker",
            "compose",
            "run",
            "--rm",
            "-e",
            f"E2E_REGENERATE_SNAPSHOTS={regenerateSnapshots}",
            "e2e_tests",
            *pytest_cmd,
        ],
    )
