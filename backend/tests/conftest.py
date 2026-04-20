import os

from migrate_util import configure_default_test_env, run_alembic_upgrade

configure_default_test_env()
run_alembic_upgrade(os.environ["DATABASE_URL"])
