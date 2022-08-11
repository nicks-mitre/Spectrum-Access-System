"""
This file contains functions that (may) be helpful for people who use the Python shell, especially those who use
the IPython shell. It mainly provides functions for global-context and object-context introspection.
"""

import typing, types, re
from typing import Dict, List, Any, Optional, Tuple, Union, Type, Sequence, Container, Mapping
from collections import Counter
from types import ModuleType, FunctionType
from sys import getsizeof
import json

def getNonIpythonObjects(checkIfIsIPythonInstance: bool = True) -> Dict[str, Any]:
	"""
	Returns a copy of the globals dictionary with all ipython objects removed. If there are no ipython objects,
	returns the copy unmodified.
	"""
	toExecList: List[str] = []
	globalsCopy = globals().copy()

	if checkIfIsIPythonInstance:
		# If this is enabled and the environment in which it is called is not an ipython instance, then the var is not
		# an ipython object, so we return the globals dictionary copy unmodified.
		if 'get_ipython' not in globalsCopy.keys():
			return globalsCopy

	# there are more efficient/compact ways to write the following regular expression, but they are less readable.
	ipyPattern = re.compile(r'^(In|Out|get_ipython|exit|quit|_{1,3}|_(?:i+|i\d+|\d+|ih|dh|oh))$')
	
	# iterate through the copied globals dict keys, and if the key matches the pattern, add it to toExecList with the
	# required code as a string.
	for k in globalsCopy.keys():
		if ipyPattern.fullmatch(k):
			toExecList.append(f'del globalsCopy["{k}"]')

	for e in toExecList:
		# for each ipy object key, delete it from the globalsCopy dict by executing the (string of) code in e.
		exec(e)

	return globalsCopy


def getVarsInfoList(obj: Optional[Any] = None) -> List[Tuple[str, str, Union[str, int], int]]:
	"""
	Returns a list of tuples containing information about (non-IPython-related) objects in one of the following:
	global symbol table (if called without an argument - default)
	object obj's __dict__ (if called with an argument)
	"""
	itemsList = []
	infoList = [] # The list to be returned

	if obj is None:
		# If the function is called without args, the function uses the global symtable (with the IPython objects,
		# if any, excluded)
		itemsList = getNonIpythonObjects().items()
	else:
		# Otherwise, it uses the symtable of the obj
		try:
			itemsList = vars(obj).items()
		except TypeError:
			#TODO: Implement __slots__ check and return that instead.
			# TypeError: vars() argument must have __dict__ attribute
			return infoList

	for k, v in itemsList:
		vLen = '—' # displayed length for values that aren't Sized

		# typing.Sized is "an alias to collections.abc.Sized," which is an "[abstract base class] for classes
		# that provide the __len__() method."
		if isinstance(v, typing.Sized):
			#vLen = str(len(v))
			vLen = len(v)

		sizeInBytes = getsizeof(v)
		tupToAppend = (k, type(v), vLen, sizeInBytes)
		infoList.append(tupToAppend)

	return infoList


def filterGlobalsListByType(
	desiredType: Type,
	obj: Optional[Any] = None,
	include_subclasses: bool = True
) -> List[Tuple[str, str, Union[str, int], int]]:
	"""
	Returns a list of tuples containing information about the (non-IPython-related) objects of type desiredType in the
	globals dict. :param desiredType: A typing.Type object (e.g. 'desiredType=FunctionType' is equivalent to
	'desiredType=type(getVarsInfoList)') that specifies which objects to include in the returned list. :param obj:
	Optional parameter specifying that
	"""
	if not (isinstance(desiredType, Type) or isinstance(desiredType, typing._GenericAlias)):
		raise TypeError("desiredType must be of type Type")

	itemsList = []
	if (obj is not None) and (len(getVarsInfoList(obj)) > 0):
		for tup in getVarsInfoList(obj):
			if not include_subclasses:
				if isinstance(tup[1], desiredType):
					itemsList.append(tup)
			else:
				# issubclass(TypeA, TypeA) is True
				if issubclass(tup[1], desiredType):
					itemsList.append(tup)

	elif len(getVarsInfoList()) > 0:
		for tup in getVarsInfoList():
			if not include_subclasses:
				if isinstance(tup[1], desiredType):
					itemsList.append(tup)
			else:
				if issubclass(tup[1], desiredType):
					itemsList.append(tup)

	return itemsList


def dispGlobalsTypes(
	obj: Optional[Any] = None,
	desiredType: Optional[Any] = None,
	sortBy: str = 'type',
	typeInFirstColumn: bool = False
) -> None:
	"""
	Display the names, types, and lengths (in the case of Sized types, otherwise length is displayed as —) of global variables.
	Checks for and prevents the inclusion of ipython line variables.
	sortBy may be one of the following: 'type' (default), 'name', 'length', 'size' or 'unsorted'
	(which is used as the default value when sortBy is not one of the previous four).
	"""
	if not isinstance(sortBy, str):
		# Instead of raising an error, just ignore the argument and proceed as if the default value was specified
		sortBy = 'unsorted'
	if not isinstance(typeInFirstColumn, bool):
		typeInFirstColumn = False

	if desiredType:
		itemsList = filterGlobalsListByType(desiredType, obj)
		if sortBy == 'type':
			# Sorting by a list of objects by type when they are the same type doesn't make much sense.
			sortBy = 'unsorted'
	else:
		itemsList = getVarsInfoList(obj) # Get the list of tuples

	if sortBy == 'type':
		itemsList.sort(key=lambda t: str(t[1]).lower()) # sort by object type
	elif sortBy == 'name':
		itemsList.sort(key=lambda t: t[0].lower()) # sort by object name
	elif sortBy == 'length':
		itemsList.sort(key=lambda t: t[2].lower()) # sort by object length
	elif sortBy == 'size':
		itemsList.sort(key=lambda t: t[3]) # sort by object size (in bytes (non-recursive))
	# if none of the above, itemsList remains in the order of when each object was defined.

	if typeInFirstColumn:
		for tup in itemsList:
			print("{:<50} {:<30} {:<12} {:<}".format(str(tup[1]), tup[0], tup[2], tup[3]))

	else: # Otherwise (default), the object's name is in the first column
		for tup in itemsList:
			print("{:<30} {:<50} {:<12} {:<}".format(tup[0], str(tup[1]), tup[2], tup[3]))


