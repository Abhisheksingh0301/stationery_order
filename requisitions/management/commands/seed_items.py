from django.core.management.base import BaseCommand
from requisitions.models import Item

DEFAULT_ITEMS = [
    ("A4 Paper",          "stationery",  "pcs"),
    ("Pen (Blue)",        "stationery",  "pcs"),
    ("Pen (Black)",       "stationery",  "pcs"),
    ("Pencil",            "stationery",  "pcs"),
    ("Notebook",          "stationery",  "pcs"),
    ("Stapler Pins",      "stationery",  "boxes"),
    ("Cello Tape",        "stationery",  "rolls"),
    ("Glue Stick",        "stationery",  "pcs"),
    ("Marker (Permanent)","stationery",  "pcs"),
    ("Whiteboard Marker", "stationery",  "pcs"),
    ("Sticky Notes",      "stationery",  "packets"),
    ("File Folder",       "stationery",  "pcs"),
    ("Printer Ink (Black)","it_supplies","pcs"),
    ("Printer Ink (Color)","it_supplies","pcs"),
    ("Hand Sanitizer",    "hygiene",     "litres"),
    ("Tissue Box",        "hygiene",     "pcs"),
    ("Disinfectant",      "hygiene",     "litres"),
    ("Rice",              "pantry",      "kg"),
    ("Sugar",             "pantry",      "kg"),
    ("Tea Bags",          "pantry",      "packets"),
    ("Coffee Powder",     "pantry",      "g"),
    ("Milk",              "pantry",      "litres"),
    ("Cooking Oil",       "pantry",      "litres"),
]


class Command(BaseCommand):
    help = "Seeds the Item table with a default master list."

    def handle(self, *args, **options):
        created = 0
        for name, category, unit in DEFAULT_ITEMS:
            obj, was_created = Item.objects.get_or_create(
                item_name=name,
                defaults={"category": category, "default_unit": unit},
            )
            if was_created:
                created += 1
        self.stdout.write(self.style.SUCCESS(
            f"Seed complete. {created} new items inserted, "
            f"{len(DEFAULT_ITEMS) - created} already existed."
        ))
