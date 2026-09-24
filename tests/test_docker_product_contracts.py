"""Static contracts for the bounded local Docker MVP topology."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_docker_01_05_compose_has_only_product_and_database_services() -> None:
    compose = (PROJECT_ROOT / "compose.yaml").read_text(encoding="utf-8")
    assert "  postgres:" in compose
    assert "  app:" in compose
    for prohibited in ("redis:", "worker:", "scheduler:", "proxy:"):
        assert prohibited not in compose
    assert "condition: service_healthy" in compose
    assert "127.0.0.1:8000:8000" in compose


def test_docker_03_04_startup_is_migration_first_and_idempotent() -> None:
    startup = (PROJECT_ROOT / "docker" / "start_app.py").read_text(
        encoding="utf-8"
    )
    assert 'REQUIRED_LOCAL_DATABASES = ("spg_dev", "spg_test")' in startup
    assert "SELECT 1 FROM pg_database" in startup
    assert '"upgrade", "head"' in startup
    assert startup.index("migrate_product_database()") < startup.index("os.execvpe(")
    assert "RuntimeNotBootstrapped" in startup
    assert "default_resource()" in startup
    assert 'SOURCE_REPOSITORY / ".git"' in startup
    assert '"safe.directory"' in startup
    assert "synchronize_repository_checkout(repository)" in startup
    assert startup.index("synchronize_repository_checkout(repository)") < startup.index(
        "ensure_local_product_foundation(repository)"
    )
    assert startup.index("synchronize_repository_checkout(repository)") < startup.index(
        "prepare_local_runtime_activation(repository)"
    )
    assert "SPG_ACTIVE_RUNTIME_STATIC_ASSET_FINGERPRINT" in startup
    assert "REPOSITORY_CHECKOUT_DIVERGENCE" in startup


def test_docker_13_14_18_19_20_configuration_preserves_boundaries() -> None:
    compose = (PROJECT_ROOT / "compose.yaml").read_text(encoding="utf-8")
    dockerfile = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")
    ignore = (PROJECT_ROOT / ".dockerignore").read_text(encoding="utf-8")
    assert "/spg_dev?" in compose
    assert "SPG_TEST_DATABASE_URL" not in compose
    assert "spg_runtime" not in compose
    assert "OPENAI_API_KEY" not in compose
    assert "CODEX_HOME" not in compose
    assert "target: runtime" in compose
    assert dockerfile.rstrip().endswith("FROM runtime-base AS runtime")
    assert "RUN uv sync --locked --no-dev --no-editable\n" in dockerfile
    assert "npm" not in dockerfile
    assert ".git" in ignore
    assert ".env" in ignore
    assert "tests" in ignore


def test_docker_07_08_image_contains_server_migrations_and_packaged_ui() -> None:
    dockerfile = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")
    project = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "uv sync --locked" in dockerfile
    assert "COPY migrations ./migrations" in dockerfile
    assert 'CMD ["python", "/app/docker/start_app.py"]' in dockerfile
    assert (
        "uv sync --locked --no-dev --no-editable "
        "--extra test"
    ) in dockerfile
    assert '"spg.web" = ["*.html", "*.css", "*.js"]' in project


def test_uncommitted_qualification_is_explicit_and_keeps_normal_activation() -> None:
    normal = (PROJECT_ROOT / "docker" / "start_app.py").read_text(encoding="utf-8")
    review = (PROJECT_ROOT / "docker" / "start_uncommitted_qualification.py").read_text(
        encoding="utf-8"
    )
    overlay = (PROJECT_ROOT / "compose.uncommitted-qualification.yaml").read_text(
        encoding="utf-8"
    )
    native = (PROJECT_ROOT / "compose.native-executor.yaml").read_text(
        encoding="utf-8"
    )
    assert "prepare_local_runtime_activation(repository)" in normal
    assert "SPG_RUNTIME_PROFILE" in review
    assert '"uncommitted-qualification"' in review
    assert "migrate_product_database()" in review
    assert "prepare_local_runtime_activation" not in review
    assert "start_uncommitted_qualification.py" in overlay
    assert "SPG_NATIVE_EXECUTOR_PRODUCTION_ENVIRONMENT_WORKSPACE_VOLUME:-watt-native-workspaces" in native
