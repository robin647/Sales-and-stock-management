"""Reconcile the known legacy inventory migration without deleting stock."""

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, migrations, transaction
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.recorder import MigrationRecorder


TARGET = ("inventory", "0002_factorystock_showroomstock_stockadjustment_and_more")
LEGACY = ("inventory", "0002_factorystock_showroomstock_stocktransfer")


class Command(BaseCommand):
    help = "Validate legacy stock tables, create missing StockAdjustment, and reconcile migration history."

    def handle(self, *args, **options):
        loader = MigrationLoader(connection)
        if TARGET in loader.applied_migrations:
            self.stdout.write("Inventory migration is already applied; no changes made.")
            return
        if LEGACY not in loader.applied_migrations:
            raise CommandError("Known legacy migration not found. Run normal migrate instead.")
        if connection.vendor != "postgresql":
            raise CommandError("Legacy inventory repair supports PostgreSQL only.")
        migration = loader.get_migration(*TARGET)
        for parent in loader.graph.node_map[TARGET].parents:
            dependency = parent.key
            if dependency not in loader.applied_migrations:
                raise CommandError(f"Apply dependency {dependency} before repair.")
        apps = loader.project_state([TARGET]).apps
        models = [apps.get_model("inventory", op.name) for op in migration.operations
                  if isinstance(op, migrations.CreateModel)]
        missing = []
        with transaction.atomic():
            with connection.cursor() as cursor:
                tables = set(connection.introspection.table_names(cursor))
                for model in models:
                    table = model._meta.db_table
                    if table not in tables:
                        if model._meta.model_name != "stockadjustment":
                            raise CommandError(f"Expected legacy table {table} is missing; stopping.")
                        missing.append(model)
                        continue
                    columns = {c.name: c for c in connection.introspection.get_table_description(cursor, table)}
                    constraints = connection.introspection.get_constraints(cursor, table)
                    for field in model._meta.local_fields:
                        column = columns.get(field.column)
                        if column is None:
                            raise CommandError(f"Missing {table}.{field.column}; stopping before changes.")
                        actual = connection.introspection.get_field_type(column.type_code, column)
                        expected = (field.target_field if field.is_relation else field).get_internal_type()
                        # PostgreSQL introspection cannot distinguish positive integers or serial IDs.
                        equivalent = {"PositiveIntegerField": "IntegerField", "BigAutoField": "BigIntegerField", "AutoField": "IntegerField"}
                        text_compatible = actual == "TextField" and expected == "CharField"
                        if not text_compatible and equivalent.get(actual, actual) != equivalent.get(expected, expected):
                            raise CommandError(f"Unexpected type for {table}.{field.column}: {actual}.")
                        if column.null_ok != field.null:
                            raise CommandError(f"Unexpected nullability for {table}.{field.column}.")
                        if field.max_length and column.internal_size and column.internal_size < field.max_length:
                            raise CommandError(f"Column {table}.{field.column} is too short.")
                        if field.primary_key and not any(c["primary_key"] and c["columns"] == [field.column] for c in constraints.values()):
                            raise CommandError(f"Missing primary key on {table}.{field.column}.")
                        if field.unique and not any(c["unique"] and c["columns"] == [field.column] for c in constraints.values()):
                            raise CommandError(f"Missing unique constraint on {table}.{field.column}.")
                        if field.is_relation:
                            target = (field.related_model._meta.db_table, field.target_field.column)
                            if not any(c["foreign_key"] == target and c["columns"] == [field.column] for c in constraints.values()):
                                raise CommandError(f"Missing foreign key on {table}.{field.column}.")
                showroom = apps.get_model("inventory", "ShowroomStock")
                constraints = connection.introspection.get_constraints(cursor, showroom._meta.db_table)
                unique_exists = any(c["unique"] and c["columns"] == ["showroom_id", "product_id"] for c in constraints.values())
            with connection.schema_editor() as editor:
                for model in missing:
                    editor.create_model(model)
                if not unique_exists:
                    editor.add_constraint(showroom, showroom._meta.constraints[0])
            MigrationRecorder(connection).record_applied(*TARGET)
        self.stdout.write(self.style.SUCCESS("Legacy inventory reconciled; existing stock preserved. Run migrate --noinput next."))
