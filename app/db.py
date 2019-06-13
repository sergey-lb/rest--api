import psycopg2
from psycopg2.extras import RealDictCursor

class Db:

    def __init__(self, conf):
        self._conf = conf

    def _open_db(self):
        db = psycopg2.connect(
            dbname=self._conf['db'],
            user=self._conf['user'],
            password=self._conf['pass'],
            host=self._conf['host'],
            port=self._conf['port'],
            cursor_factory=RealDictCursor
        )
        return db

    def validate_table_or_column_name(self, name):
        name_alnum = list(filter(lambda c: c.isalnum() or c == '_', name))

        is_valid = len(name_alnum) == len(name)
        if not is_valid:
            raise Exception(
                f"Table {name} is not valid table name, "
                "only alphanumerical characters and underscore in table names is allowed"
            )

    def _add_sorting_part(self, sql, sorting):
        if sorting is None:
            sorting = {
                'column': 'id',
                'order': 'DESC'
            }
        else:
            self.validate_table_or_column_name(sorting['column'])
            if sorting['order'] != 'ASC':
                sorting['order'] = 'DESC'

        sql += f" ORDER BY {sorting['column']} {sorting['order']}"
        return sql

    def find(self, table, item_id):
        self.validate_table_or_column_name(table)
        with self._open_db() as db:
            sql = f"SELECT * FROM {table} WHERE id = %(id)s";
            cursor = db.cursor()
            cursor.execute(sql, {'id': item_id})
            item = cursor.fetchone()
            return item

    def find_all(self, table, sorting=None):
        self.validate_table_or_column_name(table)

        with self._open_db() as db:
            sql = f"SELECT * FROM {table}"
            sql = self._add_sorting_part(sql, sorting)
            cursor = db.cursor()
            cursor.execute(sql)
            items = cursor.fetchall()
            return items

    def find_by_column(self, table, *, column, value, sorting=None):
        self.validate_table_or_column_name(table)
        self.validate_table_or_column_name(column)

        with self._open_db() as db:
            sql = f"SELECT * FROM {table} WHERE {column} = %(value)s"
            sql = self._add_sorting_part(sql, sorting)
            cursor = db.cursor()
            cursor.execute(sql, {'value': value})
            items = cursor.fetchall()
            return items

    def find_by_column_in(self, table, *, column, values, sorting=None):
        self.validate_table_or_column_name(table)
        self.validate_table_or_column_name(column)
        values = tuple(values)
        with self._open_db() as db:
            sql = f"SELECT * FROM {table} WHERE {column} IN %(values)s"
            sql = self._add_sorting_part(sql, sorting)
            cursor = db.cursor()
            cursor.execute(sql, {'values': values})
            items = cursor.fetchall()
            return items

    def find_by_column_like(self, table, *, column, value, sorting=None):
        self.validate_table_or_column_name(table)
        self.validate_table_or_column_name(column)
        with self._open_db() as db:
            sql = f"SELECT * FROM {table}"
            sql += f" WHERE {column} LIKE %(value)s"
            sql = self._add_sorting_part(sql, sorting)
            items = db.cursor().execute(sql, {'value': '%' + value + '%'}).fetchall()
            return items

    def insert(self, table, item):
        self.validate_table_or_column_name(table)
        with self._open_db() as db:
            if type(item) is not dict:
                item = item.__dict__

            cols_str = ",".join(item.keys())
            vals_str = "%(" + ")s, %(".join(item.keys()) + ')s'
            sql = f"INSERT INTO {table} ({cols_str}) VALUES({vals_str}) RETURNING id"
            cursor = db.cursor()
            cursor.execute(sql, item)
            insert_id = cursor.fetchone()
            return insert_id['id']

    def update(self, table, item):
        self.validate_table_or_column_name(table)
        with self._open_db() as db:
            if type(item) is not dict:
                item = item.__dict__

            sql_set = []
            for key in item.keys():
                if key == 'id':
                    continue
                sql_set.append(key + ' = %(' + key + ')s')

            sql = f"UPDATE {table} SET " + ",".join(sql_set) + " WHERE id = %(id)s"
            db.cursor().execute(sql, item)

    def delete(self, table, item_id):
        self.validate_table_or_column_name(table)
        with self._open_db() as db:
            sql = f"DELETE FROM {table} WHERE id = %(id)s"
            db.cursor().execute(sql, {'id': item_id})

    def raw(self, sql, params=None):
        with self._open_db() as db:
            if params is None:
                params={}
            cursor = db.cursor()
            cursor.execute(sql, params)
            return cursor
