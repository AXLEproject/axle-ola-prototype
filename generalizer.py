#!/usr/bin/python
#
# Copyright (c) 2014, Portavita BV Netherlands

class Generalizer:
	levels = None

	def __repr__(self):
		return str(self.tree)

class NominalGeneralizer(Generalizer):
	def __init__(self, tree):
		self.tree = tree
		self.levels = len(tree.itervalues().next())

	def generalize(self, value, level):
		return self.tree[value][level]

class IntervalGeneralizer(Generalizer):
	def __init__(self, min, max, levels):
		self.cache = {}
		self.levels = levels
		self.tree = {}
		segments = 2 ** (levels - 3)
		for l in range(1, levels - 1): # lowest and highest level are evaluated differently (see generalize())
			delta = (max - min) / segments
			self.tree[l] = [(min + s * delta, min + (s + 1) * delta) for s in xrange(segments)]
			segments = segments / 2

	def generalize(self, value, level):
		try:
			return self.cache[(value, level)]
		except:
			pass
		
		if level == 0: # actual value on lowest level
			self.cache[(value, level)] = value
			return value
		if level == self.levels - 1: # None on highest level
			self.cache[(value, level)] = None
			return None
		result = None
		for (min, max) in self.tree[level]:
			if value >= min and value < max:
				result = (min, max)
		self.cache[(value, level)] = result
		return self.cache[(value, level)]

if __name__ == '__main__':
	trees = {}

	trees['bp'] = IntervalGeneralizer(min=40, max=180, levels=4)

	trees['agree'] = NominalGeneralizer({
		'completely agree':    ('completely agree',    'agree',    'agree or disagree'),
		'mostly agree':        ('mostly agree',        'agree',    'agree or disagree'),
		'mostly disagree':     ('mostly disagree',     'disagree', 'agree or disagree'),
		'completely disagree': ('completely disagree', 'disagree', 'agree or disagree')})

	print trees['bp'].generalize(112, 1)
	print trees['agree'].generalize('mostly disagree', 1)

