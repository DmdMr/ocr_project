"""Optional migration helper.

This project now runs on SQLite by default.
If you need Mongo->SQLite migration later, implement readers from old dumps here.
"""

if __name__ == "__main__":
    print("No-op migration script (old data migration is optional).")