def dispDirTypes(obj: Optional[Any] = None):
	""" Display the item name and type for each item in the __dict__ of the given object. """
	if obj is None:
		dispGlobalsTypes('unsorted')

	else:
		dispGlobalsTypes(obj=obj)


def dispRecursive(obj: Any, desiredType: Type):
	"""
	The same as dispGlobalsTypes, but recursive and requires an object and a desiredType.
	"""
	pass


def ctr_to_dict(ctr: Counter) -> Dict[str, int]:
	"""
	Transform a Counter to a dict in sorted order by frequency
	"""
	if not isinstance(ctr, Counter): raise TypeError("ctr must be of type collections.Counter")
	return {k:v for k,v in ctr.most_common()}


def listImportedModules(obj: Optional[Any] = None):
	"""
	Return a list of active (imported) modules of the current (interactive shell) Python session or if obj is not
	None, the list of modules included in obj's __dict__
	"""
	moduleList = []

	if obj is None:
		for k,v in globals().items():
			if isinstance(v, types.ModuleType):
				moduleList.append(k)

	else:
		for k,v in vars(obj).items():
			if isinstance(v, types.ModuleType):
				moduleList.append(k)

	return moduleList


def listDefinedFunctions(obj: Optional[Any] = None):
	"""
	Return a list of active (imported) functions of the current (interactive shell) Python session or if obj is
	not None, the list of functions included in obj's __dict__
	"""
	functionList = []

	if obj is None:
		itemsList = globals().items()
	else:
		itemsList = vars(obj).items()

	for k,v in itemsList:
		if isinstance(v, types.FunctionType) or isinstance(v, types.BuiltinFunctionType) or isinstance(v, types.BuiltinMethodType):
			functionList.append(k)

	return functionList


def listTypes(
	obj: Optional[Any] = None,
	incl_aliases: bool = True
) -> List:
	"""
	Return a list of active (imported) types of the current (interactive shell) Python session or if obj is not None,
	the list of types included in obj's __dict__
	:param obj: the object whose included types are to be listed
	:param incl_aliases: if True, then also include objects of type GenericAlias
	"""
	typeList = []

	if obj is None:
		#itemsList = filterGlobalsListByType(desiredType)
		return dispGlobalsTypes(desiredType=type)
	else:
		itemsList = vars(obj).items()

	if incl_aliases:
		for k, v in itemsList:
			if isinstance(v, typing.Type) or isinstance(v, typing._GenericAlias):
				typeList.append(k)
	else:
		for k,v in itemsList:
			if isinstance(v, typing.Type):
				typeList.append(k)

	return typeList


def isContainer(obj: Any) -> bool: return isinstance(obj, Container)


def isSequence(obj: Any) -> bool: return isinstance(obj, Sequence)


def isMapping(obj: Any) -> bool: return isinstance(obj, Mapping)


def isFlat(mapping:Mapping) -> bool:
	"""
	Return True if the given mapping is flat (i.e. has no sub-containers) or if the input is not a mapping. Returns false otherwise.
	"""
	if not isinstance(mapping, Mapping):
		return True

	return not any([isContainer(v) for v in mapping.values()])


def isSimpleSequence(seq: Sequence) -> bool:
	"""
	In this case, for a sequence to be simple, all of its elements must be either a primitive type or another simple sequence (checked recursively). This isn't exactly simple, but it fits the purpose of ensuring that the sequence doesn't have any elements of type Mapping, so we can iterate through the sequence, without needing to consider keys and values.
	"""
	if not isSequence(seq):
		raise TypeError("seq must be of type Sequence (e.g. list, tuple, or range).")

	# Strings are of type Sequence too, but we don't want to process it, so we explicitly return True
	if isinstance(seq, str):
		return True

	for elem in seq:
		# Strings are of type Sequence too, but we don't want to process it, so we continue
		if isinstance(seq, str):
			continue
		if isContainer(elem):
			if isSequence(elem):
				if isSimpleSequence(elem):
					# Element is a simple sequence, so continue to the next element
					continue
				else:
					# Element is a sequence, but not a simple one
					return False
			# Element is a container, but not a sequence
			return False
	# All elements are either primitive types or simple sequences
	return True


def djson(
	filename: str,
	obj: Mapping,
	mode: str = 'w',
	indent: int = 2
) -> None:
	"""
	Write the given JSON-serializable Python object to a file with the given filename
	:param filename: Path to the file to which the JSON will be written
	:param obj: The JSON-serializable object to dump to the file
	:param mode: The mode with which to open the file
	:param indent: The number of spaces to use to indent
	"""
	with open(filename, mode) as fp:
		json.dump(obj, fp, indent=indent)


def ljson(
	filename: str
) -> Union[Dict, List]:
	"""
	Returns a Python object deserialized from the given JSON file.
	:param filename: The file from which to load the JSON-serialized Python object
	:return: The deserialized Python object will be either a dictionary or a list
	"""
	with open(filename) as fp:
		return json.load(fp)
