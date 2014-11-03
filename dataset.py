#!/usr/bin/python

import sqlite3, generalizer

class Dataset:

    def __init__(self, filename, tablename):
        self.tablename = tablename
        self.conn = sqlite3.connect(filename)
        self.data = self.get_data()
        self.attributes = self.get_attributes()

    def get_data(self):
        return [line for line in self.conn.execute("select * from {}".format(self.tablename))]

    def get_attributes(self):
        attributes = []
        c = self.conn.cursor()
        c.execute("pragma table_info({})".format(self.tablename))
        for (_, name, type, _, _, _) in c.fetchall():
            if type.lower() in ['integer', 'real', 'int']:
                (min, max) = self.get_min_max(name)
                gen = generalizer.IntervalGeneralizer(min, max, levels=6)
            else:
                vals = self.get_distinct_values(name)
                gen = generalizer.NominalGeneralizer({v:(v, None) for v in vals})
            attributes.append(Attribute(name, gen))
        return attributes

    def get_create_table(self):
        c = self.conn.cursor()
        c.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='{}'".format(self.tablename))
        (sql,) = c.fetchone()
        return sql

    def get_min_max(self, column_name):
        c = self.conn.cursor()
        query = "select min({0}), max({0}) from {1} where {0} != ''"
        c.execute(query.format(column_name, self.tablename))
        return c.fetchone()

    def get_distinct_values(self, column_name):
        c = self.conn.cursor()
        c.execute("select distinct {0} from {1}".format(column_name, self.tablename))
        return [v for (v, ) in c.fetchall()]

    def get_max_node(self):
        return [a.levels - 1 for a in self.get_attributes()]

    def get_min_node(self):
        return [0] * len(self.get_attributes())

    def deidentify(self, node):
        data = []
        for line in self.data:
            t = tuple(self.attributes[i].generalizer.generalize(val, node[i]) for i, val in enumerate(line))
            data.append(t)
        return data

    def suppression_rate(self, node, k=20):
        items = {}
        size = 0
        for n in self.deidentify(node):
            items[n] = items[n] + 1 if n in items else 1
            size += 1
        
        suppr_rows = sum(i for i in sorted(items.values()) if i < k)
        return suppr_rows / float(size)

class Attribute:
    """docstring for Attribute"""
    def __init__(self, name, generalizer):
        self.name = name
        self.generalizer = generalizer
        self.levels = generalizer.levels

    def __repr__(self):
        return "<%s: %s>" % (self.name, self.generalizer)

if __name__ == '__main__':
    dataset = Dataset('data.db', 'data')
    #for r in dataset.deidentify([0, 2, 1, 3, 4, 3, 4, 2, 0]):
    #    print r
    print dataset.suppression_rate([1, 3, 1, 3, 5, 4, 4, 4, 1], k=20)
