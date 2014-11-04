#!/usr/bin/python
#
# Copyright (c) 2014, Portavita BV Netherlands

from collections import defaultdict
import dataset, itertools
import argparse, sqlite3

class Lattice:
    def __init__(self, data):
    	"Creates a lattice for the given dataset and initializes some variables"
        self.dataset = data
        self.generate_lattice(data.get_max_node())
        
        # variables for progress indicator
        self.nodes_tagged = 0
        self.nodes_total = sum(len(self.lattice[x]) for x in self.lattice)
        
        # cache for descendent relations for performance
        self.descendent_cache = {}

    def __str__(self):
        return str(self.lattice)

    def generate_lattice(self, max_values):
    	"""Creates a lattice with all possible combinations of generalization 
		   levels: a dict of dicts with the following structure: 
		   {..., 3: {(2,0,1): None, (1,1,1): None}, ...}"""
        self.lattice = defaultdict(dict)
        possible_values = (xrange(x + 1) for x in max_values)
        for node in itertools.product(*possible_values):
            self.lattice[sum(node)][node] = None

    def tag_nodes(self, node, k_anonymous):
    	"""Tags the given node with the value of k_anonymous and also tags all 
    	   other nodes whose value can be derived from this fact"""
        if node == None or self.lattice[sum(node)][node] != None:
            return
        self.nodes_tagged += 1
        self.lattice[sum(node)][node] = k_anonymous
        for new_node in self.successors(node, k_anonymous):
            self.tag_nodes(new_node, k_anonymous)

    def successors(self, node, direction_up):
    	"""Returns a generator for all connected successors of the given node:
    	   i.e. all nodes directly connected to the given node in the direction
    	   indicated by direction_up (up for True, down for False)"""
        update_value = 1 if direction_up else -1
        target_level = sum(node) + update_value
        possible_nodes = itertools.product(*([x, x + update_value] for x in node))
        for successor in possible_nodes:
            level = sum(successor)
            if level == target_level and successor in self.lattice[level]:
                yield successor

    def tag_lattice(self, min_level, max_level, start_node):
    	"""Implements the OLA algorithm to tag all nodes of the lattice"""
    	
        if max_level - min_level <= 1: # base case
            return
        
        # print progress indicator
        print "\r%d%%" % (self.nodes_tagged / float(self.nodes_total) * 100),
        
        curr_level = (max_level + min_level) / 2 # determine middle level
        
        # loop over nodes in middle level
        for node in self.lattice[curr_level].keys():
        	# filter non-descendents
            if not self.is_descendent(node, start_node):
                continue
            
            # determine k-anonimity
            k_anonymous = self.lattice[curr_level][node] 
            if k_anonymous == None:
                k_anonymous = self.is_k_anonymous(node)
            
            self.tag_nodes(node, k_anonymous)

            if(k_anonymous):
                self.tag_lattice(min_level, curr_level, start_node) # recursion
            else:
                self.tag_lattice(curr_level, max_level, node) # recursion

    def is_descendent(self, node, start_node):
    	"""Returns True if node is a descendent of start_node. Uses caching for
    	   performance"""
        try:
            result = self.descendent_cache[(start_node, node)]
        except KeyError:
            result = node != start_node and not any(node[i] < start_node[i] for i in xrange(len(node)))
            self.descendent_cache[(start_node, node)] = result
        return result

    def is_k_anonymous(self, node, allowed_suppression_rate=.05):
    	"""Returns True if a generalization at the level indicated by node is
    	   k-anonymous and the suppression rate is below the allowed_suppression_rate"""
        return self.dataset.suppression_rate(node) <= allowed_suppression_rate

    def select_lowest_loss(self):
        """Simple approximation of information loss by Samarati algorithm. Return 
           first best-level solution found"""
        for level in sorted(self.lattice):
            for node in self.lattice[level]:
                if self.lattice[level][node]:
                    return node

def main():
    parser = argparse.ArgumentParser(description='De-identify an SQLite database')
    parser.add_argument('db_in', metavar='in', type=str,
                       help='the database file to de-identify')
    parser.add_argument('db_out', metavar='out', type=str,
                       help='the output database filename')

    args = parser.parse_args()

    data = dataset.Dataset(args.db_in, "data")

    print "generating lattice...",
    lattice = Lattice(data)
    print "done\nevaluating lattice..."
    lattice.tag_lattice(0, max(lattice.lattice), tuple(data.get_min_node()))
    print "done\nselecting best generalization level...",
    best_levels = lattice.select_lowest_loss()
    #print best_levels
    print "done\nwriting de-identified version to db...",
    write_to_disk(data, best_levels, args.db_out)
    print "done"

def write_to_disk(data, best_levels, filename):
    conn = sqlite3.connect(filename)
    c = conn.cursor()
    c.execute('drop table {}'.format(data.tablename))
    c.execute(data.get_create_table())
    sql = ('insert into {} values (?' + ',?' * (len(data.attributes) - 1) + ')').format(data.tablename)

    def get_value(value):
        if type(value) is tuple:
            # assume tuple of integers, i.e. range: return mean
            return sum(value)/float(len(value))
        return value

    new_data = []
    for line in data.deidentify(best_levels):
        new_data.append(tuple(get_value(x) for x in line ))
    c.executemany(sql, new_data)
    conn.commit()

if __name__ == '__main__':
    main()

